"""Publish both sealed systems in one case page with synchronized selection."""
from pathlib import Path
from decimal import Decimal,ROUND_HALF_UP
import copy,hashlib,html,json,re,shutil,zipfile,os

ROOT=Path(os.environ['OMNIALE_ORGANIZER_ROOT']).resolve()
REPO=ROOT/'work/omniale-coach-publish'
BASE=REPO/'docs/assembly-manual'
PAGE=BASE
RUN=ROOT/'outputs/HoloAssist_manual_v1/runs/luna-codex01'
SUB=RUN/'sealed-submission'
JUDGE=RUN/'annotation-primary-evaluation01'
PREP=RUN/'evaluation'
RELEASE=ROOT/'work/assembly-manual-release'
TEMPLATE=Path(__file__).with_name('comparison-template')
URL='https://github.com/vibrant700/omniale/releases/download/assembly-manual-v1/'

def load(p):return json.loads(p.read_text(encoding='utf8'))
def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def fmt(n):return str(Decimal(str(n)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP))
def clean(s):
    return re.sub(r'(?<!重)复评','评审',str(s).replace('本轮','本次评审').replace('重新评审','评审').replace('，也不导致待定','').replace('不重复评判','不再评判'))
def clean_tree(v):
    if isinstance(v,dict):return {k:clean_tree(x) for k,x in v.items()}
    if isinstance(v,list):return [clean_tree(x) for x in v]
    return clean(v) if isinstance(v,str) else v
def parts(text):
    matches=list(re.finditer(r'(?m)^#{1,6}\s+(Q(?:0[1-9]|10))\b[^\n]*$',text))
    return {m[1]:text[m.end():matches[n+1].start() if n+1<len(matches) else len(text)].strip() for n,m in enumerate(matches)}

def compare(sol,luna):
    cards=[]
    for key,label,item in [('sol','GPT-6.1-Sol',sol),('luna','GPT-6-Luna',luna)]:
        active=key=='sol';g=item['result']['groups'];seconds=int(round(item['solver']['elapsed_seconds']))
        detail=' · '.join(f'{name} {fmt(g[k]["score"])}' for name,k in [('问答','qa_semantic'),('证据','qa_evidence'),('手册','manual_delivery'),('设计','subjective_design')])
        cards.append(f'<button type="button" id="select-{key}" class="system-card{" active" if active else ""}" data-system="{key}" aria-pressed="{str(active).lower()}" aria-controls="deliverable results questions document-review files" disabled><span>{label} + Codex</span><strong>{item["result"]["score_display"]}<small> / 100</small></strong><p>{detail}</p><small>{seconds//60}分{seconds%60:02}秒 · {item["solver"]["tool_calls"]}次工具调用</small><b>{"当前展示" if active else "切换手册与逐题评分 →"}</b></button>')
    return '<section id="systems"><div class="eyebrow">TESTED SYSTEMS / SAME TASK</div><h2>同一委托，分别交付。</h2><p class="caption">点击模型，在本页切换对应的手册、问答、评分和下载文件。同一输入、隔离工具环境和50/20/20/10评分权重；两份交付分别验收。模型采用目录默认推理强度：Sol为low，Luna为medium。共同源音频的Gemini核听结果复用于两个系统，事实计分以原标注为准。</p><div class="system-grid">'+''.join(cards)+'</div><p id="system-status" role="status" aria-live="polite">正在加载模型交付…</p></section>'

