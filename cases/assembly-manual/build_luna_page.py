"""Add a sealed Luna delivery and a two-system comparison to the existing case."""
from pathlib import Path
from decimal import Decimal,ROUND_HALF_UP
import copy,hashlib,html,json,re,shutil,zipfile,os

ROOT=Path(os.environ['OMNIALE_ORGANIZER_ROOT']).resolve()
REPO=ROOT/'work/omniale-coach-publish'
BASE=REPO/'docs/assembly-manual'
PAGE=BASE/'luna'
RUN=ROOT/'outputs/HoloAssist_manual_v1/runs/luna-codex01'
SUB=RUN/'sealed-submission'
JUDGE=RUN/'annotation-primary-evaluation01'
PREP=RUN/'evaluation'
RELEASE=ROOT/'work/assembly-manual-release'
TEMPLATE=Path(__file__).with_name('site-template')
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

def compare(sol,luna,child=False):
    cards=[]
    for key,label,item in [('sol','GPT-6.1-Sol',sol),('luna','GPT-6-Luna',luna)]:
        target=('../' if key=='sol' else './') if child else ('./' if key=='sol' else 'luna/')
        active=(key=='luna')==child
        g=item['result']['groups'];seconds=int(round(item['solver']['elapsed_seconds']))
        detail=' · '.join(f'{name} {fmt(g[k]["score"])}' for name,k in [('问答','qa_semantic'),('证据','qa_evidence'),('手册','manual_delivery'),('设计','subjective_design')])
        cards.append(f'<a class="system-card{" active" if active else ""}" href="{target}"'+(' aria-current="page"' if active else '')+f'><span>{label} + Codex</span><strong>{item["result"]["score_display"]}<small> / 100</small></strong><p>{detail}</p><small>{seconds//60}分{seconds%60:02}秒 · {item["solver"]["tool_calls"]}次工具调用</small><b>{"当前展示" if active else "查看实际交付与逐题依据"} ↗</b></a>')
    return '<section id="systems"><div class="eyebrow">TESTED SYSTEMS / SAME TASK</div><h2>同一委托，分别交付。</h2><p class="caption">同一输入、隔离工具环境和50/20/20/10评分权重。两份交付分别验收；模型使用Codex目录默认推理强度：Sol为low，Luna为medium。共同源音频的Gemini核听结果复用于两个系统，事实计分以原标注为准。</p><div class="system-grid">'+''.join(cards)+'</div></section>'

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
    sol=load(BASE/'data.json');data=copy.deepcopy(sol)
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
    data['source']['preview']='../assets/recording-preview.mp4'
    data['scoring']['audio_reuse']='The same immutable source-audio observations are shared across systems; artifact and document judgments are fresh.'
    dump(PAGE/'data.json',data)
    score=data['result']['score_display'];secs=int(round(record['elapsed_seconds']));duration=f'{secs//60}分{secs%60:02}秒'
    page=(TEMPLATE/'index.html').read_text(encoding='utf8').replace('gpt-6.1-sol','gpt-6-luna').replace('GPT-6.1-sol','GPT-6-Luna').replace('GPT-6.1-SOL','GPT-6-LUNA').replace('63.11',score)
    page=page.replace('<title>装配录像核查与图解手册 · OmniALE</title>','<title>装配录像核查与图解手册 · GPT-6-Luna · OmniALE</title>')
    page=page.replace('results/sol/','results/luna/').replace('/sol-manual.docx','/luna-manual.docx').replace('/sol-editable-delivery.zip','/luna-editable-delivery.zip')
    page=page.replace('九页',f'{n}页').replace('9页',f'{n}页').replace('>9<small>页','>'+str(n)+'<small>页').replace('<b>9</b>','<b>'+str(n)+'</b>')
    figure_groups=sum(p.suffix.lower()=='.svg' for p in assets)
    page=page.replace('26张标注截图',f'{figure_groups}组标注配图').replace('26张原始截图与SVG标注源',f'{figure_groups}组原图、标注预览与SVG源').replace('26 张原始截图及SVG源',f'{figure_groups} 组配图素材').replace('<b>26</b>','<b>'+str(figure_groups)+'</b>').replace('张原始截图及SVG源','组原图、标注预览及SVG源')
    page=page.replace('约103分15秒','约'+duration).replace('241次工具调用',str(record['tool_calls'])+'次工具调用')
    page=page.replace('交付完整，事件对应仍是主要失分处。','查看实际交付与各项评分。')
    hardest=sorted(questions,key=lambda q:q['score'])[:2]
    page=re.sub(r'<div class="readout">.*?</div>', '<div class="readout"><span>RESULT AT A GLANCE</span><p>本次主要扣分题目为 '+ '、'.join(q['id']+'「'+html.escape(q['title'])+'」' for q in hardest)+'。实际答案、源标注及分项依据均可在下方逐题展开查看。</p></div>',page,flags=re.S)
    options=''.join(f'<option value="{i}">第{i}页 · 实际交付</option>' for i in range(1,n+1))
    page=re.sub(r'(<select id="manual-page"[^>]*>).*?(</select>)',lambda m:m[1]+options+m[2],page,flags=re.S).replace('01 / 09','01 / '+str(n).zfill(2))
    # Shared public source material is served once, beside the child result page.
    page=page.replace('href="../"','href="../../"').replace('href="../coach-review/"','href="../../coach-review/"')
    for name in ['TASK.zh-CN.md','SCORING.zh-CN.md','public-task.zip','questions.md','CDLA-Permissive-2.0.txt']:
        page=page.replace('href="'+name+'"','href="../'+name+'"')
    page=page.replace('src="assets/','src="../assets/').replace('poster="assets/','poster="../assets/')
    page=page.replace('<section id="deliverable">',compare(sol,data,True)+'\n<section id="deliverable">')
    (PAGE/'index.html').write_text(page,encoding='utf8')
    js=(TEMPLATE/'app.js').read_text(encoding='utf8').replace('results/sol/','results/luna/')
    js=re.sub(r"const topics=\[.*?\];",'const topics='+json.dumps([f'实际交付第{i}页' for i in range(1,n+1)],ensure_ascii=False)+';',js)
    js=js.replace('Math.min(9,Number(n))',f'Math.min({n},Number(n))').replace('page===9',f'page==={n}').replace('n<=9',f'n<={n}').replace(' / 09',' / '+str(n).zfill(2))
    (PAGE/'app.js').write_text(js,encoding='utf8')
    extra='\n.system-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}.system-card{display:flex;flex-direction:column;padding:26px;border:1px solid var(--line);background:var(--paper);text-decoration:none}.system-card.active{border-color:var(--green);box-shadow:inset 0 3px var(--green)}.system-card>span{font-size:13px;font-weight:600}.system-card>strong{font-size:42px;line-height:1.6;font-weight:500}.system-card>strong small{font-size:12px;color:var(--muted)}.system-card p,.system-card>small{font-size:11px;color:var(--muted)}.system-card>b{font-size:11px;margin-top:16px}.system-card:hover{background:var(--soft)}@media(max-width:650px){.system-grid{grid-template-columns:1fr}.system-card{padding:21px}}\n'
    css=(TEMPLATE/'case.css').read_text(encoding='utf8')+extra
    (PAGE/'case.css').write_text(css,encoding='utf8');(BASE/'case.css').write_text(css,encoding='utf8')
    root=(TEMPLATE/'index.html').read_text(encoding='utf8').replace('<section id="deliverable">',compare(sol,data)+'\n<section id="deliverable">')
    (BASE/'index.html').write_text(root,encoding='utf8')
    sol['comparison']=[{'model':s['solver']['model'],'score':s['result']['score'],'score_display':s['result']['score_display'],'url':'./' if s is sol else 'luna/'} for s in [sol,data]]
    dump(BASE/'data.json',sol)
    catalog=REPO/'docs/index.html';text=catalog.read_text(encoding='utf8')
    text=text.replace('GPT-6.1-sol + Codex · 63.11 / 100 · 9页图解手册',f'Sol 63.11 · Luna {score} · 含实际手册与逐题评分')
    catalog.write_text(text,encoding='utf8')
    public=REPO/'cases/assembly-manual/build_luna_page.py'
    code=Path(__file__).read_text(encoding='utf8').replace('import copy,hashlib,html,json,re,shutil,zipfile,os','import copy,hashlib,html,json,re,shutil,zipfile,os,os').replace('ROOT=Path(os.environ['OMNIALE_ORGANIZER_ROOT']).resolve()',"ROOT=Path(os.environ['OMNIALE_ORGANIZER_ROOT']).resolve()")
    public.write_text(code,encoding='utf8')
    manifest={'model':'gpt-6-luna','score':score,'assets':[{'name':p.name,'bytes':p.stat().st_size,'sha256':sha(p)} for p in [RELEASE/'luna-manual.docx',bundle]]}
    dump(RELEASE/'luna-release-manifest.json',manifest)
    print(json.dumps({'score':score,'pages':n,'figure_assets':len(assets),'bundle_MB':round(bundle.stat().st_size/1e6,2),'page':str(PAGE)},ensure_ascii=False))

if __name__=='__main__':main()
