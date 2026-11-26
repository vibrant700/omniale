"""Build the V3 case from allowlisted inputs, sealed deliveries and completed measurements."""
import argparse
import hashlib
import html
import json
from pathlib import Path
import re
import shutil
import zipfile

from PIL import Image

HERE=Path(__file__).resolve().parent
FRAMES=[0,20,40,60,80,99,119,139,159,179]
INPUTS=['TASK.md','ENVIRONMENT.md','cameras.json','timeline.json','scene_setup.json','ASSET-ATTRIBUTION.txt','INPUT-USE.md']
INPUTS += [f'reference/{v}.mp4' for v in ['I1','I2','I3']]
WEIGHTS={'view_coverage':30,'geometry':30,'appearance':20,'audio':20}

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,obj):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def esc(s):return html.escape(str(s),quote=True)
def zipped(path,items):
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name,p in sorted(items.items()):
            info=zipfile.ZipInfo(name,date_time=(2026,11,27,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644<<16;z.writestr(info,p.read_bytes())
    with zipfile.ZipFile(path) as z:assert z.testzip() is None and set(z.namelist())==set(items)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',required=True,type=Path)
    parser.add_argument('--reference-archive',required=True,type=Path)
    parser.add_argument('--repo',type=Path,default=HERE.parents[2])
    args=parser.parse_args();case=args.archive.resolve();reference=args.reference_archive.resolve();repo=args.repo.resolve()
    site=repo/'docs/phoenix-reconstruction/v3';site.mkdir(parents=True,exist_ok=True)
    assets=site/'assets';assets.mkdir(exist_ok=True)
    models=read(HERE/'models.json');assert models
    freeze=read(case/'runs'/models[0]['run']/'input-freeze.json')
    candidate=case/'candidate'
    assert set(freeze['candidate'])==set(INPUTS)
    for name in INPUTS:
        p=candidate/name;assert sha(p)==freeze['candidate'][name]['sha256'],name
        dest=assets/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
    zipped(assets/'agent-input.zip',{n:candidate/n for n in INPUTS})
    write(assets/'input-manifest.json',{'version':'phoenix-multiview-v3','files':freeze['candidate'],'archive_sha256':sha(assets/'agent-input.zip'),'original_experiment_input':True})
    for view in ['I1','I2','I3']:
        rgba=Image.open(reference/f'public/reference/{view}/0000.png').convert('RGBA')
        bg=Image.new('RGBA',rgba.size,(32,38,48,255));bg.alpha_composite(rgba)
        bg.convert('RGB').save(assets/f'reference/{view}-poster.jpg',quality=92)
    first_eval=case/'runs'/models[0]['run']/'evaluation'
    source_protocol=read(first_eval/'PROTOCOL.json')
    keys=['fps','frames','frame_count','duration_s','reference_diagonal','primary_F1_tolerance_diagonal_fraction','F1_surface_sample_count_per_merged_surface','surface_seed_reference','surface_seed_candidate','alpha_threshold','alpha_geometry','surface_visibility','geometry_objects','silhouette_views','silhouette','appearance_source','appearance_crop','appearance_region','SSIM','aggregation','geometry_protocol','appearance_crop_policy']
    protocol={k:source_protocol[k] for k in keys}
    protocol.update(revision='phoenix-v3-iou30-f130-ssim20-audio20-r1',task_version='phoenix-multiview-v3',weights=WEIGHTS,
                    score_formula='30*mean_IoU + 30*mean_F1 + 20*clip(mean_RGB_SSIM,0,1) + audio_20',audio={'items':10,'points_per_pass':2,'duration_s':6,'mechanism':'Full submitted audio-video checklist with timestamped evidence; assess actual submitted motion.'})
    write(assets/'protocol.json',protocol)
    # Public mechanism text excludes internal review history and unpublished judgments.
    source=(HERE/'SCORING.md').read_text(encoding='utf-8')
    mechanisms=source[source.index('视觉固定抽取'):source.index('### 评审步骤与有效性')]
    mechanisms=mechanisms.replace('；证据不足记“无法判定”，不是 0 分，也不计为有效总分，须补充有效媒体或人工复核后裁定','；证据不足时补充有效媒体或人工听看裁定')
    mechanisms=mechanisms.replace('对按旧版每项 0／1 分提交的原始评审，保留原文件，以原判定乘 2 生成单独的权重换算记录，不声称重新评审。','')
    scoring='# 凤凰 V3 评分机制\n\n二维覆盖度 30、三维几何 F1 30、成片外观 20、音效 20，总分 100。\n\n'+mechanisms
    scoring+='\n每项音效判断保留音画时间依据。自动同步判断须通过时间平移和节奏对照检查；不能可靠判断时由人工听看裁定。工程编辑、资源解析、混音重构与素材来源独立验收，不另加分。\n'
    (assets/'SCORING.md').write_text(scoring,encoding='utf-8')
    checklist=[]
    for line in source.splitlines():
        if re.match(r'\| A\d+ \|',line):
            cells=[c.strip() for c in line.strip('|').split('|')]
            checklist.append(f'<tr><td>{esc(cells[0])} · {esc(cells[1])}</td><td>{esc(cells[2])}</td><td>2</td></tr>')
    assert len(checklist)==10
    rows=[];options=[];panels=[];execution=[];analysis=[]
    for index,model in enumerate(models):
        assert model['public_result_scope']=='objective_metrics_and_engineering'
        ident=model['id'];label=model['label'];run=case/'runs'/model['run'];evaluation=run/'evaluation';delivery=run/'remote-delivery'
        record=read(run/'run_record.json');rawscore=read(evaluation/'score.json');manifest=read(run/'delivery-manifest.json')['files']
        verify=read(evaluation/'final-verification.json');audit=read(evaluation/'reaper-engineering-audit.json')
        assert record['status']=='solver_finished' and record['candidate_unchanged'] and record['submission_stable']
        assert rawscore['model']==model['model'] and rawscore['effort']==model['effort'] and rawscore['frames']==FRAMES
        assert verify['video']['full_decode_passed'] and verify['stem_reconstruction']['passed'] and audit['passed']
        dest=site/'results'/ident;dest.mkdir(parents=True,exist_ok=True)
        allow={}
        for name,item in manifest.items():
            p=delivery/name;assert p.is_file() and not p.is_symlink() and sha(p)==item['sha256'] and p.stat().st_size==item['bytes']
            assert not Path(name).is_absolute() and '..' not in Path(name).parts
            assert Path(name).suffix.lower() in {'.blend','.mp4','.rpp','.wav','.ogg','.txt','.md'},name
            target=dest/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target);allow[name]=p
        zipped(dest/'delivery.zip',allow)
        for name in ['geometry_metrics.json','image_metrics.json']:shutil.copyfile(evaluation/name,dest/name)
        raw=rawscore['raw'];scores={k:rawscore['scores'][k] for k in ['view_coverage','geometry','appearance','non_audio_subtotal']}
        assert abs(sum(scores[k] for k in ['view_coverage','geometry','appearance'])-scores['non_audio_subtotal'])<1e-10
        public_score={'task_version':'phoenix-multiview-v3','model':model['model'],'effort':model['effort'],'framework':model['framework'],
                      'result_scope':'objective_metrics_and_engineering','scoring_revision':protocol['revision'],'scores':scores,
                      'maxima':{'view_coverage':30,'geometry':30,'appearance':20,'non_audio_subtotal':80},'task_weights':WEIGHTS,'frames':FRAMES,'raw':raw,
                      'protocol_sha256':sha(assets/'protocol.json'),'submission_files_sha256':{n:v['sha256'] for n,v in manifest.items()}}
        write(dest/'score.json',public_score)
        engineering=read(evaluation/'engineering.json')
        track_count=verify['reaper_project']['track_count']
        item_count=len(re.findall(r'^\s*<ITEM\b',(delivery/model['audio_project']).read_text(encoding='utf-8'),re.M))
        bone_count=sum(a['bones'] for a in engineering['armatures'])
        image_count=len(engineering['resources'])
        public_engineering={'video':verify['video'],'blender':{'version':engineering['blender'],'armatures':engineering['armatures'],
            'unique_sampled_skinned_states':engineering['unique_skinned_geometry_states'],'camera_T1_matrix_max_abs_difference':engineering['camera_T1_matrix_max_abs_difference'],
            'resources_standalone_resolved':engineering['resources_standalone_resolved'],'images':[{'name':x['name'],'packed':x['packed'],'resolved':x['standalone_resolved']} for x in engineering['resources']]},
            'reaper':{'version':'7.86/linux-x86_64','tracks':track_count,'items':item_count,'relocated_project_opened':True,'rerender_max_error':audit['rerender_max_error'],'rerender_rms_error':audit['rerender_rms_error']},
            'stem_reconstruction':verify['stem_reconstruction'],'note':'工程核验与声音听感评价分别报告。'}
        write(dest/'engineering.json',public_engineering)
        Image.open(evaluation/'decoded-video/0000.png').convert('RGB').save(dest/'poster.jpg',quality=92)
        comparison=dest/'comparison';comparison.mkdir(exist_ok=True)
        gm=read(evaluation/'geometry_metrics.json');im=read(evaluation/'image_metrics.json');frame_data=[]
        crop=protocol['appearance_crop'];x0,y0,x1,y1=crop
        for frame in FRAMES:
            card=Image.open(evaluation/f'comparisons/{frame:04d}.jpg').convert('RGB')
            left=card.crop((x0,y0,x1,y1));right=card.crop((1280+x0,y0,1280+x1,y1))
            result=Image.new('RGB',(2*(x1-x0),y1-y0));result.paste(left,(0,0));result.paste(right,(x1-x0,0))
            result.save(comparison/f'frame-{frame:02d}.webp',quality=94)
            measure=gm['frames'][str(frame)]['input_visible_surface']['0.005'];views={v:im['frames'][str(frame)][v]['IoU'] for v in ['I1','I2','I3','T1']}
            frame_data.append({'frame':frame,'F1':measure['f1'],'IoU':views,'SSIM':im['frames'][str(frame)]['T1']['appearance']['SSIM'],
                               'observation':f'本帧可见表面的精确率 P 为 {measure["precision"]:.4f}，召回率 R 为 {measure["recall"]:.4f}；距离容差为参考联合包围盒对角线的 0.5%。'})
        write(comparison/'frame-data.json',frame_data)
        shutil.copyfile(evaluation/'comparison-overview.jpg',comparison/'comparison-sheet.jpg')
        base=f'results/{ident}';hidden='' if index==0 else ' hidden'
        options.append(f'<option value="{esc(ident)}">{esc(label)} · {esc(model["effort"])} · {esc(model["framework"])}</option>')
        rows.append(f'<tr data-result-model="{esc(ident)}"><th scope="row"><a href="#model-{esc(ident)}" data-select-model="{esc(ident)}">{esc(label)}</a></th><td>{esc(model["effort"])}</td><td>{esc(model["framework"])}</td><td>{scores["view_coverage"]:.2f}</td><td>{scores["geometry"]:.2f}</td><td>{scores["appearance"]:.2f}</td><td><strong class="score-value">{scores["non_audio_subtotal"]:.2f}</strong></td></tr>')
        audio_players=''.join(f'<figure><figcaption><strong>{esc(title)}</strong><span>{caption}</span></figcaption><audio controls preload="metadata" src="{base}/{esc(name)}" aria-label="{esc(label)} {esc(title)}"></audio></figure>' for name,title,caption in
            [(model['mix'],'完整混音','REAPER 实际导出')]+[(stem['file'],stem['title'],'模型自行设计的声部') for stem in model['stems']])
        downloads=''.join(f'<a href="{base}/{name}" download><strong>{title} ↓</strong><span>{caption}</span></a>' for name,title,caption in [
            ('score.json','score.json','当前权重下的客观分数与原始指标'),('geometry_metrics.json','geometry_metrics.json','十帧三维 P、R 与表面 F1'),('image_metrics.json','image_metrics.json','40 个轮廓 IoU 与十帧 RGB SSIM'),('engineering.json','engineering.json','工程打开、资源、分轨及迁移重导核验')])
        panels.append(f'''<div class="model-panel" data-model-panel="{ident}" id="model-{ident}"{hidden}>
          <div class="model-heading"><h3>{esc(label)} · {esc(model['effort'])} ＋ {esc(model['framework'])}</h3><span>实际交付 · 六秒完整成片</span></div>
          <div class="delivery-layout"><figure><video controls playsinline preload="metadata" poster="{base}/poster.jpg" src="{base}/T1.mp4" aria-label="{esc(label)} 实际交付有声成片"></video><figcaption><strong>T1 · 实际交付</strong><a href="{base}/T1.mp4" download>下载原片 ↓</a></figcaption></figure>
          <aside class="delivery-summary"><h3>三项客观指标小计</h3><div class="score-display"><strong>{scores['non_audio_subtotal']:.2f}</strong><span>/ 80</span></div><p>四机位轮廓 IoU {raw['mean_IoU']:.4f}<br>三维表面 F1 {raw['mean_F1']:.4f}<br>前景 RGB SSIM {raw['mean_RGB_SSIM']:.4f}</p><p>成片和工程保留模型原始交付；数值由固定脚本测量并独立复算。</p><div class="inline-links"><a href="#{ident}-score-files">评分 JSON ↓</a><a href="{base}/README.md">原始说明 ↗</a></div></aside></div>
          <div class="inline-links native-files"><a href="{base}/delivery.zip" download>完整原始交付 · {(dest/'delivery.zip').stat().st_size/1024**2:.1f} MB ↓</a><a href="{base}/scene.blend" download>Blender 工程 ↓</a><a href="{base}/{esc(model['audio_project'])}" download>REAPER 工程 ↓</a></div>
          <p class="note media-note">打开 REAPER 工程需保留完整交付包中的素材相对位置。</p>
          <h3>模型的声音交付</h3><p class="note">以下声部划分来自模型实际工程；题面未指定这些声音类别或轨道名称。</p><div class="audio-grid">{audio_players}</div>
          <div class="json-downloads result-downloads" id="{ident}-score-files"><h3>本次客观评分与核验 JSON</h3><p>轮廓、三维表面与成片外观的原始逐帧测量，及独立工程核验记录。</p><div class="download-grid">{downloads}</div></div>
          </div>''')
        execution.append(f'''<div class="model-panel" data-model-panel="{ident}"{hidden}><p class="model-section-label">{esc(label)} · {esc(model['effort'])} ＋ {esc(model['framework'])}</p>
          <dl class="runtime-list"><div><dt>模型与环境</dt><dd>{esc(model['model'])} · {esc(model['effort'])}；官方 Codex CLI 0.142.4；Blender 4.5.3 LTS、REAPER 7.86、RTX 4090 D 24GB、八核 CPU 亲和性。</dd></div><div><dt>执行规模</dt><dd>{int(record['elapsed_seconds']//60)} 分 {record['elapsed_seconds']%60:.2f} 秒 · {record['tool_calls']} 次工具调用。独立新上下文，无人工制作辅导，未设工具次数与墙钟时限。</dd></div><div><dt>选材条件</dt><dd>允许访问公共互联网寻找录音；输入未提供音效、原始角色、目标机位视频或历史提交。运行中补齐环境说明列出的 SoundFile 依赖，修复记录内部归档。</dd></div><div><dt>核验分工</dt><dd>固定脚本计算客观指标；独立重开工程、检查资源和动画姿态，复制 REAPER 工程至新目录重导混音，再逐样本比较。</dd></div></dl>
          <ul class="verified-list"><li>{len(manifest)} 个原始交付文件逐一核验 SHA-256；输入未修改，封存前后交付稳定。</li><li>Blender：{bone_count} 根骨骼，十个抽样时刻有 {engineering['unique_skinned_geometry_states']} 个不同蒙皮状态，{image_count} 张纹理完整打包。</li><li>REAPER：{track_count} 轨、{item_count} 个片段，各轨保留效果器；迁移重导混音与提交混音逐样本一致。</li><li>{len(model['stems'])} 份分轨相加的最大绝对误差为 {verify['stem_reconstruction']['max_absolute_error']:.3g}，低于 10<sup>−5</sup> 的重构容差。</li></ul></div>''')
        buttons=''.join(f'<button type="button" data-frame="{f}" aria-pressed="{str(f==0).lower()}">{f:02d}</button>' for f in FRAMES)
        analysis.append(f'''<div class="model-panel" data-model-panel="{ident}"{hidden}><h3>{esc(label)} · 十个对应时刻</h3>
          <div class="frame-inspector" data-frame-inspector data-frame-root="{base}/comparison/" data-label="{esc(label)}"><div class="frame-toolbar"><strong data-frame-title>帧 00 · 0.000 s</strong><span>左：评测参考　右：实际交付</span></div><div class="frame-buttons" role="group" aria-label="选择评分帧">{buttons}</div>
          <a class="image-zoom" data-frame-link data-zoom data-title="{esc(label)} · 帧 00" href="{base}/comparison/frame-00.webp"><img data-frame-image src="{base}/comparison/frame-00.webp" alt="左参考凤凰，右实际重建，同时间同尺度" width="1276" height="590" loading="lazy"></a><p class="metric-strip" data-frame-metrics>逐帧原始指标</p><p class="frame-observation" data-frame-observation>本帧对应测量。</p></div>
          <p class="inline-links"><a href="{base}/comparison/comparison-sheet.jpg" data-zoom data-title="{esc(label)} · 十帧总览">十帧总览 ↗</a><a href="{base}/comparison/frame-data.json">逐帧数据 JSON ↗</a></p>
          <div class="findings-grid"><article><span class="finding-number">01 / 几何</span><h3>整体姿态已建立</h3><p>角色具备完整骨架、拍翼和滑翔过程。表面 F1 为 {raw['mean_F1']:.4f}，对照中的翼面弯曲、身体体积与尾翎布局仍有可见差异。</p></article><article><span class="finding-number">02 / 外观</span><h3>细节与颜色仍有偏差</h3><p>羽翼与眼斑尾翎能够辨识，参考和交付的尾翎底色、羽片排列及受光层次仍不一致；前景 RGB SSIM 为 {raw['mean_RGB_SSIM']:.4f}。</p></article><article><span class="finding-number">03 / 工程</span><h3>声音制作可继续修改</h3><p>模型自主组织 {track_count} 个声部与 {item_count} 个片段，保留变速、淡化、声像和效果器。工程迁移重导与分轨重构均已核验。</p></article></div></div>''')
    page=(HERE/'index.html').read_text(encoding='utf-8')
    values={'PACKAGE_SIZE':f'{(assets/"agent-input.zip").stat().st_size/1024**2:.1f} MB','TASK_TEXT':esc((candidate/'TASK.md').read_text(encoding='utf-8')),
            'AUDIO_CHECKLIST':''.join(checklist),'MODEL_ROWS':''.join(rows),'MODEL_OPTIONS':''.join(options),'MODEL_PANELS':''.join(panels),'EXECUTION_PANELS':''.join(execution),'ANALYSIS_PANELS':''.join(analysis)}
    for name,value in values.items():page=page.replace('<!--'+name+'-->',value)
    assert not re.search(r'<!--[A-Z_]+-->',page)
    (site/'index.html').write_text(page,encoding='utf-8');shutil.copyfile(HERE/'style.css',site/'style.css')
    write(site/'models.json',[{k:m[k] for k in ['id','label','model','effort','framework','public_result_scope']} for m in models])
    (site/'ATTRIBUTION.md').write_text('# 素材与交付署名\n\n视觉参考：phoenix bird / NORBERTO-3D，Sketchfab，CC BY 4.0。参考渲染调整了动画速度、幅度与滑翔终态。\n\n模型交付的声音使用 The Battle for Wesnoth 中的录音及模型自行合成的气流，依原始交付 README 署名，相关 GPL v2 或更高版本许可随交付包提供。实际文件、作者、来源和处理说明见各模型原始 README。\n\n评测端原始模型、参考 Blender 工程、完整目标机位真值及未审核工具轨迹不在公开文件中。\n',encoding='utf-8')
    write(site/'manifest.json',{'task_version':'phoenix-multiview-v3','files':[{'file':p.relative_to(site).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(site.rglob('*')) if p.is_file() and p!=site/'manifest.json']})
    # Preserve all other catalog cards, including upstream updates.
    catalog=repo/'docs/index.html';text=catalog.read_text(encoding='utf-8')
    match=re.search(r'<a class="case-card" href="phoenix-reconstruction[^\"]*">.*?</a>',text,re.S);assert match
    card=match.group()
    card=re.sub(r'href="phoenix-reconstruction[^\"]*"','href="phoenix-reconstruction/v3/"',card,count=1)
    card=re.sub(r'src="phoenix-reconstruction[^\"]*"','src="phoenix-reconstruction/v3/assets/reference/I1-poster.jpg"',card,count=1)
    card=re.sub(r'<p>.*?</p>','<p>根据三路同步录像重建六秒凤凰动画，自行寻找声音素材，使用 REAPER 完成拟音与混音，交付可编辑工程和分轨。</p>',card,count=1,flags=re.S)
    card=re.sub(r'<div class="status">.*?</div>','<div class="status"><span class="status-dot"></span>V3 · Astra 6.2 xhigh ＋ Codex · 客观指标 25.25 / 80</div>',card,count=1,flags=re.S)
    card=re.sub(r'<span class="enter">.*?</span>','<span class="enter">查看题目、成片、声音工程与客观核验 →</span>',card,count=1,flags=re.S)
    catalog.write_text(text[:match.start()]+card+text[match.end():],encoding='utf-8')
    for p in [repo/'cases/phoenix-reconstruction/index.html',repo/'docs/phoenix-reconstruction/index.html']:
        text=p.read_text(encoding='utf-8')
        if 'href="v3/index.html"' not in text:text=text.replace('</nav>','<a href="v3/index.html">V3 · 六秒动画与自主拟音 →</a></nav>',1)
        p.write_text(text,encoding='utf-8')
    parent=site.parent
    write(parent/'manifest.json',{'case':'phoenix-reconstruction','files':[{'file':p.relative_to(parent).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(parent.rglob('*')) if p.is_file() and p.name!='manifest.json']})
    print(json.dumps({'page':str(site/'index.html'),'models':len(models),'input_files':len(INPUTS),'public_result_scope':'objective_metrics_and_engineering','audio_judge_reports_published':False},ensure_ascii=True))

if __name__=='__main__':main()
