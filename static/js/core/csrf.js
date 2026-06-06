(function () {
  function getCsrfToken() {
    return document.cookie.match(/csrftoken=([^;]+)/)?.[1] || "";
  }

  window.MythosCsrf = window.MythosCsrf || {};
  window.MythosCsrf.getCsrfToken = getCsrfToken;
})();

