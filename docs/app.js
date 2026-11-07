'use strict';
const canvas = document.querySelector('#wave');
const ctx = canvas.getContext('2d');
let sampleRate = 4000;
let progress = 1;
let previousTime = 0;
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

function draw() {
  const box = canvas.getBoundingClientRect();
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const w = box.width, h = box.height;
  if (canvas.width !== Math.round(w*dpr) || canvas.height !== Math.round(h*dpr)) {
    canvas.width = Math.round(w*dpr); canvas.height = Math.round(h*dpr);
  }
  ctx.setTransform(dpr,0,0,dpr,0,0);
  ctx.clearRect(0,0,w,h);
  const x0=28,x1=w-12,mid=h*.47,amp=h*.29;
  ctx.lineWidth=1; ctx.font='9px Consolas, monospace';
  for(let i=0;i<=8;i++){
    const x=x0+(x1-x0)*i/8;
    ctx.strokeStyle='#e8eae3';ctx.beginPath();ctx.moveTo(x,mid-amp-9);ctx.lineTo(x,mid+amp+9);ctx.stroke();
    if(w>420 || i%2===0){ctx.fillStyle='#8c9287';ctx.textAlign='center';ctx.fillText((i/4).toString(),x,h-29);}
  }
  ctx.strokeStyle='#b6bdaf';ctx.beginPath();ctx.moveTo(x0,mid);ctx.lineTo(x1,mid);ctx.stroke();
  ctx.textAlign='right';ctx.fillStyle='#8c9287';ctx.fillText('t / ms',x1,h-9);
  function curve(freq,color,dashed){
    ctx.strokeStyle=color;ctx.lineWidth=1.8;ctx.setLineDash(dashed?[5,4]:[]);ctx.beginPath();
    for(let i=0;i<=600*progress;i++){
      const t=i/600*.002, x=x0+t/.002*(x1-x0), y=mid-amp*Math.cos(2*Math.PI*freq*t);
      if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y);
    }
    ctx.stroke();ctx.setLineDash([]);
  }
  curve(3000,'#315bce',false);
  curve(sampleRate===4000?1000:3000,'#c75e44',true);
  for(let n=0;n<=sampleRate*.002;n++){
    const t=n/sampleRate;if(t>.002*progress)break;
    const x=x0+t/.002*(x1-x0),y=mid-amp*Math.cos(2*Math.PI*3000*t);
    ctx.strokeStyle='#c9cdbf';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(x,mid);ctx.lineTo(x,y);ctx.stroke();
    ctx.fillStyle='#232820';ctx.beginPath();ctx.arc(x,y,3.1,0,Math.PI*2);ctx.fill();
  }
}
function animate(time){
  if(progress<1){progress=Math.min(1,progress+(time-previousTime)/950);draw();}
  previousTime=time;
  if(progress<1)requestAnimationFrame(animate);
}
document.querySelectorAll('[data-rate]').forEach(button=>button.addEventListener('click',()=>{
  sampleRate=Number(button.dataset.rate);
  document.querySelectorAll('[data-rate]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));
  document.querySelector('#rate-value').innerHTML=`${sampleRate/1000}<span> kHz</span>`;
  document.querySelector('#alias-label').textContent=sampleRate===4000?'混叠频率':'可表示的原频率';
  document.querySelector('#alias-value').innerHTML=`${sampleRate===4000?1:3}<span> kHz</span>`;
  document.querySelector('#sampling-explanation').textContent=sampleRate===4000?
    '不做抗混叠处理时，3 kHz 与 1 kHz 在这些采样点上无法区分。':
    '3 kHz 低于 4 kHz 奈奎斯特频率；在带限前提下，可正确表示原信号。';
  canvas.setAttribute('aria-label',`3千赫兹原信号，以${sampleRate/1000}千赫兹采样，候选重建为${sampleRate===4000?1:3}千赫兹`);
  if(reducedMotion.matches){progress=1;draw();}else if(progress>=1){progress=0;previousTime=performance.now();requestAnimationFrame(animate);}else{progress=0;}
}));
new ResizeObserver(draw).observe(canvas);
draw();
const media = [...document.querySelectorAll('audio,video')];
media.forEach(player=>{
  player.volume=.2;
  player.addEventListener('play',()=>media.forEach(other=>{if(other!==player)other.pause();}));
});
const links=[...document.querySelectorAll('.side-nav a')];
const sectionObserver=new IntersectionObserver(entries=>{
  for(const entry of entries){if(entry.isIntersecting){links.forEach(link=>{
    const active=link.hash===`#${entry.target.id}`;link.classList.toggle('active',active);
    if(active)link.setAttribute('aria-current','location');else link.removeAttribute('aria-current');
  });}}
},{rootMargin:'-15% 0px -60% 0px',threshold:0});
document.querySelectorAll('.content-section').forEach(section=>sectionObserver.observe(section));
