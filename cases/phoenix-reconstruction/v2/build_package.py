"""Build V2 candidate inputs and version page from an explicit public allowlist."""
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
NAMES=['TASK.md','cameras.json','timeline.json','scene_setup.json','ASSET-ATTRIBUTION.txt','INPUT-USE.md']
NAMES += [f'reference/{v}.mp4' for v in ['I1','I2','I3']]
NAMES += [f'audio/{n}' for n in ['air_long.wav','air_low.wav','feather_rustle.wav','sweep_broad.wav','sweep_light.wav','SOURCE.txt']]
FRAMES=[0,20,40,60,80,99,119,139,159,179]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write_json(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def inline(text):
    text=html.escape(text)
    text=re.sub(r'`([^`]+)`',r'<code>\1</code>',text)
    return re.sub(r'\*\*([^*]+)\*\*',r'<strong>\1</strong>',text)
def body(text):
    blocks=[]
    for block in text.strip().split('\n\n'):
        if block.startswith('|'):
            rows=[r.strip().strip('|').split('|') for r in block.splitlines()]
            cells=lambda row,tag:''.join(f'<{tag}>{inline(c.strip())}</{tag}>' for c in row)
            blocks.append('<div class="table-wrap"><table><thead><tr>'+cells(rows[0],'th')+'</tr></thead><tbody>'+''.join('<tr>'+cells(r,'td')+'</tr>' for r in rows[2:])+'</tbody></table></div>')
        else:blocks.append('<p>'+inline(block.replace('\n',' '))+'</p>')
    return ''.join(blocks)

def main():
    p=argparse.ArgumentParser();p.add_argument('--archive',required=True,type=Path)
    p.add_argument('--repo',type=Path,default=HERE.parents[2]);a=p.parse_args()
    root=a.archive.resolve();candidate=root/'candidate'
    validation=json.loads((root/'logs/media-validation.json').read_text(encoding='utf-8'))
    assert validation['synchronized_frames']==180 and validation['all_media_valid']
    protocol=json.loads((root/'private/evaluator/PROTOCOL.json').read_text(encoding='utf-8'))
    assert protocol['frames']==FRAMES and protocol['freeze_state']=='frozen_before_solver'
    (candidate/'reference').mkdir(exist_ok=True)
    for view in ['I1','I2','I3']:
        shutil.copyfile(root/f'public/reference/{view}.mp4',candidate/f'reference/{view}.mp4')
    shutil.copyfile(HERE/'TASK.md',candidate/'TASK.md')
    files={p.relative_to(candidate).as_posix() for p in candidate.rglob('*') if p.is_file()}
    assert files==set(NAMES),(files-set(NAMES),set(NAMES)-files)
    manifest={n:{'bytes':(candidate/n).stat().st_size,'sha256':sha(candidate/n)} for n in sorted(NAMES)}
    if (root/'input-freeze.json').exists():
        frozen=json.loads((root/'input-freeze.json').read_text(encoding='utf-8'))
        assert frozen['files']==manifest,'Frozen input changed: create an explicit new task revision.'
        assert frozen['evaluation_protocol_sha256']==sha(root/'private/evaluator/PROTOCOL.json'),'Frozen scoring protocol changed.'
    archive=root/'phoenix-agent-input-v2.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for n in sorted(NAMES):
            info=zipfile.ZipInfo(n,date_time=(2026,11,26,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644<<16
            z.writestr(info,(candidate/n).read_bytes(),compresslevel=6)
    with zipfile.ZipFile(archive) as z:
        assert set(z.namelist())==set(NAMES) and z.testzip() is None
        assert not any(n.lower().endswith(('.blend','.glb','.png','.npz')) or n=='T1.mp4' for n in z.namelist())
    write_json(root/'input-freeze.json',{'task_version':'phoenix-multiview-v2','files':manifest,
        'archive_sha256':sha(archive),'evaluation_protocol_sha256':sha(root/'private/evaluator/PROTOCOL.json'),
        'solver_runs_completed':0,'no_private_truth_in_candidate':True})
    site=a.repo/'docs/phoenix-reconstruction/v2';assets=site/'assets';assets.mkdir(parents=True,exist_ok=True)
    for n in NAMES:
        dest=assets/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(candidate/n,dest)
    shutil.copyfile(archive,assets/'agent-input.zip');shutil.copyfile(HERE/'SCORING.md',assets/'SCORING.md')
    write_json(assets/'input-manifest.json',{'version':'phoenix-multiview-v2','files':manifest,'archive_sha256':sha(archive)})
    allowed=['revision','task_version','frames','fps','frame_count','duration_s','weights',
        'primary_F1_tolerance_diagonal_fraction','F1_surface_sample_count_per_merged_surface',
        'reference_diagonal','surface_seed_reference','surface_seed_candidate','alpha_threshold',
        'alpha_geometry','surface_visibility','geometry_protocol','silhouette_views','silhouette',
        'appearance_source','appearance_crop','appearance_region','SSIM','aggregation',
        'score_formula','audio','audio_motion_policy','limitations']
    write_json(assets/'protocol.json',{k:protocol[k] for k in allowed})
    for view in ['I1','I2','I3']:
        rgba=Image.open(root/f'public/reference/{view}/0000.png').convert('RGBA')
        bg=Image.new('RGBA',rgba.size,(32,38,48,255));bg.alpha_composite(rgba)
        bg.convert('RGB').save(assets/f'reference/{view}-poster.jpg',quality=90)
    scoring=(HERE/'SCORING.md').read_text(encoding='utf-8')
    sections=re.split(r'^## (.+)$',scoring,flags=re.M)
    scoring_html=''.join('<details'+(' open' if i==1 else '')+'><summary>'+html.escape(sections[i])+'</summary><div class="detail-body">'+body(sections[i+1])+'</div></details>' for i in range(1,len(sections),2))
    audio=[('air_long','持续气流'),('air_low','低频气流'),('feather_rustle','羽片摩擦'),('sweep_broad','宽幅扫风'),('sweep_light','轻扫风')]
    players=''.join(f'<figure><figcaption><strong>{name}</strong><span>{label}</span></figcaption><audio controls preload="metadata" aria-label="试听 {name}" src="assets/audio/{name}.wav"></audio></figure>' for name,label in audio)
    page=(HERE/'index.html').read_text(encoding='utf-8')
    for marker,value in {'PACKAGE_SIZE':f'{archive.stat().st_size/1024**2:.1f} MB','TASK_TEXT':html.escape((candidate/'TASK.md').read_text(encoding='utf-8')),'SCORING_DETAILS':scoring_html,'AUDIO_PLAYERS':players}.items():
        page=page.replace('<!--'+marker+'-->',value)
    (site/'index.html').write_text(page,encoding='utf-8')
    write_json(site/'manifest.json',{'version':'phoenix-multiview-v2','files':[{'path':p.relative_to(site).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(site.rglob('*')) if p.is_file() and p.name!='manifest.json']})
    for page_path in [HERE.parent/'index.html',site.parent/'index.html']:
        text=page_path.read_text(encoding='utf-8')
        if 'href="v2/index.html"' not in text:
            text=text.replace('</nav>','<a href="v2/index.html">V2 · 六秒变速拍翼题目 →</a></nav>',1)
            page_path.write_text(text,encoding='utf-8')
    catalog_path=a.repo/'docs/index.html';catalog=catalog_path.read_text(encoding='utf-8')
    old='<a class="case-card" href="phoenix-reconstruction/">'
    if old in catalog:
        start=catalog.index(old);end=catalog.index('</a>',start)+4
        card=catalog[start:end]
        card=card.replace('href="phoenix-reconstruction/"','href="phoenix-reconstruction/v2/"',1)
        card=card.replace('phoenix-reconstruction/results/astra62-xhigh/poster.jpg','phoenix-reconstruction/v2/assets/reference/I1-poster.jpg')
        card=card.replace('根据三个同步录像重建凤凰形体、材质与骨骼动画，补制指定新机位的有声镜头。查看真实交付、十帧几何与外观指标，以及音效评审原始 JSON。',
                          '根据三个同步录像重建六秒凤凰动画，恢复连续变化的拍翼节奏与幅度，并为单一目标机位制作声音。原版题目与历史成绩保留在版本入口。')
        card=card.replace('Astra 6.2 xhigh + Codex · 34.43 / 100','V2 · 六秒变速拍翼 · 尚未运行模型实验')
        card=card.replace('查看任务、动画和评分 →','查看新版题目、输入和评分机制 →')
        catalog_path.write_text(catalog[:start]+card+catalog[end:],encoding='utf-8')
    parent=site.parent
    write_json(parent/'manifest.json',{'case':'phoenix-reconstruction','files':[{'file':p.relative_to(parent).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(parent.rglob('*')) if p.is_file() and p.name!='manifest.json']})
    print(json.dumps({'input_files':len(NAMES),'input_zip_bytes':archive.stat().st_size,'page':str(site/'index.html'),'model_runs':0},ensure_ascii=True,indent=2))
if __name__=='__main__':main()
