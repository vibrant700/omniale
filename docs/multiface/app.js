// Each comparison is a single clock; only the submitted video supplies sound.
document.querySelectorAll('[data-comparison]').forEach(group=>{
 const ref=group.querySelector('[data-reference]'), pred=group.querySelector('[data-prediction]');
 const play=group.querySelector('[data-play]'), restart=group.querySelector('[data-restart]');
 const seek=group.querySelector('[data-seek]'), clock=group.querySelector('[data-clock]'), status=group.querySelector('[data-status]');
 ref.muted=true; const ready=new Set(); let running=false;
 const duration=104/30;
 function update(){seek.value=Math.min(pred.currentTime,duration);clock.textContent=`${pred.currentTime.toFixed(2)} / ${duration.toFixed(2)} s`;}
 function pause(){running=false;ref.pause();pred.pause();play.textContent='同步播放';update();}
 function tick(){if(!running)return;if(!ref.seeking&&Math.abs(ref.currentTime-pred.currentTime)>.045)ref.currentTime=pred.currentTime;update();requestAnimationFrame(tick);}
 for(const v of [ref,pred]){
  const loaded=()=>{ready.add(v);if(ready.size===2){play.disabled=false;restart.disabled=false;seek.disabled=false;status.textContent='左：评测保留视角原片 · 右：Agent 重建成片（声音）';}};
  v.addEventListener('loadedmetadata',loaded);if(v.readyState>=1)loaded();
  v.addEventListener('error',()=>{pause();status.textContent='视频加载失败，请刷新页面或使用下方链接打开原文件。';});
 }
 play.addEventListener('click',async()=>{
  if(running){pause();return;}
  document.querySelectorAll('video,audio').forEach(v=>{if(v!==ref&&v!==pred)v.pause();});
  if(pred.currentTime>=duration-.04){pred.currentTime=0;ref.currentTime=0;}
  ref.currentTime=pred.currentTime;
  try{await Promise.all([ref.play(),pred.play()]);ref.currentTime=pred.currentTime;running=true;play.textContent='暂停对比';requestAnimationFrame(tick);}
  catch(e){pause();status.textContent='浏览器阻止了播放，请再按一次播放，或打开原文件。';}
 });
 restart.addEventListener('click',()=>{pause();pred.currentTime=0;ref.currentTime=0;update();});
 seek.addEventListener('input',()=>{const t=Number(seek.value);pause();pred.currentTime=t;ref.currentTime=t;update();});
 pred.addEventListener('timeupdate',()=>{update();if(running&&Math.abs(ref.currentTime-pred.currentTime)>.065)ref.currentTime=pred.currentTime;});
 pred.addEventListener('pause',()=>{if(running)pause();});
 pred.addEventListener('ended',pause);
 document.addEventListener('visibilitychange',()=>{if(document.hidden)pause();});
});
