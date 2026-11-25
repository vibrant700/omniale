(() => {
  const buttons = [...document.querySelectorAll('[data-model-switch]')];
  const panels = [...document.querySelectorAll('[data-model-panel]')];
  const models = new Set(panels.map(panel => panel.dataset.modelPanel));

  function selectModel(model) {
    if (!models.has(model)) return;
    panels.forEach(panel => {
      const visible = panel.dataset.modelPanel === model;
      if (!visible) panel.querySelectorAll('video').forEach(video => video.pause());
      panel.hidden = !visible;
    });
    buttons.forEach(button => {
      button.setAttribute('aria-pressed', String(button.dataset.modelSwitch === model));
    });
  }

  buttons.forEach(button => {
    button.addEventListener('click', () => {
      const group = button.closest('.model-switcher');
      const top = group.getBoundingClientRect().top;
      selectModel(button.dataset.modelSwitch);
      // Keep the clicked controls in place when earlier sections change height.
      window.scrollBy({ top: group.getBoundingClientRect().top - top, behavior: 'instant' });
    });
  });

  function revealHash(hash = location.hash) {
    let id;
    try { id = decodeURIComponent(hash.slice(1)); } catch { return; }
    const target = document.getElementById(id);
    const panel = target?.closest('[data-model-panel]');
    if (!panel) return;
    selectModel(panel.dataset.modelPanel);
    if (target.matches('details')) target.open = true;
    target.scrollIntoView({ behavior: 'instant', block: 'start' });
  }

  document.querySelectorAll('a[href^="#"]').forEach(link => {
    link.addEventListener('click', () => revealHash(link.hash));
  });
  window.addEventListener('hashchange', () => revealHash());
  selectModel('astra');
  document.querySelectorAll('.model-switcher').forEach(group => { group.hidden = false; });
  revealHash();
})();
