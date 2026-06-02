(function () {
  window.WorkspaceUploadModal = window.WorkspaceUploadModal || {};

  window.WorkspaceUploadModal.init = (workspaceId) => {
    // ── Upload modal ─────────────────────────────────────────────────────
    const modal = document.getElementById("upload-modal");
    const backdrop = document.getElementById("upload-modal-backdrop");
    const form = document.getElementById("upload-source-form");
    const fileInput = document.getElementById("source-file-input");
    const preview = document.getElementById("upload-file-preview");
    const fileIconEl = document.getElementById("upload-file-icon");
    const fileNameEl = document.getElementById("upload-file-name");
    const fileSizeEl = document.getElementById("upload-file-size");
    const errorEl = document.getElementById("upload-error");
    const submitBtn = document.getElementById("btn-submit-upload");
    const openBtn = document.getElementById("btn-add-source");
    const openBtnRail = document.getElementById("btn-add-source-rail");
    const closeBtn = document.getElementById("btn-close-upload-modal");
    const cancelBtn = document.getElementById("btn-cancel-upload");
    const clearBtn = document.getElementById("btn-clear-file");
    const progressWrap = document.getElementById("upload-progress-wrap");
    const progressBar = document.getElementById("upload-progress-bar");
    const progressPct = document.getElementById("upload-progress-pct");

    if (!modal || !form || !fileInput) return;

    const MAX_BYTES = 20 * 1024 * 1024; // 20 MB
    const ALLOWED_EXT = [".pdf", ".txt", ".md", ".docx"];

    // ── CSRF helper ──────────────────────────────────────────────────────
    function getCSRFToken() {
      return (
        window.MythosCsrf?.getCsrfToken?.() ||
        document.cookie.match(/csrftoken=([^;]+)/)?.[1] ||
        ""
      );
    }

    // ── Modal open / close ───────────────────────────────────────────────
    function openModal() {
      modal.classList.remove("hidden");
      modal.classList.add("flex");
      document.body.style.overflow = "hidden";
    }

    function closeModal() {
      modal.classList.add("hidden");
      modal.classList.remove("flex");
      document.body.style.overflow = "";
      resetForm();
    }

    function resetForm() {
      form.reset();
      preview.classList.add("hidden");
      preview.classList.remove("flex");
      errorEl.classList.add("hidden");
      errorEl.textContent = "";
      submitBtn.disabled = true;
      submitBtn.textContent = "Upload";
      hideProgress();
    }

    // ── Error helpers ─────────────────────────────────────────────────────
    function showError(msg) {
      errorEl.textContent = msg;
      errorEl.classList.remove("hidden");
      submitBtn.disabled = true;
    }

    function clearError() {
      errorEl.classList.add("hidden");
      errorEl.textContent = "";
    }

    // ── Progress bar ─────────────────────────────────────────────────────
    function showProgress(pct) {
      if (!progressWrap || !progressBar) return;
      progressWrap.classList.remove("hidden");
      progressBar.style.width = `${pct}%`;
      if (progressPct) progressPct.textContent = `${Math.round(pct)}%`;
    }

    function hideProgress() {
      if (!progressWrap) return;
      progressWrap.classList.add("hidden");
      if (progressBar) progressBar.style.width = "0%";
      if (progressPct) progressPct.textContent = "0%";
    }

    // ── File helpers ─────────────────────────────────────────────────────
    function getFileIcon(ext) {
      const map = {
        pdf: "tabler:pdf",
        md: "tabler:markdown",
        docx: "tabler:file-type-docx",
      };
      return map[ext] || "tabler:txt";
    }

    function formatBytes(bytes) {
      const kb = bytes / 1024;
      return kb < 1024 ? `${kb.toFixed(0)} KB` : `${(kb / 1024).toFixed(1)} MB`;
    }

    function handleFile(file) {
      if (!file) return;
      clearError();

      const ext = "." + file.name.split(".").pop().toLowerCase();
      if (!ALLOWED_EXT.includes(ext)) {
        showError("Format tidak didukung. Gunakan PDF, TXT, MD, atau DOCX.");
        return;
      }
      if (file.size > MAX_BYTES) {
        showError("File terlalu besar. Maksimal 20 MB.");
        return;
      }

      fileIconEl?.setAttribute("icon", getFileIcon(ext.slice(1)));
      if (fileNameEl) fileNameEl.textContent = file.name;
      if (fileSizeEl) fileSizeEl.textContent = formatBytes(file.size);
      preview.classList.remove("hidden");
      preview.classList.add("flex");
      submitBtn.disabled = false;
    }

    // ── Map API error keys to user-friendly messages ───────────────────
    function resolveApiError(data) {
      if (!data) return "Upload gagal. Coba lagi.";
      const msg = data.file || data.detail || Object.values(data)[0];
      if (!msg) return "Upload gagal. Coba lagi.";

      // Already Indonesian from server — pass through
      const known = ["File terlalu besar", "Format tidak didukung", "File dengan nama ini"];
      if (known.some((k) => String(msg).includes(k))) return String(msg);

      return String(msg);
    }

    // ── XHR upload with progress ─────────────────────────────────────────
    function xhrUpload(formData) {
      return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open("POST", "/api/sources/upload/");
        xhr.setRequestHeader("X-CSRFToken", getCSRFToken());

        xhr.upload.addEventListener("progress", (e) => {
          if (e.lengthComputable) {
            showProgress((e.loaded / e.total) * 100);
          }
        });

        xhr.addEventListener("load", () => {
          let data;
          try {
            data = JSON.parse(xhr.responseText);
          } catch {
            data = null;
          }

          if (xhr.status === 201) {
            resolve(data);
          } else {
            reject({ status: xhr.status, data });
          }
        });

        xhr.addEventListener("error", () => reject({ status: 0, data: null }));
        xhr.addEventListener("abort", () => reject({ status: 0, data: null }));

        xhr.send(formData);
      });
    }

    // ── Event wiring ─────────────────────────────────────────────────────
    openBtn?.addEventListener("click", openModal);
    openBtnRail?.addEventListener("click", openModal);
    closeBtn?.addEventListener("click", closeModal);
    cancelBtn?.addEventListener("click", closeModal);
    backdrop?.addEventListener("click", closeModal);

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && !modal?.classList.contains("hidden")) closeModal();
    });

    fileInput?.addEventListener("change", () => handleFile(fileInput.files[0]));

    clearBtn?.addEventListener("click", () => {
      fileInput.value = "";
      preview.classList.add("hidden");
      preview.classList.remove("flex");
      submitBtn.disabled = true;
      clearError();
    });

    // Drag-and-drop on the label
    const dropLabel = form?.querySelector("label[for='source-file-input']");
    if (dropLabel) {
      dropLabel.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropLabel.classList.add("is-dragging");
      });
      dropLabel.addEventListener("dragleave", () => {
        dropLabel.classList.remove("is-dragging");
      });
      dropLabel.addEventListener("drop", (e) => {
        e.preventDefault();
        dropLabel.classList.remove("is-dragging");

        const file = e.dataTransfer?.files?.[0];
        if (file) {
          // Assign to input so form data works
          const dt = new DataTransfer();
          dt.items.add(file);
          fileInput.files = dt.files;
          handleFile(file);
        }
      });
    }

    // ── Form submit ─────────────────────────────────────────────────────
    form?.addEventListener("submit", async (e) => {
      e.preventDefault();

      const file = fileInput?.files?.[0];
      if (!file || !workspaceId || !window.workspaceSources) return;

      submitBtn.disabled = true;
      submitBtn.textContent = "Mengupload...";
      clearError();
      showProgress(0);

      const formData = new FormData();
      formData.append("file", file);
      formData.append("workspace_id", workspaceId);

      try {
        const data = await xhrUpload(formData);

        // Refresh list
        await window.workspaceSources.fetchSources();

        // Start polling for newly uploaded source
        if (data?.id) {
          window.workspaceSources.pollSourceStatus(data.id);
        }

        closeModal();

        if (window.showToast) window.showToast("Sumber berhasil diupload.", "success");
        else if (window.ToastManager?.success)
          window.ToastManager.success("Sumber berhasil diupload.");
      } catch (err) {
        hideProgress();
        const msg = resolveApiError(err?.data);
        showError(msg);
        submitBtn.disabled = false;
        submitBtn.textContent = "Upload";
      }
    });
  };
})();

