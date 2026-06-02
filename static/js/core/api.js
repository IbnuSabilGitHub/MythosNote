(function () {
  function getDefaultHeaders() {
    const csrf =
      window.MythosCsrf && typeof window.MythosCsrf.getCsrfToken === "function"
        ? window.MythosCsrf.getCsrfToken()
        : "";
    const headers = {};
    if (csrf) headers["X-CSRFToken"] = csrf;
    return headers;
  }

  async function apiFetch(url, { method = "GET", headers = {}, body = undefined } = {}) {
    const finalHeaders = { ...getDefaultHeaders(), ...headers };

    // If JSON body, attach correct content type (except for FormData).
    const isFormData = typeof FormData !== "undefined" && body instanceof FormData;
    if (!isFormData && body !== undefined && body !== null) {
      if (
        typeof body === "object" &&
        !(typeof body === "string") &&
        !finalHeaders["Content-Type"] &&
        !finalHeaders["content-type"]
      ) {
        finalHeaders["Content-Type"] = "application/json";
        body = JSON.stringify(body);
      }
    }

    const response = await fetch(url, {
      method,
      headers: finalHeaders,
      body,
    });

    let data = null;
    if (response.status !== 204) {
      try {
        data = await response.json();
      } catch {
        data = null;
      }
    }

    if (!response.ok) {
      const message = data?.detail || data?.message || `HTTP ${response.status}`;
      const err = new Error(message);
      err.status = response.status;
      err.data = data;
      throw err;
    }

    return data;
  }

  window.MythosApi = window.MythosApi || {};
  window.MythosApi.apiFetch = apiFetch;
})();

