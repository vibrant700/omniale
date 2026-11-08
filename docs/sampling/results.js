'use strict';
(() => {
  const video = document.querySelector('#luna-video');
  document.querySelectorAll('[data-seek]').forEach(button => {
    button.addEventListener('click', () => {
      if (!video) return;
      const time = Number(button.dataset.seek);
      const seek = () => {
        video.pause();
        const status = document.querySelector('#seek-status');
        if (status) status.textContent = ' 正在定位至 ' + time + ' 秒…';
        const confirm = () => {
          if (status) status.textContent = Math.abs(video.currentTime - time) < .6
            ? ' 已定位至 ' + time + ' 秒。' : ' 定位未完成，请重试。';
        };
        video.addEventListener('seeked', confirm, { once: true });
        video.currentTime = Math.min(time, video.duration || time);
      };
      if (video.readyState >= 1) seek();
      else {
        video.addEventListener('loadedmetadata', seek, { once: true });
        video.load();
      }
      video.scrollIntoView({ block: 'center', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
    });
  });
  const transcript = document.querySelector('#narration-content');
  if (transcript) {
    fetch('results/luna-v03/narration.txt').then(response => {
      if (!response.ok) throw new Error('Text unavailable');
      return response.text();
    }).then(text => {
      const paragraphs = text.trim().split(/\r?\n\s*\r?\n/);
      transcript.replaceChildren(...paragraphs.map(text => {
        const p = document.createElement('p'); p.textContent = text; return p;
      }));
    }).catch(() => { transcript.textContent = '文本暂未加载，请使用下方原件链接。'; });
  }
  const container = document.querySelector('#luna-trace');
  if (!container) return;
  const search = document.querySelector('#trace-search');
  const phase = document.querySelector('#trace-phase');
  const counter = document.querySelector('#trace-count');
  const element = (tag, text, className) => {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    return node;
  };
  fetch(container.dataset.src).then(response => {
    if (!response.ok) throw new Error('Trace unavailable');
    return response.json();
  }).then(data => {
    const entries = data.entries.map(row => {
      const details = element('details', undefined, 'trace-entry');
      details.dataset.phase = row.phase;
      details.dataset.search = [row.index, row.title, row.phase, row.status, row.operation, row.return_text].join(' ').toLowerCase();
      const summary = element('summary');
      summary.append(element('span', 'T' + String(row.index).padStart(2, '0'), 'trace-number'),
        element('strong', row.title), element('span', row.time, 'trace-time'),
        element('span', row.status, row.status === '含错误信息' ? 'trace-state error' : 'trace-state'));
      details.append(summary, element('p', row.phase + ' · 工具 ' + row.tool + ' · 北京时间 ' + row.time, 'caption'));
      details.append(element('h4', row.control_notice ? '状态通知' : '实际操作（路径已替换）'), element('pre', row.operation));
      details.append(element('h4', '可见文本返回'), element('pre', row.return_text || '本次工具返回没有新的文本输出。'));
      if (row.return_truncated) details.append(element('p', '长返回在公开版本中截取至 16000 字。', 'caption'));
      return details;
    });
    container.replaceChildren(...entries);
    const filter = () => {
      const query = search ? search.value.trim().toLowerCase() : '';
      const category = phase ? phase.value : '';
      let shown = 0;
      entries.forEach(entry => {
        const match = (!query || entry.dataset.search.includes(query)) && (!category || entry.dataset.phase === category);
        entry.hidden = !match;
        if (match) shown += 1;
      });
      if (counter) counter.textContent = shown + ' / ' + entries.length + ' 条';
    };
    if (search) search.addEventListener('input', filter);
    if (phase) phase.addEventListener('change', filter);
    filter();
  }).catch(() => {
    container.replaceChildren(element('p', '轨迹暂未加载，请使用下方公开 JSON 链接。', 'caption'));
    if (counter) counter.textContent = '加载失败';
  });
})();
