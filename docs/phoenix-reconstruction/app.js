'use strict';
const buttons = [...document.querySelectorAll('[data-frame]')];
const observations = {
  0: '抬翼姿态大体建立，翼面厚度、躯干覆羽与眼斑长尾的形状和位置仍有偏差。',
  11: '下拍阶段，近侧翼的展开方向与羽片间距不同，尾羽分布也有偏移。',
  22: '双翼回收时，参考翼面仍向上展开，交付翼面更接近水平，姿态对应出现偏差。',
  33: '参考两翼的弯曲与扭转不对称，交付翼链更接近对称上举，躯干前部的受光也不同。',
  44: '低翼阶段，交付的翼尖指向与参考不同；尾羽的眼斑间距和分叉轮廓仍未对齐。',
  55: '抬翼途中，参考飞羽更宽、颜色过渡更细碎，交付靠近躯干的覆羽明度更高。',
  66: '低点附近，参考翼尖向内弯，交付翼面更直、更向下伸展，轮廓差异明显。',
  77: '双翼再次上举，整体姿态相近；尾羽更规则地分离，参考的重叠与层次没有完整恢复。',
  88: '翼面接近竖直时，交付近侧翼与躯干衔接的厚度、亮度和尾部轮廓均与参考不同。',
  99: '片尾延续周期扑翼，主要配色与形象保留；翼面扭转、覆羽细节与长尾布局仍有差距。'
};
let metrics = [];
function selectFrame(frame) {
  const label = String(frame).padStart(2, '0');
  buttons.forEach(b => b.setAttribute('aria-pressed', String(Number(b.dataset.frame) === frame)));
  document.querySelector('#frame-title').textContent = `帧 ${label} · ${(frame / 30).toFixed(3)} s`;
  const image = document.querySelector('#frame-image');
  image.src = `assets/evaluation/frame-${label}.webp`;
  image.alt = `帧 ${frame}：左侧参考凤凰，右侧 Astra 重建凤凰，同时间同尺度比较`;
  const link = document.querySelector('#frame-link');
  link.href = image.src;
  link.dataset.title = `帧 ${label} · 左参考，右交付`;
  document.querySelector('#frame-observation').textContent = observations[frame];
  const row = metrics.find(r => r.frame === frame);
  document.querySelector('#frame-metrics').textContent = row
    ? `表面 F1 ${row.F1.toFixed(4)} · IoU I1 ${row.IoU.I1.toFixed(4)} / I2 ${row.IoU.I2.toFixed(4)} / I3 ${row.IoU.I3.toFixed(4)} / T1 ${row.IoU.T1.toFixed(4)} · T1 SSIM ${row.SSIM.toFixed(4)} · T1 LPIPS ${row.LPIPS.toFixed(4)}`
    : '逐帧指标见实际评分区 geometry_metrics.json 与 image_metrics.json。';
}
buttons.forEach((button, index) => {
  button.addEventListener('click', () => selectFrame(Number(button.dataset.frame)));
  button.addEventListener('keydown', event => {
    let target = index;
    if (event.key === 'ArrowRight') target = (index + 1) % buttons.length;
    else if (event.key === 'ArrowLeft') target = (index + buttons.length - 1) % buttons.length;
    else if (event.key === 'Home') target = 0;
    else if (event.key === 'End') target = buttons.length - 1;
    else return;
    event.preventDefault();
    buttons[target].focus();
    selectFrame(Number(buttons[target].dataset.frame));
  });
});
fetch('assets/evaluation/frame-data.json').then(response => {
  if (!response.ok) throw new Error('Frame metrics unavailable');
  return response.json();
}).then(data => {
  metrics = data;
  const active = buttons.find(b => b.getAttribute('aria-pressed') === 'true');
  selectFrame(Number(active.dataset.frame));
}).catch(() => {
  document.querySelector('#frame-metrics').textContent = '逐帧指标见实际评分区的 JSON 下载。';
});
const dialog = document.querySelector('#image-dialog');
let opener;
document.querySelectorAll('[data-zoom]').forEach(link => link.addEventListener('click', event => {
  if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
  event.preventDefault();
  opener = link;
  document.querySelector('#dialog-title').textContent = link.dataset.title;
  const image = document.querySelector('#dialog-image');
  image.src = link.href;
  image.alt = link.dataset.title;
  dialog.showModal();
}));
document.querySelector('#close-dialog').addEventListener('click', () => dialog.close());
dialog.addEventListener('close', () => opener?.focus());
dialog.addEventListener('click', event => {
  if (event.target === dialog) {
    const r = dialog.getBoundingClientRect();
    if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) dialog.close();
  }
});
// Keep user-initiated audio from overlapping across the case's media players.
document.querySelectorAll('video,audio').forEach(player => player.addEventListener('play', () => {
  document.querySelectorAll('video,audio').forEach(other => {
    if (other !== player) other.pause();
  });
}));
