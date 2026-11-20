'use strict';
const mediaControllers=[];
const esc=value=>String(value).replace(/[&<>"']/g,x=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x]));
const score=value=>Number.isFinite(value)?value.toFixed(2):'—';
document.querySelectorAll('.comparison-view').forEach(group=>{
 const ref=group.querySelector('[data-reference]'),pred=group.querySelector('[data-prediction]');
 const play=group.querySelector('[data-play]'),restart=group.querySelector('[data-restart]'),seek=group.querySelector('[data-seek]'),clock=group.querySelector('[data-clock]'),status=group.querySelector('[data-status]');
 const ready=new Set(),duration=104/30;let running=false,internal=false,animation=0;
 ref.muted=true;ref.controls=false;
 function update(){const t=Math.min(pred.currentTime||0,duration);seek.value=t;clock.textContent=`${t.toFixed(2)} / ${duration.toFixed(2)} s`;}
 function stop(){running=false;cancelAnimationFrame(animation);ref.pause();pred.pause();play.textContent='同步播放';update();}
 function tick(){if(!running)return;if(!ref.seeking&&Math.abs(ref.currentTime-pred.currentTime)>.045)ref.currentTime=pred.currentTime;update();animation=requestAnimationFrame(tick);}
 async function start(){if(ready.size!==2)return;mediaControllers.forEach(c=>{if(c.group!==group)c.stop();});document.querySelectorAll('video,audio').forEach(v=>{if(v!==ref&&v!==pred)v.pause();});if(pred.currentTime>=duration-.035)pred.currentTime=0;ref.currentTime=pred.currentTime;running=true;internal=true;try{await Promise.all([ref.play(),pred.play()]);if(!running)return;play.textContent='暂停对比';status.textContent='原片静音，仅重建片播放声音。';cancelAnimationFrame(animation);tick();}catch(_){stop();status.textContent='请再次点击播放，或使用视频自带控件。';}finally{internal=false;}}
 for(const v of [ref,pred]){const loaded=()=>{ready.add(v);play.disabled=restart.disabled=seek.disabled=ready.size!==2;};v.addEventListener('loadedmetadata',loaded);if(v.readyState>=1)loaded();v.addEventListener('emptied',()=>{ready.delete(v);play.disabled=restart.disabled=seek.disabled=true;});v.addEventListener('error',()=>{stop();status.textContent='视频加载失败，请刷新或打开原视频文件。';});}
 play.addEventListener('click',()=>running?stop():start());restart.addEventListener('click',()=>{stop();ref.currentTime=pred.currentTime=0;update();});seek.addEventListener('input',()=>{const t=Number(seek.value);stop();ref.currentTime=pred.currentTime=t;update();});pred.addEventListener('play',()=>{if(!internal&&!running)start();});pred.addEventListener('pause',()=>{if(running)stop();});pred.addEventListener('ended',stop);pred.addEventListener('seeking',()=>{ref.currentTime=pred.currentTime;update();});pred.addEventListener('timeupdate',update);document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});group.addEventListener('modelchange',()=>{stop();pred.currentTime=ref.currentTime=0;update();});mediaControllers.push({group,stop});
});
document.querySelectorAll('[data-view-tab]').forEach(button=>button.addEventListener('click',()=>{mediaControllers.forEach(c=>c.stop());document.querySelectorAll('[data-view-tab]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));document.querySelectorAll('.comparison-view').forEach(g=>{g.hidden=g.dataset.view!==button.dataset.viewTab;});}));
document.addEventListener('play',event=>{if(event.target.closest('.comparison-view'))return;mediaControllers.forEach(c=>c.stop());document.querySelectorAll('video,audio').forEach(v=>{if(v!==event.target)v.pause();});},true);

// Each model owns its scores, videos, steps and findings. Future records do not
// inherit the default model's media or claims.
const modelSelect=document.querySelector('[data-model-select]');
if(modelSelect)fetch('models.json',{cache:'no-cache'}).then(r=>{if(!r.ok)throw new Error('Model data unavailable');return r.json();}).then(data=>{
 const models=data.models.filter(m=>m.id&&m.name&&m.scores&&m.views&&m.steps&&m.findings);if(!models.length)return;
 document.querySelector('[data-leaderboard]').innerHTML=models.map(m=>`<tr data-model="${esc(m.id)}"><th scope="row">${esc(m.name)}</th><td>${esc(m.reasoning)}</td><td>${esc(m.framework)}</td><td class="num">${score(m.scores.visual)}</td><td class="num">${score(m.scores.elements)}</td><td class="num">${score(m.scores.sync)}</td><td class="num"><strong class="score-value">${score(m.scores.total)}</strong></td></tr>`).join('');
 modelSelect.replaceChildren(...models.map(m=>{const option=document.createElement('option');option.value=m.id;option.textContent=`${m.name} · ${m.reasoning} · ${m.framework}`;return option;}));let currentId=null;
 function selectModel(id,changeURL){const m=models.find(x=>x.id===id)||models.find(x=>x.id===data.default_model)||models[0];modelSelect.value=m.id;if(currentId===m.id)return;currentId=m.id;
 document.querySelector('[data-runtime]').textContent=`约${Math.round(m.runtime.seconds/60)}分钟 · ${m.runtime.tool_calls}次工具调用`;
 document.querySelectorAll('.comparison-view').forEach(g=>{const media=m.views[g.dataset.view];if(!media)return;g.dispatchEvent(new Event('modelchange'));const pred=g.querySelector('[data-prediction]');g.querySelector('[data-output-label]').textContent=`${m.name} · ${m.reasoning} · 重建成片`;if(pred.getAttribute('src')!==media.video){pred.poster=media.poster;pred.src=media.video;pred.load();}});
 document.querySelector('[data-region-rows]').innerHTML=m.regions.map(r=>`<tr><th scope="row">${esc(r.name)}</th><td class="num">${score(r.score)} / ${r.maximum}</td></tr>`).join('');document.querySelector('[data-delivery]').href=m.delivery.url;document.querySelector('[data-readme]').href=m.delivery.readme;document.querySelector('[data-result-summary]').textContent=m.delivery.summary||'查看下方工程与交付说明。';
 document.querySelector('[data-score-data]').href=m.score_url||'files/score.json';
 document.querySelector('[data-results-link]').href=`results.html#${m.id}`;
 document.querySelector('[data-traces-link]').href=`traces.html#${m.id}`;
 document.querySelector('[data-execution-intro]').textContent=`${m.name}以${m.reasoning}运行，通过代码调用Python、FFmpeg与后台Blender完成制作。`;
 document.querySelector('[data-execution-steps]').innerHTML=m.steps.map((s,i)=>`<article class="step"><span class="step-no">${i+1}</span><div><h3>${esc(s.title)}</h3><p>${esc(s.text)}</p><p class="step-source"><a href="${esc(s.evidence_url||`${m.trace_url||'traces.html'}#${s.trace}`)}">查看对应执行证据 ↗</a></p></div></article>`).join('');
 document.querySelector('[data-findings]').innerHTML=m.findings.map((f,i)=>`<article class="finding"><h3>${i+1}. ${esc(f.title)}</h3><p>${esc(f.text)}</p><details><summary>详细分析</summary><div class="detail-body"><p>${esc(f.detail)}</p>${f.image?`<figure><img loading="lazy" src="${esc(f.image)}" alt="${esc(f.caption)}"><figcaption>${esc(f.caption)}</figcaption></figure>`:''}</div></details></article>`).join('');
 if(changeURL){const url=new URL(location.href);url.searchParams.set('model',m.id);history.replaceState(null,'',url);}}
 selectModel(new URLSearchParams(location.search).get('model')||data.default_model,false);modelSelect.addEventListener('change',()=>selectModel(modelSelect.value,true));
}).catch(()=>{modelSelect.disabled=true;});
