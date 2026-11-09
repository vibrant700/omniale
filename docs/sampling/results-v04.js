"use strict";
const v04=document.querySelector('#v04-video');
for(const button of document.querySelectorAll('[data-v04-seek]'))button.addEventListener('click',()=>{v04.currentTime=Number(button.dataset.v04Seek);v04.scrollIntoView({behavior:'smooth',block:'center'});});
v04.addEventListener('seeked',()=>{document.querySelector('#v04-seek-status').textContent='已定位 '+v04.currentTime.toFixed(1)+' 秒';});
document.addEventListener('play',event=>{if(event.target instanceof HTMLMediaElement)for(const media of document.querySelectorAll('video,audio'))if(media!==event.target)media.pause();},true);
