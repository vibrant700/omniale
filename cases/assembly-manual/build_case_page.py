"""Build an allowlisted public case page from sealed artifacts and final scores."""
from pathlib import Path
from decimal import Decimal,ROUND_HALF_UP
import hashlib,json,re,shutil,subprocess,zipfile,os

ROOT=Path(os.environ['OMNIALE_ORGANIZER_ROOT']).resolve()
REPO=ROOT/'work/omniale-coach-publish'
PACK=ROOT/'outputs/HoloAssist_manual_v1'
RUN=PACK/'runs/sol-codex01'
SUB=RUN/'recovery-phase2b/sealed-submission'
EVAL=RUN/'annotation-primary-evaluation01'
PAGE=REPO/'docs/assembly-manual'
CASE=REPO/'cases/assembly-manual'
RELEASE=ROOT/'work/assembly-manual-release'
FF=ROOT/'work/media-runtime/shotcut/Shotcut/ffmpeg.exe'
FP=FF.with_name('ffprobe.exe')
SOURCE=ROOT/'work/holoassist-task-design/selected-z057/z057-june-28-22-rashult_assemble.mp4'
TAG='assembly-manual-v1'
RELEASE_URL=f'https://github.com/vibrant700/omniale/releases/download/{TAG}/'

def load(p):return json.loads(p.read_text(encoding='utf8'))
def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(2**20),b''):h.update(chunk)
 return h.hexdigest()
def fmt(n):return str(Decimal(str(n)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP))
def run(args):subprocess.run([str(FF),'-v','error','-y',*map(str,args)],check=True,capture_output=True)
def clean(text):
 return str(text).replace('本轮','本次评审').replace('重新评审','评审').replace('复评','评审').replace('，也不导致待定','')
