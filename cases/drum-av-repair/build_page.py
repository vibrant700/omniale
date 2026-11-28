"""Build the public drum case from the reviewed release bundle.

Usage: python build_page.py --bundle ABS_PATH --ffmpeg ABS_PATH
Never publishes the hidden full reference, injection script or raw model logs.
"""
from pathlib import Path
import argparse
import html
import json
import re
import shutil
import subprocess
import zipfile
import hashlib

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
SITE=REPO/'docs/drum-av-repair'
TITLES=['轻击与换鼓','快速交替节奏','弱奏与滚奏','快速过门','高潮与镲片切换']
ANALYSIS=[
 ['主要军鼓重拍与可见动作基本对应，轻击与装饰音细节有所简化。','进入和退出没有明显点击；连续轻击之间仍有采样拼接的生硬感。','相对前后正常录音略偏干、偏薄，尾声和重复采样影响现场感。'],
 ['主要军鼓击打多处对应；部分可见重击缺失或偏弱，收尾重音不足。','两端衔接自然，片段内部仍有轻微拼接质感。','五处中鼓组音色较自然，连续击打的样本重复仍可辨。'],
 ['双棒持续在中央军鼓，单打转滚奏的结构基本保留，前半段动态与单击清晰度不足。','进入修复段时能量下降明显，退出相对自然；段内仍有拼贴感。','前半段声音较薄、较闷，滚奏保留部分现场质感。'],
 ['快速军鼓连击中出现空档，连续数次左上镲击缺少对应镲声；右侧部分动作对应较好。','进入和退出均有质感变化，段内快速过门拼接有明显断裂。','密集叠层拥挤，连续击打存在机械重复和镲片叠层伪影。'],
 ['右侧与高潮主拍大致对应，左侧大镲多处缺失或偏弱，双臂重击爆发力不足。','入口自然，出口镲片密度略有变化；段内有轻微拼贴感。','高潮镲片延音较浑浊，现场音色与动态层次仍有差距。']
]

