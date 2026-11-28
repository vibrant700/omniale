'use strict';
const $ = s => document.querySelector(s);
let caseData, selected = 0, changing = false, syncing = false, audition = 'candidate';
const left = $('#baseline-video'), right = $('#candidate-video');
const position = $('#compare-position'), clock = $('#compare-time'), play = $('#compare-play');
const status = $('#playback-status');
let playing = false, generation = 0;
const current = () => caseData.regions[selected];
const number = (n, d = 2) => Number(n).toFixed(d);
function duration() {
  const r = current();
  return Math.min(r.window[1] - r.window[0], Number.isFinite(right.duration) ? right.duration : Infinity, Number.isFinite(left.duration) ? left.duration : Infinity);
}
function setSound() { left.muted = audition !== 'baseline'; right.muted = audition !== 'candidate'; }
function setPlaying(value) { playing = value; play.textContent = value ? '暂停两路' : '同步播放'; }
function pauseBoth() { syncing = true; left.pause(); right.pause(); syncing = false; setPlaying(false); }
function timeDisplay(t) { position.value = String(t); clock.value = `${number(t)} / ${number(duration())} s`; }
function seekBoth(time) {
  const t = Math.max(0, Math.min(Number(time), duration()));
  syncing = true;
  if (left.readyState) left.currentTime = t;
  if (right.readyState) right.currentTime = t;
  syncing = false; timeDisplay(t);
}
async function playBoth() {
  status.textContent = ''; setSound();
  if (right.currentTime >= duration() - 0.06) seekBoth(0);
  syncing = true;
  try {
    await Promise.all([left.play(), right.play()]); setPlaying(true);
  } catch (e) {
    left.pause(); right.pause(); setPlaying(false);
    status.textContent = '浏览器暂未开始播放，请再点一次“同步播放”，或使用视频原生播放键。';
  } finally { syncing = false; }
}
function renderRegion() {
  const r = current();
  $('#region-title').textContent = `${r.id} · ${r.title}`;
  $('#region-window').textContent = `测试视频 ${number(r.window[0])}–${number(r.window[1])} 秒；修复区域位于片段内 ${number(r.local[0])}–${number(r.local[1])} 秒。切换听音不改变播放位置。`;
  $('#baseline-caption').textContent = $('#baseline-kind').value === 'reference' ? '干净参考' : '错误输入 · 修复前';
  $('#region-metrics').innerHTML = [
    [number(r.scores.total), '本段得分 / 18'],
    [number(r.scores.correspondence), '演奏与声音对应 / 9'],
    [number(r.scores.blending), '衔接与电平 / 4.5'],
    [number(r.scores.quality), '同源音色与伪影 / 4.5']
  ].map(([v,k]) => `<div><strong>${v}</strong><span>${k}</span></div>`).join('');
  $('#region-analysis').replaceChildren(...r.analysis.map(text => { const li = document.createElement('li'); li.textContent = text; return li; }));
  document.querySelectorAll('[data-region]').forEach(b => b.setAttribute('aria-pressed', Number(b.dataset.region) === selected ? 'true' : 'false'));
}
function loadMedia(video, path, t, stamp) {
  return new Promise(resolve => {
    const loaded = () => { if (stamp === generation) video.currentTime = Math.min(t, Math.max(0, video.duration - .04)); resolve(); };
    video.addEventListener('loadedmetadata', loaded, {once:true});
    video.src = path; video.poster = `assets/${current().id}-poster.jpg`; video.load();
  });
}
async function loadRegion(index) {
  changing = true; generation++; const stamp = generation;
  pauseBoth(); selected = index; renderRegion(); position.max = String(current().window[1] - current().window[0]); timeDisplay(0);
  const r = current(), kind = $('#baseline-kind').value;
  await Promise.all([loadMedia(left, r.media[kind], 0, stamp), loadMedia(right, r.media.repaired, 0, stamp)]);
  if (stamp !== generation) return;
  setSound(); changing = false; seekBoth(0);
}
play.addEventListener('click', () => playing ? pauseBoth() : playBoth());
$('#compare-reset').addEventListener('click', async () => { pauseBoth(); seekBoth(current().local[0]); await playBoth(); });
position.addEventListener('input', () => { pauseBoth(); seekBoth(position.value); });
$('#frame-back').addEventListener('click', () => { pauseBoth(); seekBoth(right.currentTime - .04); });
$('#frame-next').addEventListener('click', () => { pauseBoth(); seekBoth(right.currentTime + .04); });
document.querySelectorAll('input[name=audition]').forEach(x => x.addEventListener('change', () => { audition = x.value; setSound(); }));
document.querySelectorAll('[data-region]').forEach(b => b.addEventListener('click', () => loadRegion(Number(b.dataset.region))));
document.querySelectorAll('[data-jump]').forEach(a => a.addEventListener('click', () => loadRegion(Number(a.dataset.jump))));
$('#baseline-kind').addEventListener('change', async () => {
  const t = right.currentTime; pauseBoth(); changing = true; generation++; const stamp = generation; renderRegion();
  await loadMedia(left, current().media[$('#baseline-kind').value], t, stamp);
  if (stamp !== generation) return;
  changing = false; setSound(); seekBoth(t);
});
for (const video of [left, right]) {
  video.addEventListener('play', () => { if (!changing && !syncing && !playing) { seekBoth(video.currentTime); playBoth(); } });
  video.addEventListener('pause', () => { if (!changing && !syncing && playing && !video.ended) pauseBoth(); });
  video.addEventListener('seeking', () => {
    if (!changing && !syncing) {
      const other = video === left ? right : left;
      if (Math.abs(other.currentTime - video.currentTime) > .09) { syncing = true; other.currentTime = video.currentTime; syncing = false; }
    }
  });
  video.addEventListener('ended', () => { if (!changing) pauseBoth(); });
  video.addEventListener('error', () => { status.textContent = '视频加载失败，请检查网络后切换区间重试。'; pauseBoth(); });
}
right.addEventListener('timeupdate', () => { if (caseData && !changing) timeDisplay(right.currentTime); });
function tick() {
  if (caseData && playing && !changing && !right.seeking && !left.seeking) {
    if (Math.abs(left.currentTime - right.currentTime) > .14) left.currentTime = right.currentTime;
  }
  requestAnimationFrame(tick);
}
fetch('assets/case-data.json').then(r => { if (!r.ok) throw Error(r.status); return r.json(); }).then(data => { caseData = data; setSound(); renderRegion(); tick(); }).catch(() => { status.textContent = '对照数据加载失败，请刷新页面。'; });
