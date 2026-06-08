(function () {
  function escapeHtml(unsafe) {
    return (unsafe || "")
      .toString()
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function sanitizeHtml(dirty) {
    if (typeof dirty !== "string") return "";
    if (typeof window.DOMPurify?.sanitize === "function") {
      return window.DOMPurify.sanitize(dirty);
    }
    return dirty;
  }

  function renderMarkdown(markdownText) {
    if (typeof markdownText !== "string") return "";
    if (typeof window.marked?.parse === "function") {
      const raw = window.marked.parse(markdownText);
      return sanitizeHtml(raw);
    }
    return sanitizeHtml(markdownText);
  }

  window.MythosDom = window.MythosDom || {};
  window.MythosDom.escapeHtml = escapeHtml;
  window.MythosDom.sanitizeHtml = sanitizeHtml;
  window.MythosDom.renderMarkdown = renderMarkdown;
})();