def dump(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def cmd(ff,*args):subprocess.run([str(ff),'-hide_banner','-loglevel','error','-y',*map(str,args)],check=True)
def copy(src,dst):
    dst.parent.mkdir(parents=True,exist_ok=True)
    if not dst.exists() or hashlib.sha256(src.read_bytes()).digest()!=hashlib.sha256(dst.read_bytes()).digest():shutil.copy2(src,dst)
def preview(ff,src,dst):
    if dst.exists() and dst.stat().st_mtime>=src.stat().st_mtime:return
    cmd(ff,'-i',src,'-map','0:v:0','-map','0:a:0','-c:v','copy','-c:a','aac','-b:a','256k','-movflags','+faststart',dst)
def poster(ff,src,t,dst):
    if not dst.exists():cmd(ff,'-ss',t,'-i',src,'-frames:v','1','-vf','scale=1278:-1','-q:v','3',dst)
def zipfiles(out,files):
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for source,name in files:z.write(source,name)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--bundle',type=Path,required=True);ap.add_argument('--ffmpeg',type=Path,required=True);args=ap.parse_args()
    bundle=args.bundle.resolve();ff=args.ffmpeg.resolve();assets=SITE/'assets';clips=assets/'clips';clips.mkdir(parents=True,exist_ok=True)
    sub=bundle/'submission_astra62';ev=bundle/'evaluation'
    score=json.loads((ev/'score_summary.json').read_text(encoding='utf-8'))
    diag=json.loads((ev/'objective_diag.json').read_text(encoding='utf-8'))
    review=json.loads((ev/'subjective_review.json').read_text(encoding='utf-8'))
    for name in ['style.css','app.js']:copy(HERE/name,SITE/name)
    for name in ['TASK.md','TOOLS.md']:copy(bundle/'candidate'/name,assets/name)
    copy(bundle/'candidate/media/test_corrupted.mp4',assets/'input.mp4')
    copy(bundle/'candidate/media/test_corrupted.wav',assets/'input.wav')
    copy(sub/'repaired.wav',assets/'repaired.wav');copy(sub/'changes.json',assets/'changes.json')
    preview(ff,sub/'repaired.mp4',assets/'repaired-preview.mp4')
    for name,t in [('hero.jpg',70.8),('input-poster.jpg',2.8),('result-poster.jpg',69.8)]:poster(ff,sub/'repaired.mp4',t,assets/name)
    zipfiles(assets/'candidate.zip',[(p,'candidate/'+p.relative_to(bundle/'candidate').as_posix()) for p in (bundle/'candidate').rglob('*') if p.is_file()])
    project=[(sub/'repair.rpp','repair.rpp'),(sub/'changes.json','changes.json')]+[(p,p.relative_to(sub).as_posix()) for p in (sub/'assets').rglob('*') if p.is_file() and p.suffix not in ['.reapeaks','.log']]
    zipfiles(assets/'reaper-project.zip',project)
    regions=[]
    for i,(eid,s) in enumerate(review['spots'].items()):
        support=s['support_sec'];w=[round(support[0]-1.5,2),round(support[1]+1.5,2)];local=[1.5,round(support[1]-support[0]+1.5,2)];result=score['per_spot'][eid]
        for kind in ['reference','repaired']:preview(ff,ev/'clips'/f'{eid}_{kind}.mp4',clips/f'{eid}-{kind}.mp4')
        corrupt=clips/f'{eid}-corrupted.mp4'
        if not corrupt.exists():cmd(ff,'-ss',w[0],'-i',bundle/'candidate/media/test_corrupted.mp4','-t',w[1]-w[0],'-map','0:v:0','-map','0:a:0','-c:v','libx264','-preset','fast','-crf','18','-c:a','aac','-b:a','256k','-movflags','+faststart',corrupt)
        poster(ff,ev/s['clip_repaired'],max(1.6,local[0]+.4),assets/f'{eid}-poster.jpg')
        regions.append(dict(id=eid,title=TITLES[i],window=w,local=local,support=[round(w[0]+local[0],2),round(w[0]+local[1],2)],media={k:f'assets/clips/{eid}-{k}.mp4' for k in ['reference','repaired','corrupted']},scores=dict(correspondence=result['correspondence']['subtotal'],blending=result['blending']['subtotal'],quality=result['quality']['subtotal'],total=result['spot_total_18']),analysis=ANALYSIS[i],diagnostics=diag[eid]))
    data=dict(title='Drum AV Repair',solver='gpt-6.2-astra',effort='xhigh',framework='Codex CLI 0.142.4',total=score['grand_total_100'],regions=regions)
    dump(assets/'case-data.json',data)
    public_score={k:v for k,v in score.items() if k not in ['calibration_baselines','reconstruction_90']};public_score['judge_roles']=score['judge_roles']
    dump(assets/'score-summary.json',public_score)
    copy(HERE/'SCORING.md',assets/'scoring.md')
    (assets/'favicon.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40"><rect width="40" height="40" rx="6" fill="#315c48"/><circle cx="20" cy="20" r="11" fill="none" stroke="#f7f7f0" stroke-width="3"/></svg>',encoding='utf-8')
    page=(HERE/'index.template.html').read_text(encoding='utf-8')
    bars=[]
    for key,label,mx in [('localization_10','五处定位',10),('correspondence_50','演奏与声音对应',50),('blending_20','自然衔接与连续性',20),('quality_20','同源音色与无新增伪影',20)]:
        value=score[key];bars.append(f'<div class="bar-row"><div class="bar-label"><span>{label}</span><b>{value:.2f} / {mx:g}</b></div><div class="bar-track" role="meter" aria-label="{label}" aria-valuemin="0" aria-valuemax="{mx}" aria-valuenow="{value}"><i style="width:{value/mx*100:.3f}%"></i></div></div>')
    rows=[];buttons=[]
    for i,r in enumerate(regions):
        s=r['scores'];rows.append(f'<tr><th scope="row"><a href="#comparison" data-jump="{i}">{r["id"]} · {r["title"]}</a></th><td>{r["support"][0]:.2f}–{r["support"][1]:.2f} s</td><td>{s["correspondence"]:.2f}</td><td>{s["blending"]:.2f}</td><td>{s["quality"]:.2f}</td><td class="total-cell">{s["total"]:.2f}</td></tr>')
        buttons.append(f'<button type="button" data-region="{i}" aria-pressed="{"true" if i==0 else "false"}"><strong>{r["id"]} · {r["title"]}</strong><span>{r["support"][0]:.2f}–{r["support"][1]:.2f} s</span></button>')
    first=regions[0];fs=first['scores'];metrics=''.join(f'<div><strong>{v:.2f}</strong><span>{label}</span></div>' for v,label in [(fs['total'],'本段得分 / 18'),(fs['correspondence'],'演奏与声音对应 / 10'),(fs['blending'],'自然衔接 / 4'),(fs['quality'],'同源音色与伪影 / 4')])
    replacements=dict(CORRESPONDENCE=f'{score["correspondence_50"]:.2f}',TASK=html.escape((assets/'TASK.md').read_text(encoding='utf-8')),TOTAL=f'{score["grand_total_100"]:.2f}',BARS=''.join(bars),SCORE_ROWS=''.join(rows),REGION_BUTTONS=''.join(buttons),INITIAL_METRICS=metrics,INITIAL_ANALYSIS=''.join('<li>'+html.escape(t)+'</li>' for t in first['analysis']))
    for k,v in replacements.items():page=page.replace('@@'+k+'@@',v)
    assert '@@' not in page
    (SITE/'index.html').write_text(page,encoding='utf-8')
    catalog=REPO/'docs/index.html';s=catalog.read_text(encoding='utf-8')
    if 'href="drum-av-repair/"' not in s:
        card='<a class="case-card" href="drum-av-repair/"><div class="case-cover" style="padding:0;background:#18231d"><img src="drum-av-repair/assets/hero.jpg" alt="现场架子鼓独奏的音画修复" style="width:100%;height:100%;object-fit:cover" loading="lazy"><span class="mono" style="position:absolute;left:14px;top:12px;background:#f5f6ef;padding:4px 8px">09 / DRUM AV REPAIR</span></div><div><div class="eyebrow">音视频联合理解与演奏拟音</div><h3>从演奏动作，完成五处拟音。</h3><p>在87秒现场独奏中定位五处错误配声，利用正常录音为击打与延音重新拟音，交付完整音轨、成片和可编辑 REAPER 工程。</p><div class="status"><span class="status-dot"></span>Astra 6.2 xhigh ＋ Codex · @@TOTAL@@ / 100</div><span class="enter">查看任务、五处对照和评分 →</span></div></a>'
        card=card.replace('@@TOTAL@@',f'{score["grand_total_100"]:.2f}')
        marker='<p class="catalog-note">';assert marker in s;s=s.replace(marker,card+marker,1)
        count=len(re.findall(r'class="case-card"',s));s=re.sub(r'\d+ CASES',f'{count:02d} CASES',s);catalog.write_text(s,encoding='utf-8')
    catalog_html=catalog.read_text(encoding='utf-8')
    catalog_html=re.sub(r'(<a class="case-card" href="drum-av-repair/">.*?</a>)',lambda m:m[0].replace('音视频联合理解与现场声音修复','音视频联合理解与演奏拟音').replace('从演奏动作，重建五处鼓声。','从演奏动作，完成五处拟音。').replace('利用正常录音重建击打与延音','利用正常录音为击打与延音重新拟音'),catalog_html,flags=re.S)
    catalog_html=re.sub(r'(<a class="case-card" href="drum-av-repair/">.*?Codex · )[\d.]+( / 100)',lambda m:m[1]+f'{score["grand_total_100"]:.2f}'+m[2],catalog_html,flags=re.S)
    catalog.write_text(catalog_html,encoding='utf-8')
    print(json.dumps(dict(site=str(SITE),files=sum(p.is_file() for p in SITE.rglob('*')),total_megabytes=round(sum(p.stat().st_size for p in SITE.rglob('*') if p.is_file())/1e6,1),score=score['grand_total_100']),ensure_ascii=False))

if __name__=='__main__':main()