def main():
    result=load(JUDGE/'evaluation.json');record=load(RUN/'run_record.json');inspection=load(PREP/'inspection/inspection.json')
    assert not result['errors'] and result['pending_points']==0
    assert record['solver_model']=='gpt-6-luna' and record['status']=='solver_finished'
    expected=load(RUN/'submission_seal.json')['files']
    assert expected=={p.relative_to(SUB).as_posix():sha(p) for p in SUB.rglob('*') if p.is_file()}
    assert record['candidate_unchanged'] and record['evaluator_unchanged']
    n=inspection['pdf']['page_count'];assert n>0 and inspection['docx']['valid']
    for p in [PAGE,PAGE/'results/luna/pages',RELEASE]:p.mkdir(exist_ok=True,parents=True)
    for page in inspection['pdf']['pages']:shutil.copyfile(PREP/'inspection'/page['image'],PAGE/'results/luna/pages'/page['image'])
    shutil.copyfile(SUB/'manual.pdf',PAGE/'results/luna/manual.pdf')
    shutil.copyfile(RUN/'sealed-phase1/sealed-answers.md',PAGE/'results/luna/answers.md')
    shutil.copyfile(SUB/'manual.docx',RELEASE/'luna-manual.docx')
    bundle=RELEASE/'luna-editable-delivery.zip'
    if not bundle.exists():
        with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED,compresslevel=5) as z:
            for p in sorted(SUB.rglob('*')):
                if p.is_file():z.write(p,p.relative_to(SUB).as_posix())
    existing=load(BASE/'data.json');sol=copy.deepcopy(existing.get('systems',{}).get('sol',existing));sol.pop('comparison',None);data=copy.deepcopy(sol)
    answers=parts((RUN/'sealed-phase1/sealed-answers.md').read_text(encoding='utf-8-sig'))
    byid={q['id']:q for q in sol['result']['questions']};questions=[]
    for row in result['questions']:
        qid=row['qid'];v=clean_tree(load(JUDGE/(qid+'.json')));q=copy.deepcopy(byid[qid]);b=row['breakdown']
        q['answer']=answers[qid];q['score']=row['confirmed_points']
        q['scores']={'qa':b['qa_semantic']['confirmed'],'evidence':b['qa_evidence']['confirmed'],'manual':b['manual_facts']['confirmed']+b['manual_illustrations']['confirmed']}
        q['checks']={key:[{k:x[k] for k in ['id','status','evidence','pages','annotation_event_ids'] if k in x} for x in v[key]] for key in ['qa_claims','qa_evidence','manual_claims','illustration_checks']}
        q['page_numbers']=sorted({int(p) for key in ['manual_claims','illustration_checks'] for x in v[key] for p in x.get('pages',[]) if str(p).isdigit() and 1<=int(p)<=n})
        lower=sorted(v['qa_claims']+v['qa_evidence'],key=lambda x:{'fail':0,'partial':1,'pass':2}[x['status']])
        q['summary']=lower[0]['evidence'][:240]+('…' if len(lower[0]['evidence'])>240 else '')
        questions.append(q)
    data['solver']={'model':'gpt-6-luna','framework':'Official Codex CLI','version':'0.142.4','elapsed_seconds':record['elapsed_seconds'],'tool_calls':record['tool_calls'],'audio_tool':'whisper.cpp / base.en','local_asr_calls':record['asr_calls'],'time_limit':None,'tool_limit':None,'native_audio':False,'catalog_default_reasoning_effort':'medium'}
    data['result']={'score':result['confirmed_diagnostic_points'],'score_display':fmt(result['confirmed_diagnostic_points']),'maximum':100,'groups':{k:{'score':round(v['confirmed'],10),'maximum':round(v['maximum'],10)} for k,v in result['group_scores'].items()},'details':{k:{'score':round(v['confirmed'],10),'maximum':round(v['maximum'],10)} for k,v in result['detailed_scores'].items()},'questions':questions}
    assets=[p for p in SUB.rglob('*') if p.is_file() and p.suffix.lower() in ['.png','.jpg','.jpeg','.svg']]
    data['delivery']={'pages':n,'figure_asset_count':len(assets),'editable_svg':sum(p.suffix.lower()=='.svg' for p in assets),'pdf':'results/luna/manual.pdf','docx':URL+'luna-manual.docx','bundle':URL+bundle.name,'answers':'results/luna/answers.md','pdf_sha256':sha(SUB/'manual.pdf'),'docx_sha256':sha(SUB/'manual.docx'),'bundle_sha256':sha(bundle),'page_images':[f'results/luna/pages/page-{i:03}.png' for i in range(1,n+1)]}
    data['document_checks']=clean_tree(load(PREP/'document.json'))
    data['source']['preview']='assets/recording-preview.mp4'
    data['scoring']['audio_reuse']='The same immutable source-audio observations are shared across systems; artifact and document judgments are fresh.'
    sol['delivery']['page_topics']=['部件与查阅索引','侧框横条关系','底架连接阶段','托盘选用与返工','夹片中断与恢复','紧固问题与重试','剩余托盘','整体横放姿态','脚轮与两把工具']
    data['delivery']['page_topics']=[f'实际交付第{i}页' for i in range(1,n+1)]
    combined={'title':sol['title'],'slug':sol['slug'],'default_system':'sol','systems':{'sol':sol,'luna':data}}
    dump(BASE/'data.json',combined)
    page=(TEMPLATE/'index.html').read_text(encoding='utf8').replace('{{SYSTEM_COMPARISON}}',compare(sol,data))
    (BASE/'index.html').write_text(page,encoding='utf8')
    for name in ['app.js','case.css']:shutil.copyfile(TEMPLATE/name,BASE/name)
    # The old public URL remains a redirect; it no longer contains a second case page.
    legacy=BASE/'luna'
    legacy.mkdir(exist_ok=True)
    obsolete=['app.js','case.css','data.json','results/luna/manual.pdf','results/luna/answers.md']+[f'results/luna/pages/page-{i:03}.png' for i in range(1,7)]
    for relative in obsolete:
        target=(legacy/relative).resolve()
        assert target.is_relative_to(legacy.resolve())
        if target.is_file():target.unlink()
    for relative in ['results/luna/pages','results/luna','results']:
        target=(legacy/relative).resolve()
        assert target.is_relative_to(legacy.resolve())
        if target.is_dir() and not any(target.iterdir()):target.rmdir()
    (legacy/'index.html').write_text('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="0;url=../?model=luna#systems"><link rel="canonical" href="https://vibrant700.github.io/omniale/assembly-manual/?model=luna"><title>装配手册 · OmniALE</title></head><body><p>正在打开合并后的结果页。<a href="../?model=luna#systems">查看Luna结果</a></p></body></html>',encoding='utf8')
    catalog=REPO/'docs/index.html';text=catalog.read_text(encoding='utf8')
    score=data['result']['score_display']
    text=text.replace('GPT-6.1-sol + Codex · 63.11 / 100 · 9页图解手册',f'Sol 63.11 · Luna {score} · 同页查看手册与逐题评分').replace(f'Sol 63.11 · Luna {score} · 含实际手册与逐题评分',f'Sol 63.11 · Luna {score} · 同页查看手册与逐题评分')
    catalog.write_text(text,encoding='utf8')
    public=REPO/'cases/assembly-manual/build_luna_page.py'
    code=Path(__file__).read_text(encoding='utf8').replace('import copy,hashlib,html,json,re,shutil,zipfile,os','import copy,hashlib,html,json,re,shutil,zipfile,os,os').replace('ROOT=Path(os.environ['OMNIALE_ORGANIZER_ROOT']).resolve()',"ROOT=Path(os.environ['OMNIALE_ORGANIZER_ROOT']).resolve()")
    public.write_text(code,encoding='utf8')
    shutil.copytree(TEMPLATE,public.parent/'comparison-template',dirs_exist_ok=True)
    manifest={'model':'gpt-6-luna','score':score,'assets':[{'name':p.name,'bytes':p.stat().st_size,'sha256':sha(p)} for p in [RELEASE/'luna-manual.docx',bundle]]}
    dump(RELEASE/'luna-release-manifest.json',manifest)
    print(json.dumps({'scores':{k:d['result']['score_display'] for k,d in combined['systems'].items()},'pages':{k:d['delivery']['pages'] for k,d in combined['systems'].items()},'page':str(BASE)},ensure_ascii=False))

if __name__=='__main__':main()
