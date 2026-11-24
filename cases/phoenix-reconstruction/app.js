'use strict';

const modelSelect = document.querySelector('#model-select');
const modelPanels = [...document.querySelectorAll('[data-model-panel]')];

function selectModel(id) {
  if (![...modelSelect.options].some(option => option.value === id)) return;
  modelSelect.value = id;
  modelPanels.forEach(panel => {
    const selected = panel.dataset.modelPanel === id;
    panel.hidden = !selected;
    if (!selected) panel.querySelectorAll('video,audio').forEach(media => media.pause());
  });
  document.querySelectorAll('[data-result-model]').forEach(row => {
    row.classList.toggle('is-selected', row.dataset.resultModel === id);
  });
  document.querySelectorAll('[data-select-model]').forEach(link => {
    if (link.dataset.selectModel === id) link.setAttribute('aria-current', 'true');
    else link.removeAttribute('aria-current');
  });
}

modelSelect.addEventListener('change', () => selectModel(modelSelect.value));
document.querySelectorAll('[data-select-model]').forEach(link => link.addEventListener('click', () => {
  selectModel(link.dataset.selectModel);
}));
function selectHashModel() {
  let target;
  try { target = document.getElementById(decodeURIComponent(location.hash.slice(1))); }
  catch { return; }
  const panel = target?.closest('[data-model-panel]');
  if (panel) selectModel(panel.dataset.modelPanel);
}
selectModel(modelSelect.value);
selectHashModel();
window.addEventListener('hashchange', selectHashModel);

// Each model keeps its own frame, metric data, observations and comparison images.
document.querySelectorAll('[data-frame-inspector]').forEach(inspector => {
  const buttons = [...inspector.querySelectorAll('[data-frame]')];
  const root = inspector.dataset.frameRoot;
  const label = inspector.dataset.label;
  let metrics = [];
  const find = name => inspector.querySelector(`[data-frame-${name}]`);
  function selectFrame(frame) {
    const number = String(frame).padStart(2, '0');
    buttons.forEach(button => button.setAttribute('aria-pressed', String(Number(button.dataset.frame) === frame)));
    find('title').textContent = `帧 ${number} · ${(frame / 30).toFixed(3)} s`;
    const image = find('image');
    image.src = `${root}frame-${number}.webp`;
    image.alt = `帧 ${frame}：左侧参考凤凰，右侧 ${label} 重建凤凰，同时间同尺度比较`;
    const link = find('link');
    link.href = image.src;
    link.dataset.title = `${label} · 帧 ${number} · 左参考，右交付`;
    const row = metrics.find(value => value.frame === frame);
    find('metrics').textContent = row
      ? `表面 F1 ${row.F1.toFixed(4)} · IoU I1 ${row.IoU.I1.toFixed(4)} / I2 ${row.IoU.I2.toFixed(4)} / I3 ${row.IoU.I3.toFixed(4)} / T1 ${row.IoU.T1.toFixed(4)} · T1 SSIM ${row.SSIM.toFixed(4)} · T1 LPIPS ${row.LPIPS.toFixed(4)}`
      : '逐帧指标见当前模型实际评分区的 JSON。';
    find('observation').textContent = row?.observation || '本帧的对应指标见当前模型评分文件。';
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
  fetch(`${root}frame-data.json`).then(response => {
    if (!response.ok) throw new Error('Frame metrics unavailable');
    return response.json();
  }).then(data => {
    metrics = data;
    const active = buttons.find(button => button.getAttribute('aria-pressed') === 'true');
    selectFrame(Number(active.dataset.frame));
  }).catch(() => {
    find('metrics').textContent = '逐帧指标见当前模型实际评分区的 JSON 下载。';
  });
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
    const rect = dialog.getBoundingClientRect();
    if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close();
  }
});
document.querySelectorAll('video,audio').forEach(player => player.addEventListener('play', () => {
  document.querySelectorAll('video,audio').forEach(other => {
    if (other !== player) other.pause();
  });
}));
