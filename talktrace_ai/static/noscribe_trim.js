/*
 * Self-contained audio waveform + trim widget for the Transcription tab.
 *
 * No external library, no CDN: the audio file is served locally by a Shiny
 * dynamic route, decoded in-browser via the Web Audio API, drawn on a <canvas>,
 * and two draggable handles let the user pick a keep-range. The handle times
 * are written (HH:MM:SS) into the existing noScribe start/stop text inputs, so
 * only the selected range is transcribed — no physical cutting of the file.
 *
 * Activation: a `<div class="ttai-trim" data-audio-url=... data-start-input=...
 * data-stop-input=...>` rendered by handlers/noscribe.py is picked up by a
 * MutationObserver and initialised. Re-rendering (new file) re-initialises.
 */
(function () {
  "use strict";

  function injectStyle() {
    if (document.getElementById("ttai-trim-style")) return;
    const css = `
      .ttai-trim-wrap{position:relative;width:100%;height:96px;
        border:1px solid var(--bs-border-color,#ccc);border-radius:.4rem;
        background:var(--bs-tertiary-bg,#f3f4f6);overflow:hidden;
        touch-action:none;user-select:none;}
      .ttai-trim-canvas{position:absolute;inset:0;width:100%;height:100%;display:block;}
      .ttai-trim-region{position:absolute;top:0;bottom:0;
        background:rgba(91,141,239,.16);border-left:2px solid #5b8def;
        border-right:2px solid #5b8def;pointer-events:none;}
      .ttai-trim-mask{position:absolute;top:0;bottom:0;
        background:rgba(120,120,120,.35);pointer-events:none;}
      .ttai-trim-h{position:absolute;top:0;bottom:0;width:12px;margin-left:-6px;
        cursor:ew-resize;display:flex;align-items:center;justify-content:center;}
      .ttai-trim-h::after{content:"";width:2px;height:100%;background:#3b6fe0;}
      .ttai-trim-h::before{content:"";position:absolute;top:50%;transform:translateY(-50%);
        width:10px;height:22px;background:#3b6fe0;border-radius:3px;opacity:.9;}
      .ttai-trim-cursor{position:absolute;top:0;bottom:0;width:1px;
        background:#d6336c;pointer-events:none;display:none;}
      .ttai-trim-controls{display:flex;align-items:center;gap:.6rem;
        margin-top:.4rem;flex-wrap:wrap;font-size:.85rem;}
      .ttai-trim-readout{font-variant-numeric:tabular-nums;color:var(--bs-secondary-color,#666);}
      .ttai-trim-status{color:var(--bs-secondary-color,#888);}
    `;
    const style = document.createElement("style");
    style.id = "ttai-trim-style";
    style.textContent = css;
    document.head.appendChild(style);
  }

  function fmtClock(t) {
    t = Math.max(0, Math.round(t));
    const h = Math.floor(t / 3600), m = Math.floor((t % 3600) / 60), s = t % 60;
    const p = (n) => String(n).padStart(2, "0");
    return p(h) + ":" + p(m) + ":" + p(s);
  }

  function setField(id, value, dispatch) {
    const el = document.getElementById(id);
    if (!el) return;
    el.value = value;
    if (dispatch) {
      el.dispatchEvent(new Event("input", { bubbles: true }));
      el.dispatchEvent(new Event("change", { bubbles: true }));
    }
  }

  function drawWave(canvas, buffer) {
    const ctx = canvas.getContext("2d");
    const W = canvas.width, H = canvas.height;
    ctx.clearRect(0, 0, W, H);
    const data = buffer.getChannelData(0);
    const step = Math.max(1, Math.floor(data.length / W));
    const mid = H / 2;
    ctx.fillStyle = "#5b8def";
    for (let x = 0; x < W; x++) {
      let min = 1.0, max = -1.0;
      const base = x * step;
      for (let i = 0; i < step; i++) {
        const v = data[base + i] || 0;
        if (v < min) min = v;
        if (v > max) max = v;
      }
      const y1 = mid + min * mid;
      const y2 = mid + max * mid;
      ctx.fillRect(x, y1, 1, Math.max(1, y2 - y1));
    }
  }

  function ttaiInitTrim(el) {
    const url = el.dataset.audioUrl;
    const startId = el.dataset.startInput;
    const stopId = el.dataset.stopInput;
    const L = {
      play: el.dataset.labelPlay || "Play",
      pause: el.dataset.labelPause || "Pause",
      reset: el.dataset.labelReset || "Reset",
      region: el.dataset.labelRegion || "Range",
      decoding: el.dataset.labelDecoding || "Loading waveform…",
      failed: el.dataset.labelFailed || "Waveform unavailable.",
    };

    el.innerHTML = "";
    const wrap = document.createElement("div");
    wrap.className = "ttai-trim-wrap";
    const canvas = document.createElement("canvas");
    canvas.className = "ttai-trim-canvas";
    const maskL = document.createElement("div"); maskL.className = "ttai-trim-mask";
    const maskR = document.createElement("div"); maskR.className = "ttai-trim-mask";
    const region = document.createElement("div"); region.className = "ttai-trim-region";
    const hStart = document.createElement("div"); hStart.className = "ttai-trim-h ttai-trim-h-start";
    const hEnd = document.createElement("div"); hEnd.className = "ttai-trim-h ttai-trim-h-end";
    const cursor = document.createElement("div"); cursor.className = "ttai-trim-cursor";
    wrap.append(canvas, maskL, maskR, region, hStart, hEnd, cursor);

    const controls = document.createElement("div");
    controls.className = "ttai-trim-controls";
    const playBtn = document.createElement("button");
    playBtn.type = "button";
    playBtn.className = "btn btn-sm btn-outline-primary ttai-trim-play";
    playBtn.textContent = "▶ " + L.play;
    const resetBtn = document.createElement("button");
    resetBtn.type = "button";
    resetBtn.className = "btn btn-sm btn-outline-secondary ttai-trim-reset";
    resetBtn.textContent = L.reset;
    const readout = document.createElement("span");
    readout.className = "ttai-trim-readout";
    const status = document.createElement("span");
    status.className = "ttai-trim-status";
    status.textContent = L.decoding;
    controls.append(playBtn, resetBtn, readout, status);

    const audio = document.createElement("audio");
    audio.preload = "auto";
    audio.src = url;

    el.append(wrap, controls, audio);

    const state = { dur: 0, pStart: 0, pEnd: 1, ready: false, raf: 0, buffer: null };

    function layout() {
      const w = wrap.clientWidth || 600;
      canvas.width = w;
      canvas.height = wrap.clientHeight || 96;
    }

    function paintHandles() {
      const ls = (state.pStart * 100).toFixed(3) + "%";
      const le = (state.pEnd * 100).toFixed(3) + "%";
      hStart.style.left = ls;
      hEnd.style.left = le;
      region.style.left = ls;
      region.style.width = ((state.pEnd - state.pStart) * 100).toFixed(3) + "%";
      maskL.style.left = "0";
      maskL.style.width = ls;
      maskR.style.left = le;
      maskR.style.width = (100 - state.pEnd * 100).toFixed(3) + "%";
      const a = state.pStart <= 0.0005 ? "00:00:00" : fmtClock(state.pStart * state.dur);
      const b = state.pEnd >= 0.9995 ? fmtClock(state.dur) : fmtClock(state.pEnd * state.dur);
      readout.textContent = L.region + ": " + a + " – " + b;
    }

    function applyFields(dispatch) {
      setField(startId, state.pStart <= 0.0005 ? "" : fmtClock(state.pStart * state.dur), dispatch);
      setField(stopId, state.pEnd >= 0.9995 ? "" : fmtClock(state.pEnd * state.dur), dispatch);
    }

    // --- dragging --------------------------------------------------------
    function fracFromEvent(ev) {
      const r = wrap.getBoundingClientRect();
      return Math.min(1, Math.max(0, (ev.clientX - r.left) / r.width));
    }
    let dragging = null;
    function onDown(which, ev) {
      if (!state.ready) return;
      dragging = which;
      try { ev.target.setPointerCapture(ev.pointerId); } catch (e) {}
      ev.preventDefault();
    }
    function onMove(ev) {
      if (!dragging) return;
      const f = fracFromEvent(ev);
      const gap = 0.005;
      if (dragging === "start") state.pStart = Math.min(f, state.pEnd - gap);
      else state.pEnd = Math.max(f, state.pStart + gap);
      state.pStart = Math.max(0, state.pStart);
      state.pEnd = Math.min(1, state.pEnd);
      paintHandles();
      applyFields(false);
    }
    function onUp() {
      if (!dragging) return;
      dragging = null;
      applyFields(true);
    }
    hStart.addEventListener("pointerdown", (e) => onDown("start", e));
    hEnd.addEventListener("pointerdown", (e) => onDown("end", e));
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);

    // --- playback (selected region only) --------------------------------
    function stopRaf() { if (state.raf) { cancelAnimationFrame(state.raf); state.raf = 0; } }
    function tick() {
      if (!document.body.contains(wrap)) { stopRaf(); audio.pause(); return; }
      const end = state.pEnd * state.dur;
      if (audio.currentTime >= end) audio.pause();
      if (audio.paused) {
        playBtn.textContent = "▶ " + L.play;
        cursor.style.display = "none";
        stopRaf();
        return;
      }
      cursor.style.display = "block";
      cursor.style.left = (Math.min(1, audio.currentTime / state.dur) * 100).toFixed(3) + "%";
      state.raf = requestAnimationFrame(tick);
    }
    playBtn.addEventListener("click", () => {
      if (!state.ready) return;
      if (audio.paused) {
        const start = state.pStart * state.dur, end = state.pEnd * state.dur;
        if (audio.currentTime < start || audio.currentTime >= end) audio.currentTime = start;
        audio.play().then(() => {
          playBtn.textContent = "⏸ " + L.pause;
          stopRaf();
          state.raf = requestAnimationFrame(tick);
        }).catch(() => {});
      } else {
        audio.pause();
        playBtn.textContent = "▶ " + L.play;
      }
    });
    resetBtn.addEventListener("click", () => {
      state.pStart = 0; state.pEnd = 1;
      paintHandles(); applyFields(true);
      audio.pause(); cursor.style.display = "none"; playBtn.textContent = "▶ " + L.play; stopRaf();
    });

    if (window.ResizeObserver) {
      const ro = new ResizeObserver(() => {
        if (state.ready && state.buffer) { layout(); drawWave(canvas, state.buffer); paintHandles(); }
      });
      ro.observe(wrap);
    }

    // --- decode + draw ---------------------------------------------------
    fetch(url)
      .then((r) => r.arrayBuffer())
      .then((buf) => {
        const AC = window.AudioContext || window.webkitAudioContext;
        const ctx = new AC();
        return ctx.decodeAudioData(buf).finally(() => { try { ctx.close(); } catch (e) {} });
      })
      .then((buffer) => {
        state.buffer = buffer;
        state.dur = buffer.duration || 0;
        state.ready = true;
        layout();
        drawWave(canvas, buffer);
        paintHandles();
        status.textContent = "";
      })
      .catch(() => {
        wrap.style.display = "none";
        playBtn.style.display = "none";
        resetBtn.style.display = "none";
        readout.textContent = "";
        status.textContent = L.failed;
      });
  }

  function initAll() {
    injectStyle();
    document.querySelectorAll(".ttai-trim[data-audio-url]").forEach((el) => {
      if (el.dataset.initedUrl === el.dataset.audioUrl) return;
      el.dataset.initedUrl = el.dataset.audioUrl;
      try { ttaiInitTrim(el); } catch (e) { /* leave the manual time fields usable */ }
    });
  }

  // The script is inlined in <head>, so document.body may not exist yet when
  // this runs. Attach the observer once the DOM is ready (or immediately if it
  // already is) — otherwise Shiny's dynamically-rendered .ttai-trim container
  // would never be picked up.
  function startObserver() {
    const target = document.body || document.documentElement;
    new MutationObserver(initAll).observe(target, { childList: true, subtree: true });
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { startObserver(); initAll(); });
  } else {
    startObserver();
    initAll();
  }
})();
