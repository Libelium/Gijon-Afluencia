(function () {
  var KEY = 'kcLocale';
  var root = document.documentElement;
  var current = root.getAttribute('data-kc-current-locale') || '';
  var def = root.getAttribute('data-kc-default-locale') || '';

  var saved = null;
  try { saved = localStorage.getItem(KEY); } catch (e) { /* storage blocked */ }

  var target = saved || def;

  if (target && current && target !== current) {
    try {
      var url = new URL(window.location.href);
      if (url.searchParams.get('kc_locale') !== target) {
        url.searchParams.set('kc_locale', target);
        window.location.replace(url.toString());
        return;
      }
    } catch (e) { /* URL API unavailable */ }
  }

  document.addEventListener('DOMContentLoaded', function () {
    var opts = document.querySelectorAll('[data-kc-locale-option]');
    for (var i = 0; i < opts.length; i++) {
      opts[i].addEventListener('click', function () {
        try { localStorage.setItem(KEY, this.getAttribute('data-kc-locale-option')); } catch (e) { }
      });
    }
  });
})();
