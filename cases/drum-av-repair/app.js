'use strict';
const $ = s => document.querySelector(s);
let caseData, selected = 0, changing = false, audition = 'candidate';
const left = $('#baseline-video'), right = $('#candidate-video');
const position = $('#compare-position'), clock = $('#compare-time'), play = $('#compare-play');
const status = $('#playback-status'), modeLabel = $('#playback-mode');
let mode = 'independent', activeVideo = right, generation = 0, playbackRequest = 0;
const current = () => caseData.regions[selected];
const number = (n, d = 2) => Number(n).toFixed(d);
function duration() {
  if (!caseData) return Number(position.max);
  const r = current();
  return Math.min(r.window[1] - r.window[0], Number.isFinite(right.duration) ? right.duration : Infinity, Number.isFinite(left.duration) ? left.duration : Infinity);
}
function setSound() {
  // Native controls play their own audio. Only explicit sync uses one audio lane.
  left.muted = mode === 'sync' && audition !== 'baseline';
  right.muted = mode === 'sync' && audition !== 'candidate';
}
function setMode(value) {
  mode = value;
  play.textContent = value === 'sync' ? '暂停同步' : '同步播放';
  modeLabel.textContent = value === 'sync' ? '当前：同步播放' : '当前：独立播放';
  setSound();
}
function pauseBoth() {
  playbackRequest++;
  setMode('independent');
  left.pause(); right.pause();
}
function timeDisplay(time) {
  const t = Math.max(0, Math.min(time, duration()));
  position.value = String(t); clock.value = `${number(t)} / ${number(duration())} s`;
}
function seekBoth(time) {
  const t = Math.max(0, Math.min(Number(time), duration()));
  if (left.readyState) left.currentTime = t;
  if (right.readyState) right.currentTime = t;
  timeDisplay(t);
}
async function playBoth() {
  if (!caseData || changing) return;
  const request = ++playbackRequest;
  status.textContent = '';
  let t = activeVideo.currentTime;
  if (t >= duration() - .06) t = 0;
  seekBoth(t); setMode('sync');
  try {
    await Promise.all([left.play(), right.play()]);
    if (request !== playbackRequest) return;
  } catch (e) {
    if (request !== playbackRequest) return;
    pauseBoth();
    status.textContent = '浏览器暂未开始同步播放，请再点一次“同步播放”。两侧视频也可分别播放。';
  }
}
function renderRegion() {
  const r = current();
  $('#region-title').textContent = `${r.id} · ${r.title}`;
  $('#region-window').textContent = `测试视频 ${number(r.window[0])}–${number(r.window[1])} 秒；修复区域位于片段内 ${number(r.local[0])}–${number(r.local[1])} 秒。两侧播放键各自独立，“同步播放”才会联动。`;
  $('#baseline-caption').textContent = $('#baseline-kind').value === 'reference' ? '干净参考' : '错误输入 · 修复前';
  $('#region-metrics').innerHTML = [
    [number(r.scores.total), '本段得分 / 18'],
    [number(r.scores.correspondence), '演奏与声音对应 / 10'],
    [number(r.scores.blending), '自然衔接 / 4'],
    [number(r.scores.quality), '同源音色与伪影 / 4']
  ].map(([v,k]) => `<div><strong>${v}</strong><span>${k}</span></div>`).join('');
  $('#region-analysis').replaceChildren(...r.analysis.map(text => { const li = document.createElement('li'); li.textContent = text; return li; }));
  document.querySelectorAll('[data-region]').forEach(b => b.setAttribute('aria-pressed', Number(b.dataset.region) === selected ? 'true' : 'false'));
}
function loadMedia(video, path, t, stamp) {
  return new Promise((resolve, reject) => {
    const cleanup = () => { video.removeEventListener('loadedmetadata', loaded); video.removeEventListener('error', failed); };
    const loaded = () => { cleanup(); if (stamp === generation) video.currentTime = Math.min(t, Math.max(0, video.duration - .04)); resolve(); };
    const failed = () => { cleanup(); reject(new Error('media_load_failed')); };
    video.addEventListener('loadedmetadata', loaded, {once:true});
    video.addEventListener('error', failed, {once:true});
    video.src = path; video.poster = `assets/${current().id}-poster.jpg`; video.load();
  });
}
async function loadRegion(index) {
  if (!caseData) return;
  changing = true; generation++; const stamp = generation;
  pauseBoth(); selected = index; activeVideo = right; renderRegion();
  position.max = String(current().window[1] - current().window[0]); timeDisplay(0);
  const r = current(), kind = $('#baseline-kind').value;
  try {
    await Promise.all([loadMedia(left, r.media[kind], 0, stamp), loadMedia(right, r.media.repaired, 0, stamp)]);
    if (stamp !== generation) return;
    changing = false; setSound(); seekBoth(0); status.textContent = '';
  } catch (e) {
    if (stamp !== generation) return;
    changing = false; status.textContent = '视频加载失败，请检查网络后切换区间重试。';
  }
}
play.addEventListener('click', () => mode === 'sync' ? pauseBoth() : playBoth());
$('#compare-reset').addEventListener('click', async () => {
  if (!caseData || changing) return;
  pauseBoth(); seekBoth(current().local[0]); await playBoth();
});
position.addEventListener('input', () => { pauseBoth(); seekBoth(position.value); });
$('#frame-back').addEventListener('click', () => { const t = activeVideo.currentTime; pauseBoth(); seekBoth(t - .04); });
$('#frame-next').addEventListener('click', () => { const t = activeVideo.currentTime; pauseBoth(); seekBoth(t + .04); });
document.querySelectorAll('input[name=audition]').forEach(x => x.addEventListener('change', () => { audition = x.value; setSound(); }));
document.querySelectorAll('[data-region]').forEach(b => b.addEventListener('click', () => loadRegion(Number(b.dataset.region))));
document.querySelectorAll('[data-jump]').forEach(a => a.addEventListener('click', () => loadRegion(Number(a.dataset.jump))));
$('#baseline-kind').addEventListener('change', async () => {
  if (!caseData) return;
  const t = left.currentTime;
  pauseBoth(); changing = true; generation++; const stamp = generation; renderRegion();
  try {
    await loadMedia(left, current().media[$('#baseline-kind').value], t, stamp);
    if (stamp !== generation) return;
    changing = false; setSound(); timeDisplay(activeVideo.currentTime); status.textContent = '';
  } catch (e) {
    if (stamp !== generation) return;
    changing = false; status.textContent = '左侧视频加载失败，请重新选择对照音轨。';
  }
});
for (const video of [left, right]) {
  video.addEventListener('play', () => {
    if (changing || mode === 'sync') return;
    activeVideo = video;
    // Starting either native player never starts or seeks the other player.
    (video === left ? right : left).pause();
    setSound();
  });
  video.addEventListener('pause', () => { if (!changing && mode === 'sync' && video.paused && !video.ended) pauseBoth(); });
  video.addEventListener('seeking', () => {
    if (changing || mode !== 'sync') return;
    const other = video === left ? right : left;
    if (Math.abs(other.currentTime - video.currentTime) > .09) other.currentTime = video.currentTime;
  });
  video.addEventListener('ended', () => { if (!changing && mode === 'sync') pauseBoth(); });
  video.addEventListener('error', () => { status.textContent = '视频加载失败，请检查网络后切换区间重试。'; pauseBoth(); });
  video.addEventListener('timeupdate', () => {
    if (caseData && !changing && video === (mode === 'sync' ? right : activeVideo)) timeDisplay(video.currentTime);
  });
}
function tick() {
  if (caseData && mode === 'sync' && !changing && !right.seeking && !left.seeking && !right.paused && !left.paused) {
    if (Math.abs(left.currentTime - right.currentTime) > .14) left.currentTime = right.currentTime;
  }
  requestAnimationFrame(tick);
}
fetch('assets/case-data.json?v=20261128g', { cache: 'no-cache' }).then(r => { if (!r.ok) throw Error(r.status); return r.json(); }).then(data => { caseData = data; setMode('independent'); renderRegion(); tick(); }).catch(() => { status.textContent = '对照数据加载失败，请刷新页面。'; });