def main():
 for p in [PAGE,CASE,RELEASE,PAGE/'assets',PAGE/'results/sol',PAGE/'results/sol/pages'] :p.mkdir(parents=True,exist_ok=True)
 expected=load(RUN/'recovery-phase2b/submission_seal.json')['files']
 assert expected=={p.relative_to(SUB).as_posix():sha(p) for p in SUB.rglob('*') if p.is_file()}
 score=load(EVAL/'evaluation.json');record=load(RUN/'run_record.json')
 assert score['pending_points']==0 and not score['errors']
 questions_text=(PACK/'agent-input/questions.md').read_text(encoding='utf8')
 prompts={m[1]:(m[2],m[3].strip()) for m in re.finditer(r'## (Q\d{2}) ([^\n]+)\n(.*?)(?=\n## Q|\Z)',questions_text,re.S)}
 rubric=load(PACK/'private/rubric.json');answers=(RUN/'sealed-phase1/sealed-answers.md').read_text(encoding='utf8')
 q_pages={'Q01':[4],'Q02':[2],'Q03':[3],'Q04':[6],'Q05':[7],'Q06':[8],'Q07':[6],'Q08':[5],'Q09':[9],'Q10':[1,7]}
 anchors={'Q01':450,'Q02':39,'Q03':216,'Q04':348,'Q05':722,'Q06':760,'Q07':547,'Q08':632,'Q09':1030,'Q10':738}
 summaries={
 'Q01':'找到了早先选盘与返工的联系；附近另一次拿盘的独立纠正、拆卸与重新装入的阶段仍有遗漏。',
 'Q02':'理解横条应分处两端，但将多轮拆开、翻转与重接压缩，部件指代和中间状态不够完整。',
 'Q03':'识别先组底部、再接侧框的阶段变化；具体动作与语音的逐段定位仍有偏差。',
 'Q04':'遗漏小紧固件选择错误和先装支架的依赖关系，将正常操作泛化为连接不顺。',
 'Q05':'区分选件、放入和固定要求；时间区间偏宽，部分阶段及执行对象未完全对应。',
 'Q06':'抓住整体横放与长侧支承的目标；对提醒时所持对象、实际移动过程的描述仍不够准确。',
 'Q07':'未识别两次共同的“尚需装支架，却先处理螺丝”错误，替代时段包含正常紧固。',
 'Q08':'把451—468秒的架体、轮子和托盘操作写成掉落恢复，错过637—644秒的明确动作链。',
 'Q09':'正确解释追加“两把扳手”，但第二次提醒时间偏后，并把提醒后的拿工具写到提醒前。',
 'Q10':'正确辨认手持夹片，然而重复提醒后的拿盘、装盘响应被定位到更晚的另一段动作。'}
 qrows=[]
 for row in score['questions']:
  qid=row['qid'];verdict=load(EVAL/(qid+'.json'));q=next(q for q in rubric['questions'] if q['qid']==qid)
  section=answers.split('## '+qid,1)[1].split('\n## ',1)[0].strip()
  checks={}
  for key in ['qa_claims','qa_evidence','manual_claims','illustration_checks']:
   checks[key]=[{k:clean(i[k]) if k=='evidence' else i[k] for k in ['id','status','evidence','pages','annotation_event_ids'] if k in i} for i in verdict[key]]
  b=row['breakdown']
  qrows.append({'id':qid,'title':prompts[qid][0],'question':prompts[qid][1],'answer':section,'summary':summaries[qid],
   'score':row['confirmed_points'],'maximum':8.4,'scores':{'qa':b['qa_semantic']['confirmed'],'evidence':b['qa_evidence']['confirmed'],'manual':b['manual_facts']['confirmed']+b['manual_illustrations']['confirmed']},
   'page_numbers':q_pages[qid],'source_start':anchors[qid],'annotation_basis':q['annotation_supported_answer'],'checks':checks})
 for p in sorted((RUN/'recovery-phase2b/evaluation/inspection').glob('page-*.png')):shutil.copy2(p,PAGE/'results/sol/pages'/p.name)
 shutil.copy2(SUB/'manual.pdf',PAGE/'results/sol/manual.pdf')
 shutil.copy2(RUN/'sealed-phase1/sealed-answers.md',PAGE/'results/sol/answers.md')
 shutil.copy2(SUB/'manual.docx',RELEASE/'sol-manual.docx')
 bundle=RELEASE/'sol-editable-delivery.zip'
 if not bundle.exists():
  with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED,compresslevel=5) as z:
   for p in sorted(SUB.rglob('*')):
    if p.is_file():z.write(p,p.relative_to(SUB).as_posix())
 preview=PAGE/'assets/recording-preview.mp4'
 if not preview.exists():
  print('Encoding full video preview',flush=True)
  run(['-threads',3,'-i',SOURCE,'-map','0:v:0','-map','0:a:0','-map_metadata',-1,'-vf','scale=704:-2,fps=12','-c:v','libx264','-threads',3,'-preset','fast','-crf',29,'-c:a','copy','-movflags','+faststart',preview])
 assert preview.stat().st_size<95_000_000
 run(['-ss',750,'-i',SOURCE,'-frames:v',1,'-q:v',2,PAGE/'assets/poster.jpg'])
 for stamp,name in [(451,'early-tray'),(638.3,'bracket-drop'),(750,'bracket-in-hand'),(1045,'two-wrenches')]:
  run(['-ss',stamp,'-i',SOURCE,'-frames:v',1,'-q:v',2,PAGE/'assets'/(name+'.jpg')])
 # Compact actual manual cover for the catalog / social image.
 from PIL import Image
 with Image.open(PAGE/'results/sol/pages/page-001.png') as im:im.convert('RGB').save(PAGE/'assets/manual-cover.jpg',quality=88)
 source_info=json.loads(subprocess.check_output([str(FP),'-v','error','-show_entries','format=duration:stream=codec_type,codec_name,width,height,sample_rate,channels','-of','json',str(SOURCE)]))
 elapsed=(record.get('elapsed_seconds') or 0)+(record.get('phase2_elapsed_seconds') or 0)
 groups={k:{'score':round(v['confirmed'],10),'maximum':round(v['maximum'],10)} for k,v in score['group_scores'].items()}
 details={k:{'score':round(v['confirmed'],10),'maximum':round(v['maximum'],10)} for k,v in score['detailed_scores'].items()}
 data={'title':'装配录像核查与图解手册','slug':'assembly-manual','solver':{'model':'gpt-6.1-sol','framework':'Official Codex CLI','version':'0.142.4','elapsed_seconds':elapsed,'tool_calls':record['tool_calls'],'audio_tool':'whisper.cpp / base.en','local_asr_calls':record['asr_calls'],'time_limit':None,'tool_limit':None,'native_audio':False},
  'result':{'score':score['confirmed_diagnostic_points'],'score_display':fmt(score['confirmed_diagnostic_points']),'maximum':100,'groups':groups,'details':details,'questions':qrows},
  'delivery':{'pages':9,'original_screenshots':26,'editable_svg':26,'pdf':'results/sol/manual.pdf','docx':RELEASE_URL+'sol-manual.docx','bundle':RELEASE_URL+'sol-editable-delivery.zip','answers':'results/sol/answers.md','pdf_sha256':sha(SUB/'manual.pdf'),'docx_sha256':sha(SUB/'manual.docx'),'bundle_sha256':sha(bundle),'page_images':[f'results/sol/pages/page-{n:03}.png' for n in range(1,10)]},
  'source':{'dataset':'HoloAssist','id':'z057-june-28-22-rashult_assemble','project_url':'https://holoassist.github.io/','duration':float(source_info['format']['duration']),'license':'CDLA-Permissive-2.0','preview':'assets/recording-preview.mp4','original':RELEASE_URL+'z057-june-28-22-rashult_assemble.mp4','sha256':sha(SOURCE),'preview_sha256':sha(preview),'preview_processing':'704px宽，12fps，原AAC音轨直接复制；完整时长。','original_media':source_info},
  'scoring':{'fact_authority':'原数据集动作、语音、时间与纠正关联标注','judge':'gpt-6-astra','audio_observer':'gemini-3.1-pro-preview','aggregation':'脚本校验逐项字段、换算源时间并按固定权重汇总。','unit_policy':'pass全分、partial半分、fail零分。','scope':'本页分数对应这一段录像、这一份交付及本页列明的评分口径。','note':'模型评分；未进行人工盲评。十题共享部分事件，不能视作十个独立样本。'},
  'document_checks':json.loads((RUN/'hybrid-evaluation01/document.json').read_text(encoding='utf8').replace('不重复评判','不再评判'))}
 # Only explicitly selected public evidence is exported, never raw provider responses.
 dump(PAGE/'data.json',data)
 dump(PAGE/'questions.json',[{'id':q['id'],'title':q['title'],'question':q['question']} for q in qrows])
 task='''# 委托：装配录像核查与图解培训资料

## 委托目标

培训部门希望把一次远程指导的推车装配录像整理成新员工可查阅的操作与纠错手册。请先回答十题核查单，再根据结论制作带标注截图的手册，帮助读者辨认部件、理解各阶段的要求，并在遇到典型问题时知道检查什么、怎样处理。

## 提供资料

- **完整音视频**：HoloAssist公开变调版本的18分31秒推车装配录像，包含第一人称操作画面和英文远程指导语音。
- **十题核查单**（`questions.md`）：需要结合画面与语音回答的十个问题。
- **空白答案模板**（`answers-template.md`）：供填写各题结论、证据及无法确认的部分。
- **素材来源与许可**：说明录像来源及使用许可。

不提供参考答案、语音转录、事件时间锚点或手册初稿。输入录像单独下载，下载链接见题包中的`VIDEO.md`。

录像包含错误尝试、指导者的提醒和后续纠正。请结合画面与语音，区分错误操作、指导要求和实际执行情况，再整理成手册；不能把录像中的所有实际动作都当作正确示范。

## 任务要求

1. **核查十题**：结合完整画面和英文语音，分清部件、指导对象、操作阶段、错误与后续处理。每题给出结论及源录像时间；相似事件分别定位，说明动作与语音如何对应。录像无法确认的部分应明确说明，不要用常识补写规格或完成状态。
2. **制作图解手册**：从零制作，不提供初稿。根据核查结果组织操作与纠错主题，可合并相关题目，让读者能查阅和理解实际操作要求。
3. **选图并标注**：自行选取关键视频截图，以箭头、框或简短标签标明对象、方向和状态，图注标出源时间。说明动作顺序时提供必要的前后画面；引用口头要求时说明语义及声音时间。

不限定手册页数、截图数量或工具调用顺序。可以使用Word、LibreOffice或其他可靠的文档制作与导出工具。

## 交付内容

| 交付项 | 内容与要求 |
|---|---|
| `answers.md` | 十题核查结果，包含结论、画面与语音证据、源录像时间及无法确认的部分。 |
| `manual.docx` | 可编辑的图解操作与纠错手册；正文可直接编辑，配图嵌入文档，落实十题核查结论。 |
| `manual.pdf` | 与Word手册内容一致、能正常打开与显示的PDF版本。 |
| 原始截图 | 手册所用截图的未标注版本。 |
| 可编辑标注源文件 | 保留箭头、框、标签等标注的编辑能力，可使用文档原生形状、SVG等形式。 |
'''
 (PAGE/'TASK.zh-CN.md').write_text(task,encoding='utf8')
 scoring='''# 评分规则

事实真值采用HoloAssist原数据集的动作、错误与纠正标签、Conversation语音转录、源时间及sequence关联。按固定50/20/20/10权重评价实际提交。

| 维度 | 分值 | 评价内容 |
|---|---:|---|
| 十题结论与关系 | 50 | 每题四条等权命题，核对对象、语义、阶段与因果关系 |
| 证据时间与动作语音配对 | 20 | 每题定位、配对、具体性三项等权 |
| 手册综合交付 | 20 | 事实落实6、图文证据8、基本可用性2、可编辑及导出4 |
| 美观与教学引导 | 10 | 视觉层级、布局、字体配色、教学顺序、关键点引导各2分 |

语义与图文由GPT-6-astra逐项评审，pass全分、partial半分、fail零分。设计五项各按0—4等级换算成2分。脚本负责时间格式换算、文件检查、字段校验和固定权重汇总。

Gemini 3.1 Pro Preview核听实际源音频；标注与听音冲突时，计分以原标注为准。求解器使用本地Whisper辅助理解音频，评委只在交付封存后介入。

问答与手册分别看实际内容；手册可以修正问答。截图来源、箭头指向、图文支持与前后过程证据分别评价。正确的文字不能弥补错取事件，图片确有出处也不意味着图注和结论正确。

公开题面允许的替代实例，应检查其实际对应标注，不能仅因不同于作者候选秒数而自动判错。缺少标注不能用来证明整个过程绝对静音，也不能从某一次动作推断整车完成验收。

分数按原始精度求和后四舍五入展示；逐项显示值可能存在末位舍入差。该结果对应本页列出的任务与受测系统，不与其他案例直接排名。
'''
 (PAGE/'SCORING.zh-CN.md').write_text(scoring,encoding='utf8')
 for name in ['questions.md','answers-template.md','SOURCE_NOTICE.md','CDLA-Permissive-2.0.txt']:shutil.copy2(PACK/'agent-input'/name,PAGE/name)
 with zipfile.ZipFile(PAGE/'public-task.zip','w',zipfile.ZIP_DEFLATED) as z:
  for name in ['TASK.zh-CN.md','SCORING.zh-CN.md','questions.md','answers-template.md','SOURCE_NOTICE.md','CDLA-Permissive-2.0.txt']:z.write(PAGE/name,name)
  z.writestr('VIDEO.md',f'# 输入录像\n\n[下载完整原始录像]({RELEASE_URL}z057-june-28-22-rashult_assemble.mp4)\n\nSHA256: {sha(SOURCE)}\n')
 readme=f'''# 装配录像核查与图解手册

展示页：https://vibrant700.github.io/omniale/assembly-manual/

输入：HoloAssist公开变调版推车装配录像，18分31秒，英文指导与第一人称画面；十题中文核查单。输出：问答、9页Word/PDF手册、26张原始截图与26份SVG标注源。

受测：gpt-6.1-sol＋Official Codex CLI 0.142.4，累计模型与工具运行约103分15秒，无人为总时长和工具次数限制。本地Whisper辅助转写，无原生音频输入；交付封存后评价。

结果：{fmt(score['confirmed_diagnostic_points'])}/100。问答31.25/50、证据9.333333/20、手册14.525/20、设计8/10。事实按原数据集标注；GPT-6-astra评审，Gemini核听音频，脚本汇总。

公开内容仅为审核后的题面、实际交付、展示用评分依据与哈希；不包含API凭据、宿主路径、原始运行记录或私有原始标注。视频许可CDLA-Permissive-2.0，不表示由数据集作者审核。

静态页面无需构建依赖，在docs目录启动HTTP服务即可预览。页面生成工具位于build_case_page.py，模板位于site-template/；生成工具需要组织者本地封存资料，不包含在公开输入中。媒体由页面相对路径及GitHub Release提供。
'''
 (CASE/'README.md').write_text(readme,encoding='utf8')
 shutil.copy2(Path(__file__),CASE/'build_case_page.py')
 # Public generator is relocatable only when organizer root is explicitly provided.
 code=(CASE/'build_case_page.py').read_text(encoding='utf8')
 code=code.replace('import hashlib,json,re,shutil,subprocess,zipfile,os','import hashlib,json,re,shutil,subprocess,zipfile,os,os').replace("ROOT=Path(os.environ['OMNIALE_ORGANIZER_ROOT']).resolve()","ROOT=Path(os.environ['OMNIALE_ORGANIZER_ROOT']).resolve()")
 (CASE/'build_case_page.py').write_text(code,encoding='utf8')
 for name in ['index.html','case.css','app.js']:
  template=Path(__file__).parent/'site-template'/name
  shutil.copy2(template,PAGE/name)
 shutil.copytree(Path(__file__).parent/'site-template',CASE/'site-template',dirs_exist_ok=True)
 # Add case to the existing catalog without altering existing cases.
 catalog=REPO/'docs/index.html';html=catalog.read_text(encoding='utf8')
 if 'href="assembly-manual/"' not in html:
  card='''<a class="case-card" href="assembly-manual/"><div class="case-cover" style="padding:0"><img src="assembly-manual/assets/early-tray.jpg" alt="第一人称推车装配录像" style="width:100%;height:100%;object-fit:cover"><span class="mono" style="position:absolute;left:14px;top:12px;background:#f5f6ef;padding:4px 8px">05 / ASSEMBLY MANUAL</span></div><div><div class="eyebrow">音视频证据核查与图解资料制作</div><h3>从装配现场，到可用手册。</h3><p>观看18分31秒远程指导录像，核查十项问题，再制作带截图标注的可编辑操作手册。查看真实交付、逐题依据与评分。</p><div class="status"><span class="status-dot"></span>GPT-6.1-sol + Codex · 63.11 / 100 · 9页图解手册</div><span class="enter">查看任务、手册和评分 →</span></div></a>'''
  html=html.replace('<p class="catalog-note">',card+'<p class="catalog-note">').replace('03 CASES','04 CASES')
  catalog.write_text(html,encoding='utf8')
 release_manifest={'tag':TAG,'assets':[{'name':'z057-june-28-22-rashult_assemble.mp4','local_source':str(SOURCE),'bytes':SOURCE.stat().st_size,'sha256':sha(SOURCE)},{'name':'sol-manual.docx','local_source':str(RELEASE/'sol-manual.docx'),'bytes':(RELEASE/'sol-manual.docx').stat().st_size,'sha256':sha(RELEASE/'sol-manual.docx')},{'name':bundle.name,'local_source':str(bundle),'bytes':bundle.stat().st_size,'sha256':sha(bundle)}]}
 dump(RELEASE/'release-manifest.json',release_manifest)
 print(json.dumps({'page':str(PAGE),'preview_MB':round(preview.stat().st_size/1e6,2),'bundle_MB':round(bundle.stat().st_size/1e6,2),'score':data['result']['score_display'],'questions':len(qrows)},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
