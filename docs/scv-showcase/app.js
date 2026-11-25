"use strict";

(() => {
  const metadata = JSON.parse(document.querySelector("#model-metadata").textContent);
  const views = { front: "正面", back: "背面", left: "机甲左侧", right: "机甲右侧", top: "顶面", bottom: "底面" };
  const sections = ["results", "execution", "analysis"];
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const status = document.querySelector("#player-status");
  const dialog = document.querySelector("#image-dialog");
  let selected = "astra62-xhigh";
  let currentView = "front";
  let pendingSeek = null;
  let zoomTrigger = null;

  function video() {
    return document.querySelector("#showcase-video");
  }

  function applySeek() {
    const player = video();
    if (!player || pendingSeek === null || player.readyState < 1) return;
    const target = pendingSeek;
    pendingSeek = null;
    player.pause();
    player.currentTime = Math.max(0, Math.min(target, player.duration));
    player.focus({ preventScroll: true });
    status.textContent = `${metadata[selected].name} 成片已定位到 ${target.toFixed(3)} 秒。`;
  }

  function bindVideo() {
    const player = video();
    player?.addEventListener("loadedmetadata", () => {
      if (player === video()) applySeek();
    });
  }

  function selectView(view, focus = false) {
    if (!views[view]) return;
    currentView = view;
    const label = views[view];
    const model = metadata[selected];
    const prefix = model.assetsRoot;
    document.querySelectorAll("[data-view]").forEach((tab) => {
      const active = tab.dataset.view === view;
      tab.setAttribute("aria-selected", String(active));
      tab.tabIndex = active ? 0 : -1;
    });
    const image = document.querySelector("#comparison-image");
    const zoom = document.querySelector("#comparison-zoom");
    image.src = `${prefix}/comparison/${view}.webp`;
    image.alt = `${model.name} ${label}并排对照：左为输入参考，右为重建`;
    zoom.href = image.src;
    zoom.dataset.title = `${model.name} · ${label}参考与重建对照`;
    document.querySelector("#comparison-caption").textContent = `${model.name} · ${label} · 左：输入参考；右：统一机位与灯光下的重建。`;
    document.querySelector("#comparison-reference").href = `assets/reference/${view}.png`;
    document.querySelector("#comparison-reconstruction").href = `${prefix}/reconstruction/${view}.png`;
    document.querySelector("#comparison-panel").setAttribute("aria-labelledby", `view-${view}`);
    if (focus) document.querySelector(`[data-view="${view}"]`).focus();
  }

  function selectModel(id, { updateUrl = true, focusTab = false } = {}) {
    if (!metadata[id]) return;
    const readingLine = Math.min(window.innerHeight / 2, document.querySelector("#model-switcher").offsetHeight + 100);
    const readingSection = ["execution", "analysis"].map(name => document.getElementById(name)).find(section => {
      const bounds = section.getBoundingClientRect();
      return bounds.top <= readingLine && bounds.bottom > readingLine;
    });
    video()?.pause();
    pendingSeek = null;
    selected = id;
    for (const name of sections) {
      const template = document.querySelector(`template[data-model-template="${id}"][data-section="${name}"]`);
      const panel = document.querySelector(`[data-model-section="${name}"]`);
      panel.replaceChildren(template.content.cloneNode(true));
      panel.dataset.model = id;
      panel.setAttribute("aria-labelledby", `model-tab-${id}`);
    }
    document.querySelectorAll("[data-select-model]").forEach((button) => {
      const active = button.dataset.selectModel === id;
      if (button.getAttribute("role") === "tab") {
        button.setAttribute("aria-selected", String(active));
        button.tabIndex = active ? 0 : -1;
      } else button.setAttribute("aria-pressed", String(active));
    });
    document.querySelectorAll("[data-result-model]").forEach((row) => {
      row.dataset.selected = String(row.dataset.resultModel === id);
    });
    document.querySelectorAll("[data-model-name]").forEach((node) => { node.textContent = metadata[id].name; });
    document.querySelectorAll("[data-selected-asset]").forEach((link) => { link.href = metadata[id].asset; });
    bindVideo();
    selectView(currentView);
    if (updateUrl) {
      const url = new URL(window.location.href);
      url.searchParams.set("model", id);
      window.history.replaceState(null, "", url);
    }
    if (readingSection) readingSection.scrollIntoView({ behavior: "instant", block: "start" });
    if (focusTab) document.querySelector(`#model-tab-${id}`).focus({ preventScroll: true });
    status.textContent = `当前查看 ${metadata[id].name} 的成片、过程和失败分析。`;
  }

  document.addEventListener("click", (event) => {
    const modelButton = event.target.closest("[data-select-model]");
    if (modelButton) {
      selectModel(modelButton.dataset.selectModel);
      return;
    }
    const viewButton = event.target.closest("[data-view]");
    if (viewButton) {
      selectView(viewButton.dataset.view);
      return;
    }
    const seekButton = event.target.closest("[data-seek]");
    if (seekButton) {
      const target = Number(seekButton.dataset.seek);
      if (!Number.isFinite(target)) return;
      pendingSeek = target;
      video().scrollIntoView({ behavior: reducedMotion.matches ? "instant" : "smooth", block: "center" });
      if (video().readyState >= 1) applySeek();
      else video().load();
      return;
    }
    const zoom = event.target.closest("[data-zoom]");
    if (zoom && typeof dialog?.showModal === "function") {
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      zoomTrigger = zoom;
      document.querySelector("#dialog-title").textContent = zoom.dataset.title || "图片预览";
      const image = document.querySelector("#dialog-image");
      image.alt = zoom.querySelector("img")?.alt || zoom.dataset.title || "图片预览";
      image.src = zoom.href;
      document.querySelector("#dialog-original").href = zoom.href;
      document.body.classList.add("dialog-open");
      dialog.showModal();
    }
  });

  document.addEventListener("keydown", (event) => {
    const isModel = event.target.matches('.model-tabs [role="tab"]');
    const isView = event.target.matches('[data-view][role="tab"]');
    if (!isModel && !isView) return;
    const tabs = Array.from(document.querySelectorAll(isModel ? '.model-tabs [role="tab"]' : '[data-view][role="tab"]'));
    let next = tabs.indexOf(event.target);
    if (event.key === "ArrowRight") next = (next + 1) % tabs.length;
    else if (event.key === "ArrowLeft") next = (next - 1 + tabs.length) % tabs.length;
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = tabs.length - 1;
    else return;
    event.preventDefault();
    if (isModel) selectModel(tabs[next].dataset.selectModel, { focusTab: true });
    else selectView(tabs[next].dataset.view, true);
  });

  dialog?.addEventListener("click", (event) => {
    if (event.target !== dialog) return;
    const bounds = dialog.getBoundingClientRect();
    if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) dialog.close();
  });
  dialog?.addEventListener("close", () => {
    document.body.classList.remove("dialog-open");
    document.querySelector("#dialog-image").src = "data:,";
    zoomTrigger?.focus({ preventScroll: true });
  });

  const requested = new URLSearchParams(window.location.search).get("model");
  selectModel(metadata[requested] ? requested : selected, { updateUrl: false });
})();
