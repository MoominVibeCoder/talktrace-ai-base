(function () {
  var DARK_BG = '#161B19';
  var DARK_FG = '#D5DDD8';
  var LIGHT_BG = '#f8f8f800';

  // --- Rewrite bslib's style.css rule in place -------------------------
  // The inline-!important strategy below should win the cascade, but some
  // browsers still display the style.css source rule in DevTools. Walking
  // the CSSOM and patching the --bslib-sidebar-main-bg value directly
  // makes the change visible at the source as well.
  function patchBslibStylesheet() {
    for (var i = 0; i < document.styleSheets.length; i++) {
      var sheet = document.styleSheets[i];
      var rules;
      try { rules = sheet.cssRules || sheet.rules; } catch (e) { continue; }
      if (!rules) continue;
      for (var j = 0; j < rules.length; j++) {
        var rule = rules[j];
        if (!rule || !rule.style) continue;
        try {
          if (rule.style.getPropertyValue('--bslib-sidebar-main-bg')) {
            rule.style.setProperty('--bslib-sidebar-main-bg', LIGHT_BG, 'important');
          }
        } catch (e) { /* cross-origin or read-only */ }
      }
    }
  }
  patchBslibStylesheet();
  [50, 200, 600, 1500, 3000].forEach(function (ms) { setTimeout(patchBslibStylesheet, ms); });

  // --- Append an override <style> at the end of <head> so it wins source
  // order against bslib's bundled stylesheet.
  var override = document.createElement('style');
  override.setAttribute('data-tt-override', 'bslib-sidebar-main-bg');
  override.textContent =
    ':root, .bslib-sidebar-layout, html .bslib-sidebar-layout, html body .bslib-sidebar-layout {' +
    '  --bslib-sidebar-main-bg: ' + LIGHT_BG + ' !important;' +
    '}';
  (document.head || document.documentElement).appendChild(override);

  var SELECTORS = [
    'html',
    'body',
    'main.bslib-page-main',
    'div.main',
    '.bslib-sidebar-layout',
    '.bslib-sidebar-layout > .main',
    '.bslib-page-fill',
    '.bslib-page-sidebar',
    '.tab-content'
  ];

  function applyTheme() {
    var isDark = document.documentElement.getAttribute('data-bs-theme') === 'dark';
    SELECTORS.forEach(function (sel) {
      try {
        document.querySelectorAll(sel).forEach(function (el) {
          el.style.setProperty('background-color', isDark ? DARK_BG : '', 'important');
          el.style.setProperty('color', isDark ? DARK_FG : '', 'important');
        });
      } catch (e) { /* ignore bad selectors */ }
    });
    // Tab panes are coloured via theme-scoped CSS rules (see theme.css),
    // not inline styles — clear any stale inline bg left by older builds so
    // a dark->light toggle never leaks dark blocks into the light layout.
    document.querySelectorAll('.tab-pane').forEach(function (el) {
      el.style.removeProperty('background-color');
      el.style.removeProperty('color');
    });
    // bslib reads --_main-bg / --bslib-sidebar-main-bg off .bslib-sidebar-layout
    // to colour the .main container. Force them inline so nothing can override.
    // In light mode, use #f8f8f800 (fully transparent) instead of clearing --
    // clearing falls back to bslib's style.css default of #f8f8f8 (opaque).
    var LIGHT_TRANSPARENT = '#f8f8f800';
    document.querySelectorAll('.bslib-sidebar-layout').forEach(function (el) {
      el.style.setProperty('--_main-bg', isDark ? DARK_BG : LIGHT_TRANSPARENT, 'important');
      el.style.setProperty('--bslib-sidebar-main-bg', isDark ? DARK_BG : LIGHT_TRANSPARENT, 'important');
      el.style.setProperty('--_main-fg', isDark ? DARK_FG : '', 'important');
    });
  }

  new MutationObserver(applyTheme).observe(
    document.documentElement,
    { attributes: true, attributeFilter: ['data-bs-theme'] }
  );
  // Run immediately, plus on DOM ready, plus on a few post-load ticks to
  // catch async-injected bslib containers.
  applyTheme();
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', applyTheme);
  }
  window.addEventListener('load', applyTheme);
  [50, 200, 600, 1500, 3000].forEach(function (ms) { setTimeout(applyTheme, ms); });
})();
