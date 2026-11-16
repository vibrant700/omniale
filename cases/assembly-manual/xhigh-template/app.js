'use strict';
const $=s=>document.querySelector(s);
const num=n=>(Math.round((Number(n)+1e-8)*100)/100).toFixed(2);
const time=n=>`${Math.floor(n/60)}:${String(Math.floor(n%60)).padStart(2,'0')}`;
const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
const modelNames={sol:'GPT-6.1-Sol · 默认 low',luna:'GPT-6-Luna · 默认 medium','sol-xhigh':'GPT-6.1-Sol · xhigh'};
const shortNames={sol:'Sol 默认',luna:'Luna 默认','sol-xhigh':'Sol xhigh'};
const labels={qa_semantic:'十题结论与关系',qa_evidence:'证据时间与动作语音配对',manual_delivery:'手册综合交付',subjective_design:'美观与教学引导'};
const statusNames={pass:'通过',partial:'部分通过',fail:'未通过'};
let systems,data,active='sol',page=1,requestedSeek=null;

function showPage(n,scroll=false){
  page=Math.max(1,Math.min(data.delivery.pages,Number(n)||1));
  const path=data.delivery.page_images[page-1],topic=data.delivery.page_topics[page-1];
  $('#manual-page').value=String(page);
  $('#manual-image').src=path;
  $('#manual-image').alt=`${modelNames[active]}实际提交手册第${page}页：${topic}`;
  $('#page-full').href=path;
  $('#page-label').textContent=`${String(page).padStart(2,'0')} / ${String(data.delivery.pages).padStart(2,'0')}`;
  $('#prev-page').disabled=page===1;
  $('#next-page').disabled=page===data.delivery.pages;
  document.querySelectorAll('#page-dots button').forEach(b=>b.setAttribute('aria-pressed',String(Number(b.dataset.page)===page)));
  if(scroll)$('#deliverable').scrollIntoView({behavior:'smooth'});
}

function seekSource(seconds,id){
  const v=$('#source-video');requestedSeek=Number(seconds);$('#source-chapter').value=String(seconds);
  if(v.readyState>=1){v.currentTime=requestedSeek;requestedSeek=null;}else v.load();
  $('#video-status').textContent=`${id||'源录像'} · 定位 ${time(Number(seconds))} · 点击播放查看并听取原声`;
  $('#source').scrollIntoView({behavior:'smooth'});
}

function criteria(title,items){
  const d=el('details'),s=el('summary',title),box=el('div',undefined,'qa-content criterion-group');
  for(const i of items){const row=el('div',undefined,'criterion');row.append(el('span',`${i.id} · ${statusNames[i.status]||i.status}`,'status '+i.status),el('p',i.evidence));box.append(row);}
  d.append(s,box);return d;
}

