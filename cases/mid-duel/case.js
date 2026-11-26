(() => {
  const tabs = [...document.querySelectorAll('[data-report]')];
  function select(name, focus = false) {
    tabs.forEach(tab => {
      const on = tab.dataset.report === name;
      tab.setAttribute('aria-selected', String(on)); tab.tabIndex = on ? 0 : -1;
      document.getElementById(tab.getAttribute('aria-controls')).hidden = !on;
      if (on && focus) tab.focus();
    });
    if (name === 'analysis') document.querySelector('video').pause();
  }
  tabs.forEach((tab, i) => {
    tab.addEventListener('click', () => select(tab.dataset.report));
    tab.addEventListener('keydown', e => {
      let j;
      if (e.key === 'ArrowRight') j = (i + 1) % tabs.length;
      if (e.key === 'ArrowLeft') j = (i + tabs.length - 1) % tabs.length;
      if (e.key === 'Home') j = 0;
      if (e.key === 'End') j = tabs.length - 1;
      if (j !== undefined) { e.preventDefault(); select(tabs[j].dataset.report, true); }
    });
  });
  function reveal() {
    const id = decodeURIComponent(location.hash.slice(1));
    if (id === 'analysis') { select('analysis'); document.getElementById('results').scrollIntoView(); return; }
    const target = document.getElementById(id);
    if (!target) return;
    if (id === 'results' || target.closest('#panel-results')) select('results');
    if (target.matches('details')) target.open = true;
    target.scrollIntoView();
  }
  document.querySelectorAll('a[href^="#"]').forEach(a => a.addEventListener('click', () => setTimeout(reveal, 0)));
  window.addEventListener('hashchange', reveal);
  if (location.hash) reveal();
  document.querySelectorAll('[data-seek]').forEach(button => button.addEventListener('click', () => {
    const video = document.querySelector('video');
    const seek = () => { video.currentTime = Number(button.dataset.seek); video.play().catch(() => {}); };
    if (video.readyState >= 1) seek(); else { video.addEventListener('loadedmetadata', seek, {once:true}); video.load(); }
    document.getElementById('delivery').scrollIntoView({block:'center'});
  }));
})();
