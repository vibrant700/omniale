'use strict';
(() => {
  const video = document.querySelector('#astra-video');
  const status = document.querySelector('#seek-status');
  document.querySelectorAll('[data-seek]').forEach(button => button.addEventListener('click', () => {
    if (!video) return;
    const time = Number(button.dataset.seek);
    const seek = () => {
      video.pause();
      if (status) status.textContent = ` 正在定位至 ${time} 秒…`;
      video.addEventListener('seeked', () => { if (status) status.textContent = ` 已定位至 ${time} 秒。`; }, { once: true });
      video.currentTime = Math.min(time, video.duration || time);
    };
    if (video.readyState >= 1) seek(); else { video.addEventListener('loadedmetadata', seek, { once: true }); video.load(); }
    video.scrollIntoView({ block: 'center', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
  }));
  const links = [...document.querySelectorAll('.side-nav a')];
  const observer = new IntersectionObserver(entries => entries.forEach(entry => {
    if (!entry.isIntersecting) return;
    links.forEach(link => {
      const active = link.hash === `#${entry.target.id}`;
      link.classList.toggle('active', active);
      if (active) link.setAttribute('aria-current', 'location'); else link.removeAttribute('aria-current');
    });
  }), { rootMargin: '-15% 0px -60% 0px' });
  document.querySelectorAll('.content-section').forEach(section => observer.observe(section));
})();