function answerBlock(text){
  const box=el('div',undefined,'answer-text');
  for(const line of text.split('\n')){
    const row=el('div');
    if(!line.trim())row.append(document.createElement('br'));
    else{
      const pattern=/\*\*([^*]+)\*\*|`([^`]+)`/g;let start=0,match;
      while((match=pattern.exec(line))){row.append(document.createTextNode(line.slice(start,match.index)),el(match[1]?'strong':'code',match[1]||match[2]));start=pattern.lastIndex;}
      row.append(document.createTextNode(line.slice(start)));
    }
    box.append(row);
  }
  return box;
}

function renderQuestions(){
  const list=$('#qa-list');list.replaceChildren();
  for(const q of data.result.questions){
    const d=el('details'),s=el('summary'),head=el('span',undefined,'qa-head');
    head.append(el('b',q.id),el('span',q.title),el('strong',`${num(q.score)} / 8.40`));s.append(head);
    const c=el('div',undefined,'qa-content');c.append(el('p',q.question,'question'),el('p',q.summary,'qa-summary'));
    const scores=el('div',undefined,'qa-scores');
    for(const [text,value,max] of [['问答',q.scores.qa,5],['证据',q.scores.evidence,2],['手册',q.scores.manual,1.4]])scores.append(el('span',`${text} ${num(value)} / ${max}`));
    c.append(scores);
    const actions=el('div',undefined,'qa-actions'),video=el('button','查看相关源录像 ↗','button');video.onclick=()=>seekSource(q.source_start,q.id);actions.append(video);
    for(const n of q.page_numbers){const b=el('button',`手册第${n}页 ↗`,'button secondary');b.onclick=()=>showPage(n,true);actions.append(b);}
    c.append(actions,el('h4',`${modelNames[active]}实际提交的回答`),answerBlock(q.answer),el('h4','原数据集标注依据'),el('p',q.annotation_basis,'annotation-basis'));
    for(const [title,key] of [['问答结论：对象与关系','qa_claims'],['证据：时间、配对与具体性','qa_evidence'],['手册：事实是否落实','manual_claims'],['配图：来源、指向、图文与过程','illustration_checks']])c.append(criteria(title,q.checks[key]));
    d.append(s,c);list.append(d);
  }
}

function renderScores(){
  $('#score-bars').replaceChildren();$('#manual-scores').replaceChildren();$('#document-review').replaceChildren();
  for(const key of Object.keys(labels)){
    const g=data.result.groups[key],row=el('div',undefined,'score-row'),line=el('div',undefined,'score-line'),value=el('strong',num(g.score));
    value.append(el('small',` / ${g.maximum}`));line.append(el('span',labels[key]),value);
    const bar=el('div',undefined,'bar'),fill=el('span');fill.style.width=`${g.score/g.maximum*100}%`;bar.append(fill);row.append(line,bar);$('#score-bars').append(row);
  }
  for(const [name,key] of [['事实落实','manual_facts'],['截图与标注证据','manual_illustrations'],['基本组织与可用性','manual_organization'],['可编辑、PDF与导出一致性','editable_delivery']]){
    const s=data.result.details[key],tr=el('tr');tr.append(el('td',name),el('td',num(s.score)),el('td',String(s.maximum)));$('#manual-scores').append(tr);
  }
  const doc=data.document_checks;
  for(const [title,key] of [['文档组织与可用性','organization'],['正文、标注与导出','editable']])$('#document-review').append(criteria(title,doc[key]));
  const design=el('div');
  for(const item of doc.subjective){const row=el('div',undefined,'criterion');row.append(el('span',`${item.rating} / 4`,'status'),el('p',item.evidence));design.append(row);}
  $('#document-review').append(el('h4','设计质量：五项各2分'),design);
}

function selectSystem(key,updateUrl=true){
  if(!systems||!Object.hasOwn(systems,key))return;
  active=key;data=systems[key];const name=modelNames[key],d=data.delivery;
  document.querySelectorAll('[data-system]').forEach(b=>{const chosen=b.dataset.system===key;b.setAttribute('aria-pressed',String(chosen));b.classList.toggle('active',chosen);const label=shortNames[b.dataset.system]||b.dataset.system;b.querySelector('b').textContent=chosen?`✓ 当前展示 ${label}`:`查看 ${label} 手册与评分 →`;});
  document.querySelectorAll('.system-select').forEach(s=>s.value=key);
  document.querySelectorAll('.model-name').forEach(n=>n.textContent=name);
  $('#system-status').textContent=`当前展示 ${name}：${d.pages}页手册 · ${data.result.score_display} / 100 · 主评 ${data.scoring.judge} · Gemini核听音频`;
  $('#hero-pages').replaceChildren(document.createTextNode(String(d.pages)),el('small','页'));
  const figures=d.figure_count??d.original_screenshots??d.editable_svg;
  $('#hero-figures').textContent=d.figure_summary||`实际手册 · ${figures}组标注配图`;
  $('#manual-description').textContent=`这里展示${name}实际提交的${d.pages}页PDF。正文、截图和标注内容均保留原样。`;
  $('#artifact-pages').textContent=d.pages;$('#artifact-figures').textContent=figures;
  $('#artifact-figures-label').textContent=d.figure_description||'组原图及SVG标注源';
  $('#manual-page').replaceChildren();$('#page-dots').replaceChildren();
  for(let i=1;i<=d.pages;i++){
    const o=el('option',`第${i}页 · ${d.page_topics[i-1]}`);o.value=String(i);$('#manual-page').append(o);
    const b=el('button',String(i));b.dataset.page=String(i);b.setAttribute('aria-label',`第${i}页：${d.page_topics[i-1]}`);b.onclick=()=>showPage(i);$('#page-dots').append(b);
  }
  showPage(1);
  for(const [id,url] of [['download-pdf',d.pdf],['download-docx',d.docx],['file-pdf',d.pdf],['file-answers',d.answers],['file-bundle',d.bundle]])$('#'+id).href=url;
  $('#file-bundle-description').textContent=d.bundle_description||`${name}：Word、PDF、答案、${figures}组原图与SVG标注源${key==='luna'?'，附标注PNG预览':''}。`;
  $('#result-total').replaceChildren(document.createTextNode(data.result.score_display),el('small','/ 100'));
  const seconds=Math.round(data.solver.elapsed_seconds);
  $('#result-duration').textContent=`约${Math.floor(seconds/60)}分${String(seconds%60).padStart(2,'0')}秒`;
  $('#result-tools').textContent=`${data.solver.tool_calls}次工具调用`;
  const hardest=[...data.result.questions].sort((a,b)=>a.score-b.score).slice(0,2);
  $('#result-readout').textContent=`${name}主要扣分题目为${hardest.map(q=>q.id+'「'+q.title+'」').join('、')}。下方可查看实际答案、标注依据和逐项判断。`;
  renderScores();renderQuestions();
  if(updateUrl){const url=new URL(location.href);url.searchParams.set('model',key);history.replaceState(null,'',url);}
}

$('#source-video').addEventListener('loadedmetadata',()=>{if(requestedSeek!==null){$('#source-video').currentTime=requestedSeek;requestedSeek=null;}});
$('#source-video').addEventListener('error',()=>{$('#video-status').textContent='当前浏览器无法播放预览，可使用下方链接下载原始录像。';});
$('#manual-page').onchange=e=>{if(data)showPage(e.target.value);};
$('#prev-page').onclick=()=>{if(data)showPage(page-1);};$('#next-page').onclick=()=>{if(data)showPage(page+1);};
$('#source-chapter').onchange=e=>seekSource(e.target.value,'源录像');
document.querySelectorAll('[data-system]').forEach(b=>b.onclick=()=>selectSystem(b.dataset.system));
document.querySelectorAll('.system-select').forEach(s=>s.onchange=e=>selectSystem(e.target.value));
window.addEventListener('popstate',()=>selectSystem(new URLSearchParams(location.search).get('model')||'sol',false));

fetch('data.json').then(r=>{if(!r.ok)throw new Error('展示数据暂时无法加载');return r.json();}).then(all=>{
  systems=all.systems;
  for(const q of systems.sol.result.questions){const o=el('option',`${q.id} · ${q.title} · ${time(q.source_start)}`);o.value=String(q.source_start);$('#source-chapter').append(o);}
  const requested=new URLSearchParams(location.search).get('model');selectSystem(Object.hasOwn(systems,requested)?requested:all.default_system,false);
  document.querySelectorAll('[data-system],.system-select').forEach(n=>n.disabled=false);
}).catch(err=>{const e=$('#load-error');e.hidden=false;e.textContent=err.message+'。仍可直接翻阅Sol手册或下载完整交付。';$('#system-status').textContent='结果切换暂时无法加载';$('#qa-list').replaceChildren(el('p','逐题材料暂未加载，请打开下方展示数据文件。','caption'));});
