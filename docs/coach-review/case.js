(() => {
  function revealHash(hash = location.hash) {
    let id;
    try { id = decodeURIComponent(hash.slice(1)); } catch { return; }
    const target = document.getElementById(id);
    if (!target) return;
    if (target.matches('details')) target.open = true;
    target.scrollIntoView({ behavior: 'instant', block: 'start' });
  }
  document.querySelectorAll('a[href^="#"]').forEach(link => {
    link.addEventListener('click', () => revealHash(link.hash));
  });
  window.addEventListener('hashchange', () => revealHash());
  revealHash();
})();
