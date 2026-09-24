(function () {
  var KEY = 'kcLocale';
  var root = document.documentElement;
  var current = root.getAttribute('data-kc-current-locale') || '';
  var def = root.getAttribute('data-kc-default-locale') || '';

  var saved = null;
  try { saved = localStorage.getItem(KEY); } catch (e) { /* storage blocked */ }

  var target = saved || def;

  // Never reload a page inside the login flow (login-actions/*: code form, required actions,
  // errors). Those pages answer a POST and carry a one-time session code: reloading them with
  // kc_locale re-runs the step and Keycloak answers "page expired". There, after the password,
  // the language is the account's own, which is also the right one to show.
  var inFlow = window.location.pathname.indexOf('/login-actions/') !== -1;

  if (!inFlow && target && current && target !== current) {
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
