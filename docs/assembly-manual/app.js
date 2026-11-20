'use strict';

(() => {
  const $ = (id) => document.getElementById(id);
  const escape = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const number = (value) => Number(value).toLocaleString('en-US', {maximumFractionDigits:3});
  const clock = (seconds) => `${String(Math.floor(seconds / 60)).padStart(2,'0')}:${String(Math.floor(seconds % 60)).padStart(2,'0')}`;
  const duration = (seconds) => { const rounded = Math.round(seconds); return `${Math.floor(rounded / 60)}分${String(rounded % 60).padStart(2,'0')}秒`; };
  const inline = (value) => escape(value).replace(/`([^`]+)`/g,'<code>$1</code>').replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>');

  // Small, escaped Markdown renderer for the public prompt and original answers.
  // Raw HTML and Markdown URLs are deliberately treated as text.
  function markdown(value) {
    const lines = String(value ?? '').replace(/\r/g,'').split('\n');
    const out = [];
    const cells = (line) => line.trim().replace(/^\||\|$/g,'').split('|').map((s) => s.trim());
    for (let i = 0; i < lines.length;) {
      const line = lines[i];
      if (!line.trim()) { i++; continue; }
      if (/^\s*```/.test(line)) {
        const code = []; i++;
        while (i < lines.length && !/^\s*```/.test(lines[i])) code.push(lines[i++]);
        i++; out.push(`<pre>${escape(code.join('\n'))}</pre>`); continue;
      }
      const heading = line.match(/^(#{1,6})\s+(.+)$/);
      if (heading) { const level = Math.min(heading[1].length + 1, 6); out.push(`<h${level}>${inline(heading[2])}</h${level}>`); i++; continue; }
      if (line.includes('|') && i + 1 < lines.length && /^\s*\|?[\s:|-]+\|[\s:|-]*$/.test(lines[i+1])) {
        const head = cells(line); i += 2; const rows = [];
        while (i < lines.length && lines[i].trim().includes('|')) rows.push(cells(lines[i++]));
        out.push(`<div class="table-wrap"><table><thead><tr>${head.map((s) => `<th>${inline(s)}</th>`).join('')}</tr></thead><tbody>${rows.map((row) => `<tr>${row.map((s) => `<td>${inline(s)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`); continue;
      }
      if (/^\s*[-*]\s/.test(line) || /^\s*\d+\.\s/.test(line)) {
        const ordered = /^\s*\d+\.\s/.test(line); const tag = ordered ? 'ol' : 'ul'; const items = [];
        const pattern = ordered ? /^\s*\d+\.\s+(.+)$/ : /^\s*[-*]\s+(.+)$/;
        while (i < lines.length && pattern.test(lines[i])) items.push(`<li>${inline(lines[i++].replace(pattern,'$1'))}</li>`);
        out.push(`<${tag}>${items.join('')}</${tag}>`); continue;
      }
      const para = [line]; i++;
      while (i < lines.length && lines[i].trim() && !/^(#{1,6}\s|\s*[-*]\s|\s*\d+\.\s|\s*```)/.test(lines[i]) && !(lines[i].includes('|') && /^\s*\|?[\s:|-]+\|[\s:|-]*$/.test(lines[i+1] || ''))) para.push(lines[i++]);
      out.push(`<p>${para.map(inline).join('<br>')}</p>`);
    }
    return out.join('\n');
  }

  let data, executions, selected, pageIndex = 0;
  const statuses = {pass:'符合',partial:'部分符合',fail:'不符合'};
  const evidenceTitles = {localization:'时间定位',claim_support:'证据支持结论'};
  const getSystem = () => data.systems[selected];

  async function fetchFile(path, asJSON = true) {
    const response = await fetch(path, {cache:'no-store'});
    if (!response.ok) throw new Error(`${path}：HTTP ${response.status}`);
    return asJSON ? response.json() : response.text();
  }
  function activateTab(id, focus = false) {
    for (const button of document.querySelectorAll('[data-tab]')) {
      const active = button.dataset.tab === id;
      button.setAttribute('aria-selected', String(active));
      button.tabIndex = active ? 0 : -1;
      $(`pane-${button.dataset.tab}`).hidden = !active;
      if (active && focus) button.focus();
    }
  }
  function renderPage(index) {
    const delivery = getSystem().delivery;
    pageIndex = Math.max(0, Math.min(delivery.pages - 1, index));
    $('manual-page').value = String(pageIndex + 1);
    $('manual-image').src = delivery.pageImages[pageIndex];
    $('manual-image').alt = `${getSystem().label}实际交付 · 第${pageIndex + 1}页 · ${delivery.pageTopics[pageIndex] || ''}`;
    $('page-full').href = delivery.pageImages[pageIndex];
    $('page-label').textContent = `${String(pageIndex + 1).padStart(2,'0')} / ${String(delivery.pages).padStart(2,'0')}`;
    $('prev-page').disabled = pageIndex === 0;
    $('next-page').disabled = pageIndex === delivery.pages - 1;
  }
  function checkTable(checks, referenceClaims) {
    return `<div class="table-wrap"><table class="check-table"><thead><tr><th>小项</th><th>判定</th><th>得分</th><th>具体依据</th></tr></thead><tbody>${checks.map((check, i) => `<tr><td>${escape(evidenceTitles[check.id] || check.id)}</td><td><span class="status ${escape(check.status)}">${statuses[check.status] || escape(check.status)}</span></td><td class="num">${number(check.score)} / ${number(check.maximum)}</td><td>${referenceClaims ? `<b>${escape(referenceClaims[i])}</b><br>` : ''}${escape(check.reason)}</td></tr>`).join('')}</tbody></table></div>`;
  }
  function renderQuestions(system) {
    $('qa-summary').innerHTML = `<table class="qa-summary-table"><thead><tr><th>题目</th><th>回答 /5</th><th>证据 /2</th><th>合计 /7</th></tr></thead><tbody>${system.qa.map((q) => `<tr><td><a href="#${q.id}" data-open-question="${q.id}">${escape(q.id)} · ${escape(q.title)}</a></td><td class="num">${number(q.scores.qa)}</td><td class="num">${number(q.scores.evidence)}</td><td class="num">${number(q.scores.total)}</td></tr>`).join('')}<tr><td><b>合计</b></td><td class="num"><b>${number(system.result.groups.qa.score)} /50</b></td><td class="num"><b>${number(system.result.groups.evidence.score)} /20</b></td><td class="num"><b>${number(system.result.groups.qa.score + system.result.groups.evidence.score)} /70</b></td></tr></tbody></table>`;
    $('qa-list').innerHTML = system.qa.map((q) => `<details class="question-card" id="${q.id}"><summary><span class="q-id">${q.id}</span><span class="summary-title">${escape(q.title)}</span><span class="summary-score">${number(q.scores.total)} <small>/7</small></span></summary><div class="detail-body"><h4>题目</h4><p class="question-text">${escape(q.question)}</p><button class="inline-button source-seek" data-seek="${q.sourceStart}">到源录像 ${clock(q.sourceStart)} ↗</button><h4>Agent实际回答（完整原文）</h4><div class="answer">${markdown(q.candidateAnswer)}</div><h4>参考事实与事件关系</h4><p class="note">${escape(q.annotationBasis)}</p><h4>回答判分 · ${number(q.scores.qa)}/5</h4>${checkTable(q.qaChecks,q.referenceClaims)}<h4>证据判分 · ${number(q.scores.evidence)}/2</h4>${checkTable(q.evidenceChecks)}<p class="judgment-total">本题：${number(q.scores.qa)}＋${number(q.scores.evidence)}＝<b>${number(q.scores.total)} /7</b>。手册质量另按整份手册评价，不摊入本题。</p></div></details>`).join('');
  }
  function renderManual(system) {
    const manual = system.manual;
    const critical = manual.dimensions.filter((dim) => dim.criticalZero);
    $('manual-score-intro').textContent = `${manual.errors.length}个独立问题，按根因唯一归属四个维度。当前手册得分${number(manual.score)}/${number(manual.maximum)}；${critical.length ? `${critical.map((dim) => dim.title).join('、')}触发关键错误归零` : '本次没有触发关键错误归零'}。`;
    $('manual-score-table').innerHTML = `<table class="manual-dimension-table"><thead><tr><th>维度</th><th>独立问题</th><th>问题单位</th><th>等级 /3</th><th>折算</th><th>得分 /7.5</th></tr></thead><tbody>${manual.dimensions.map((dim) => `<tr><td><b>${escape(dim.title)}</b><span class="dim-id">${dim.id}</span></td><td>${dim.errorIds.map((id) => `<a href="#${id}" data-open-error="${id}">${id}</a>`).join('、') || '无'}</td><td class="num">${number(dim.units)}</td><td class="num">${dim.level}${dim.criticalZero ? '（关键错误）' : ''}</td><td class="num">${dim.level}÷3×7.5</td><td class="num"><b>${number(dim.score)}</b></td></tr>`).join('')}<tr><td colspan="5"><b>手册质量合计</b></td><td class="num"><b>${number(manual.score)} /30</b></td></tr></tbody></table>`;
    $('manual-errors').innerHTML = manual.errors.map((error) => `<details class="error-card" id="${error.id}"><summary><span class="q-id">${error.id}</span><span class="summary-title">${escape(error.title || `第${error.pages.join('、')}页`)}</span><span class="severity">${escape(error.severityLabel)} · ${error.severity === 'critical' ? '所属维度归零' : `${error.units}单位`}</span><span class="error-owner">${escape(error.ownerTitle)} ${error.owner}</span></summary><div class="detail-body"><p class="error-meta">手册位置：${escape(error.location)}</p><dl><dt>实际问题</dt><dd>${escape(error.observation)}</dd><dt>对照依据</dt><dd>${escape(error.source_evidence)}</dd><dt>对读者的影响</dt><dd>${escape(error.impact)}</dd><dt>严重性与唯一归属</dt><dd>${escape(error.severity_reason)}</dd></dl><button class="inline-button" data-manual-page="${error.pages[0]}">查看手册第${error.pages[0]}页 →</button></div></details>`).join('');
  }
  function renderExecution() {
    const execution = executions?.systems?.[selected];
    $('execution-intro').textContent = execution ? `${duration(getSystem().meta.elapsedSeconds)}的实际运行，按工作内容归纳如下。展开可见真实工具记录的命令与输出摘录；步骤按内容组织，部分操作交替进行。` : '当前结果尚未附执行摘录。';
    $('execution-steps').innerHTML = (execution?.steps || []).map((step, i) => `<details class="execution-step"><summary><span class="step-no">${String(i + 1).padStart(2,'0')}</span><span class="summary-title">${escape(step.title)}</span></summary><div class="detail-body"><p class="execution-summary">${escape(step.summary)}</p>${step.evidence.map((e) => `<div class="execution-evidence"><h4>${escape(e.itemId)} · ${escape(e.tool || e.type)}</h4>${e.command ? `<pre>${escape(e.command)}</pre>` : ''}${e.arguments ? `<pre>${escape(JSON.stringify(e.arguments,null,2))}</pre>` : ''}${e.files ? `<pre>${escape(e.files.join('\n'))}</pre>` : ''}${e.outputSnippet ? `<pre>${escape(e.outputSnippet)}</pre>` : ''}</div>`).join('')}</div></details>`).join('');
  }
  function renderAnalysis(system) {
    const groups = system.result.groups;
    $('analysis-intro').textContent = `回答与证据合计${number(groups.qa.score + groups.evidence.score)}/70，手册${number(groups.manual.score)}/30。下面按手册维度归纳有证据支持的问题，详细判定与分数可回到对应错误条目查看。`;
    const lowest = system.qa.filter((q) => q.scores.total < q.scores.maximum).sort((a,b) => a.scores.total - b.scores.total).slice(0,3);
    $('qa-findings').innerHTML = lowest.length ? `<h3>回答与证据中的主要失分</h3><p class="note">本次得分较低的三题如下；展开查看已有逐项裁定，点击题号可阅读完整原答。</p>${lowest.map((q) => `<details class="disclosure"><summary>${escape(q.id)} · ${escape(q.title)} · ${number(q.scores.total)}/7</summary><p class="note">回答${number(q.scores.qa)}/5，证据${number(q.scores.evidence)}/2。</p>${q.qaChecks.filter((c) => c.status === 'fail').map((c) => `<p><b>${c.id} 不符合：</b>${escape(c.reason)}</p>`).join('') || `<p>${escape(q.qaChecks.find((c) => c.status === 'partial')?.reason || q.evidenceChecks.find((c) => c.status !== 'pass')?.reason || '')}</p>`}<a href="#${q.id}" data-open-question="${q.id}">查看${q.id}完整回答与评分 ↑</a></details>`).join('')}<h3>手册中的主要问题</h3>` : '';
    $('failure-findings').innerHTML = system.manual.dimensions.filter((dim) => dim.errorIds.length).map((dim) => {
      const errors = system.manual.errors.filter((e) => e.owner === dim.id);
      return `<article class="finding"><h3>${escape(dim.title)} · ${number(dim.score)}/${number(dim.weight)}</h3>${errors.map((e) => `<p>${escape(e.observation)}</p>`).join('')}<p class="note">${dim.errorIds.map((id) => `<a href="#${id}" data-open-error="${id}">${id}</a>`).join('、')}：${dim.units}问题单位 → 等级${dim.level} → ${number(dim.score)}分。<a href="#pane-manual" data-show-tab="manual">查看完整判定依据 ↑</a></p></article>`;
    }).join('');
    $('review-images').innerHTML = (system.manual.reviewImages || []).map((img) => `<figure><a href="${escape(img.src)}" target="_blank" rel="noopener"><img src="${escape(img.src)}" alt="${escape(img.caption)}" loading="lazy"></a><figcaption>${escape(img.caption)} <button class="inline-button" data-manual-page="${img.page}">查看整页 ↗</button></figcaption></figure>`).join('');
    $('review-disclosure').hidden = !(system.manual.reviewImages || []).length;
    $('review-intro').textContent = '以下为当前模型实际交付的局部放大图。对应问题的严重性、唯一归属与计分依据见“手册质量评分”。';
  }
  function selectSystem(id, updateURL = true) {
    selected = Object.hasOwn(data.systems,id) ? id : data.defaultSystem;
    const system = getSystem(); const meta = system.meta; const delivery = system.delivery;
    $('result-system').value = selected;
    for (const row of document.querySelectorAll('#systems-table tr')) row.classList.toggle('active', row.dataset.system === selected);
    for (const button of document.querySelectorAll('[data-select-system]')) { const active = button.dataset.selectSystem === selected; button.setAttribute('aria-pressed',String(active)); button.textContent = active ? '查看当前结果 ↓' : '查看交付与评分 ↓'; }
    $('system-status').textContent = `${system.label} · ${system.result.scoreDisplay} /100`;
    $('run-config').innerHTML = [
      ['运行框架',`${meta.framework} ${meta.codexVersion}`],['推理强度',`${meta.reasoningEffort} · ${meta.requestCount}次请求${meta.allRequestsExplicitXhigh ? '逐条确认' : '记录'}`],['总运行时间',duration(meta.elapsedSeconds)],['工具调用',`${meta.toolCalls}次（含${meta.asrCalls}次本地ASR）`]
    ].map(([key,value]) => `<div><dt>${escape(key)}</dt><dd>${escape(value)}</dd></div>`).join('') + `<div class="run-note">音频工具：${escape(meta.audioTool)}；${meta.nativeAudio ? '使用原生音频输入' : '无原生音频输入'}。${meta.timeLimit == null ? '无总答题时限' : `总时限${duration(meta.timeLimit)}`}，${meta.toolLimit == null ? '无工具次数上限' : `工具上限${meta.toolLimit}次`}。运行时间包含模型与工具，不含评分。</div>`;
    $('delivery-title').textContent = `${system.label} · ${delivery.pages}页实际手册`;
    $('delivery-description').textContent = `${delivery.screenshotsCount}张原截图＋${delivery.annotationsCount}份SVG标注源；PDF、Word和完整交付均可下载。`;
    for (const [element,key] of [['download-pdf','pdf'],['download-docx','docx'],['download-bundle','editableBundle'],['download-answers','answers']]) $(element).href = delivery[key];
    $('manual-page').innerHTML = delivery.pageImages.map((_,i) => `<option value="${i+1}">第${i+1}页 · ${escape(delivery.pageTopics[i] || '')}</option>`).join('');
    renderPage(0); renderQuestions(system); renderManual(system); renderExecution(); renderAnalysis(system);
    $('source-chapter').innerHTML = '<option value="0">完整录像 · 从头开始</option>' + system.qa.map((q) => `<option value="${q.sourceStart}">${q.id} · ${escape(q.title)} · ${clock(q.sourceStart)}</option>`).join('');
    if (updateURL) { const url = new URL(location.href); url.searchParams.set('model',selected); history.replaceState(null,'',url); }
  }
  async function seekSource(time) {
    const video = $('source-video');
    if (video.readyState < 1) await new Promise((resolve) => video.addEventListener('loadedmetadata',resolve,{once:true}));
    video.pause(); video.currentTime = Number(time);
    $('video-status').textContent = `已定位 ${clock(Number(time))}，点击播放可听取该片段。`;
    video.scrollIntoView({behavior:'smooth',block:'center'});
  }
  function openQuestion(id) { activateTab('qa'); const node = $(id); if (node) { node.open = true; node.scrollIntoView({behavior:'smooth',block:'start'}); } }
  function openError(id) { activateTab('manual'); const node = $(id); if (node) { node.open = true; node.scrollIntoView({behavior:'smooth',block:'start'}); } }
  function handleHash() { if (/^#Q\d+$/.test(location.hash)) openQuestion(location.hash.slice(1)); else if (/^#E\d+$/.test(location.hash)) openError(location.hash.slice(1)); else if (location.hash === '#pane-qa') activateTab('qa'); else if (location.hash === '#pane-manual') activateTab('manual'); }

  document.addEventListener('click',(event) => {
    const target = event.target.closest('button,a'); if (!target) return;
    if (target.dataset.tab) activateTab(target.dataset.tab);
    if (target.dataset.selectSystem) { selectSystem(target.dataset.selectSystem); activateTab('delivery'); $('result-system').scrollIntoView({behavior:'smooth',block:'center'}); }
    if (target.dataset.seek) seekSource(target.dataset.seek);
    if (target.dataset.manualPage) { activateTab('delivery'); renderPage(Number(target.dataset.manualPage)-1); $('manual-page').scrollIntoView({behavior:'smooth',block:'center'}); }
    if (target.dataset.openQuestion) { event.preventDefault(); openQuestion(target.dataset.openQuestion); history.replaceState(null,'',`#${target.dataset.openQuestion}`); }
    if (target.dataset.openError) { event.preventDefault(); openError(target.dataset.openError); history.replaceState(null,'',`#${target.dataset.openError}`); }
    if (target.dataset.showTab) { event.preventDefault(); activateTab(target.dataset.showTab); $('result-system').scrollIntoView({behavior:'smooth',block:'start'}); }
  });
  document.querySelector('.result-tabs').addEventListener('keydown',(event) => {
    const tabs = [...document.querySelectorAll('[data-tab]')]; let index = tabs.indexOf(document.activeElement);
    if (index < 0) return;
    if (event.key === 'ArrowRight') index = (index + 1) % tabs.length;
    else if (event.key === 'ArrowLeft') index = (index + tabs.length - 1) % tabs.length;
    else if (event.key === 'Home') index = 0;
    else if (event.key === 'End') index = tabs.length - 1;
    else return;
    event.preventDefault(); activateTab(tabs[index].dataset.tab,true);
  });
  $('result-system').addEventListener('change',(event) => selectSystem(event.target.value));
  $('manual-page').addEventListener('change',(event) => renderPage(Number(event.target.value)-1));
  $('prev-page').addEventListener('click',() => renderPage(pageIndex-1));
  $('next-page').addEventListener('click',() => renderPage(pageIndex+1));
  $('source-chapter').addEventListener('change',(event) => seekSource(event.target.value));
  window.addEventListener('hashchange',handleHash);

  (async () => {
    const loaded = await Promise.allSettled([fetchFile('data-v2.json'),fetchFile('execution-v2.json'),fetchFile('TASK.zh-CN.md',false)]);
    if (loaded[0].status !== 'fulfilled') throw loaded[0].reason;
    data = loaded[0].value;
    if (data.schemaVersion !== 2 || !data.systems[data.defaultSystem]) throw new Error('评分数据版本或默认结果不正确');
    executions = loaded[1].status === 'fulfilled' ? loaded[1].value : null;
    $('task-prompt').innerHTML = loaded[2].status === 'fulfilled' ? markdown(loaded[2].value) : '<p>请通过下方链接阅读题面原文。</p>';
    $('systems-table').innerHTML = Object.entries(data.systems).map(([id,system]) => `<tr data-system="${escape(id)}"><td><b>${escape(system.meta.model)}</b><small>Codex · ${escape(system.meta.reasoningEffort)}</small></td><td class="num total-cell">${escape(system.result.scoreDisplay)}</td><td class="num">${number(system.result.groups.qa.score)}</td><td class="num">${number(system.result.groups.evidence.score)}</td><td class="num">${number(system.result.groups.manual.score)}</td><td><button data-select-system="${escape(id)}" aria-pressed="false">查看交付与评分 ↓</button></td></tr>`).join('');
    $('result-system').innerHTML = Object.entries(data.systems).map(([id,system]) => `<option value="${escape(id)}">${escape(system.label)}</option>`).join('');
    $('rubric-dimensions').innerHTML = data.systems[data.defaultSystem].manual.dimensions.map((dim) => `<tr><td><b>${escape(dim.title)}</b><span class="dim-id">${dim.id}</span></td><td class="num">${number(dim.weight)}</td><td>${escape(dim.criterion)}</td></tr>`).join('');
    $('task-questions').innerHTML = data.systems[data.defaultSystem].qa.map((q) => `<h3>${escape(q.id)} · ${escape(q.title)}</h3><p>${escape(q.question)}</p>`).join('');
    selectSystem(new URLSearchParams(location.search).get('model') || data.defaultSystem);
    $('result-system').disabled = false;
    handleHash();
  })().catch((error) => {
    $('load-error').hidden = false; $('load-error').textContent = `页面资料未能完整载入：${error.message}。请刷新页面，或使用文件下载链接查看。`;
    $('system-status').textContent = '结果载入失败';
  });
})();
