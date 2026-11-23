"use strict";

(() => {
  const dialog = document.querySelector("#image-dialog");
  const dialogImage = document.querySelector("#dialog-image");
  const dialogTitle = document.querySelector("#dialog-title");
  const dialogOriginal = document.querySelector("#dialog-original");
  let zoomTrigger = null;

  if (dialog && typeof dialog.showModal === "function") {
    document.querySelectorAll("[data-zoom]").forEach((link) => {
      link.addEventListener("click", (event) => {
        if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
        event.preventDefault();
        zoomTrigger = link;
        dialogTitle.textContent = link.dataset.title || "图片预览";
        dialogImage.alt = link.querySelector("img")?.alt || dialogTitle.textContent;
        dialogImage.src = link.href;
        dialogOriginal.href = link.href;
        document.body.classList.add("dialog-open");
        dialog.showModal();
      });
    });

    dialog.addEventListener("click", (event) => {
      if (event.target !== dialog) return;
      const bounds = dialog.getBoundingClientRect();
      if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) dialog.close();
    });

    dialog.addEventListener("close", () => {
      document.body.classList.remove("dialog-open");
      dialogImage.src = "data:,";
      zoomTrigger?.focus({ preventScroll: true });
    });
  }

  const views = {
    front: "正面",
    back: "背面",
    left: "机甲左侧",
    right: "机甲右侧",
    top: "顶面",
    bottom: "底面"
  };
  const tabs = Array.from(document.querySelectorAll("[data-view]"));
  const panel = document.querySelector("#comparison-panel");
  const comparisonImage = document.querySelector("#comparison-image");
  const comparisonZoom = document.querySelector("#comparison-zoom");

  function selectView(tab, focus = false) {
    const view = tab.dataset.view;
    const label = views[view];
    if (!label) return;
    tabs.forEach((item) => {
      const selected = item === tab;
      item.setAttribute("aria-selected", String(selected));
      item.tabIndex = selected ? 0 : -1;
    });
    panel.setAttribute("aria-labelledby", tab.id);
    comparisonImage.src = `assets/comparison/${view}.webp`;
    comparisonImage.alt = `${label}并排对照：左侧为输入参考图，右侧为重建图`;
    comparisonZoom.href = `assets/comparison/${view}.webp`;
    comparisonZoom.dataset.title = `${label} · 参考与重建对照`;
    document.querySelector("#comparison-caption").textContent = `${label} · 左：输入参考；右：统一机位与灯光下的重建。`;
    document.querySelector("#comparison-reference").href = `assets/reference/${view}.png`;
    document.querySelector("#comparison-reconstruction").href = `assets/reconstruction/${view}.png`;
    if (focus) tab.focus();
  }

  tabs.forEach((tab, index) => {
    tab.addEventListener("click", () => selectView(tab));
    tab.addEventListener("keydown", (event) => {
      let next = index;
      if (event.key === "ArrowRight") next = (index + 1) % tabs.length;
      else if (event.key === "ArrowLeft") next = (index - 1 + tabs.length) % tabs.length;
      else if (event.key === "Home") next = 0;
      else if (event.key === "End") next = tabs.length - 1;
      else return;
      event.preventDefault();
      selectView(tabs[next], true);
    });
  });

  const video = document.querySelector("#showcase-video");
  const status = document.querySelector("#player-status");
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  let pendingSeek = null;

  function applySeek() {
    if (pendingSeek === null) return;
    const target = pendingSeek;
    pendingSeek = null;
    video.pause();
    video.currentTime = Math.max(0, Math.min(target, Number.isFinite(video.duration) ? video.duration : target));
    status.textContent = `成片已定位到 ${target.toFixed(3)} 秒。可播放查看当前片段。`;
    video.focus({ preventScroll: true });
  }

  video?.addEventListener("loadedmetadata", applySeek);
  document.querySelectorAll("[data-seek]").forEach((button) => {
    button.addEventListener("click", () => {
      const target = Number(button.dataset.seek);
      if (!video || !Number.isFinite(target)) return;
      pendingSeek = target;
      video.scrollIntoView({ behavior: reducedMotion.matches ? "instant" : "smooth", block: "center" });
      if (video.readyState >= 1) applySeek();
      else video.load();
    });
  });
})();
