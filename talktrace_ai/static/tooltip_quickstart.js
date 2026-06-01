(function () {
  // Stationary tooltip: appears only after 2s of mouse staying still on the element.
  var DELAY_MS = 2000;
  var activeTip = null;
  var activeTimer = null;

  function clearActive() {
    if (activeTimer) { clearTimeout(activeTimer); activeTimer = null; }
    if (activeTip) { activeTip.remove(); activeTip = null; }
  }

  function scheduleTip(el, e) {
    clearActive();
    var text = el.getAttribute('data-tt-help');
    if (!text) return;
    var pageX = e.pageX, pageY = e.pageY;
    activeTimer = setTimeout(function () {
      var tip = document.createElement('div');
      tip.className = 'tt-stationary-tooltip';
      tip.textContent = text;
      tip.style.left = (pageX + 14) + 'px';
      tip.style.top = (pageY + 14) + 'px';
      document.body.appendChild(tip);
      activeTip = tip;
    }, DELAY_MS);
  }

  document.addEventListener('mousemove', function (e) {
    var el = e.target.closest && e.target.closest('[data-tt-help]');
    if (!el) { clearActive(); return; }
    scheduleTip(el, e);
  }, true);
  document.addEventListener('mouseleave', clearActive, true);
  window.addEventListener('blur', clearActive);
})();

(function () {
  // Quick-start floating panel: clickable header toggles open/close.
  // Event delegation on document.documentElement in CAPTURE phase
  // so that stopPropagation() in Shiny/Bootstrap handlers cannot block it.
  document.documentElement.addEventListener('click', function (e) {
    var header = e.target.closest && e.target.closest('.qs-header');
    if (!header) return;
    var qs = header.closest && header.closest('#tt-quickstart');
    if (qs) qs.classList.toggle('qs-open');
  }, true);
})();

(function () {
  // Spin the globe icon once when the language toggle is clicked.
  document.addEventListener('click', function (e) {
    var btn = e.target.closest && e.target.closest('#language_toggle');
    if (!btn) return;
    btn.classList.remove('is-spinning');
    // force reflow so the animation restarts on rapid repeated clicks
    void btn.offsetWidth;
    btn.classList.add('is-spinning');
  }, true);
})();
