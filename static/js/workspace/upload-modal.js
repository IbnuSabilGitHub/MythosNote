(function () {
  window.WorkspaceUploadModal = window.WorkspaceUploadModal || {};

  window.WorkspaceUploadModal.init = (workspaceId) => {
    // ── Upload modal ─────────────────────────────────────────────────────
    const modal = document.getElementById("upload-modal");
    const backdrop = document.getElementById("upload-modal-backdrop");
    const form = document.getElementById("upload-source-form");
    const fileInput = document.getElementById("source-file-input");
    const previewContainer = document.getElementById("upload-file-preview-container");
    const template = document.getElementById("upload-file-item-template");
    const errorEl = document.getElementById("upload-error");
    const submitBtn = document.getElementById("btn-submit-upload");
    const openBtn = document.getElementById("btn-add-source");
    const openBtnRail = document.getElementById("btn-add-source-rail");
    const closeBtn = document.getElementById("btn-close-upload-modal");
    const cancelBtn = document.getElementById("btn-cancel-upload");
    const progressWrap = document.getElementById("upload-progress-wrap");
    const progressBar = document.getElementById("upload-progress-bar");
    const progressPct = document.getElementById("upload-progress-pct");

    if (!modal || !form || !fileInput) return;

    let selectedFiles = [];

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
      selectedFiles = [];
      renderPreview();
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

    function renderPreview() {
      if (!previewContainer || !template) return;
      previewContainer.innerHTML = "";
      
      if (selectedFiles.length === 0) {
        previewContainer.classList.add("hidden");
        previewContainer.classList.remove("flex");
        submitBtn.disabled = true;
        fileInput.value = "";
        return;
      }

      previewContainer.classList.remove("hidden");
      previewContainer.classList.add("flex");
      submitBtn.disabled = false;

      selectedFiles.forEach((file, index) => {
        const ext = "." + file.name.split(".").pop().toLowerCase();
        const clone = template.content.cloneNode(true);
        
        clone.querySelector(".file-icon").setAttribute("icon", getFileIcon(ext.slice(1)));
        clone.querySelector(".file-name").textContent = file.name;
        clone.querySelector(".file-size").textContent = formatBytes(file.size);
        
        clone.querySelector(".btn-remove-file").addEventListener("click", () => {
          selectedFiles.splice(index, 1);
          renderPreview();
        });
        
        previewContainer.appendChild(clone);
      });
      
      // Update fileInput to match selectedFiles for consistency
      const dt = new DataTransfer();
      selectedFiles.forEach(f => dt.items.add(f));
      fileInput.files = dt.files;
    }

    function handleFiles(files) {
      if (!files || files.length === 0) return;
      clearError();

      const newFiles = Array.from(files);
      if (selectedFiles.length + newFiles.length > 5) {
        showError("Maksimal 5 file dapat diupload sekaligus.");
        return;
      }

      for (let i = 0; i < newFiles.length; i++) {
        const file = newFiles[i];
        const ext = "." + file.name.split(".").pop().toLowerCase();
        if (!ALLOWED_EXT.includes(ext)) {
          showError(`Format file ${file.name} tidak didukung.`);
          return;
        }
        if (file.size > MAX_BYTES) {
          showError(`File ${file.name} terlalu besar. Maksimal 20 MB per file.`);
          return;
        }
      }

      // Avoid duplicates
      newFiles.forEach(nf => {
        const exists = selectedFiles.some(sf => sf.name === nf.name && sf.size === nf.size);
        if (!exists) {
          selectedFiles.push(nf);
        }
      });
      
      renderPreview();
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
    function xhrUpload(formData, index = 0, totalFiles = 1) {
      return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open("POST", "/api/sources/upload/");
        xhr.setRequestHeader("X-CSRFToken", getCSRFToken());

        xhr.upload.addEventListener("progress", (e) => {
          if (e.lengthComputable) {
            const filePct = e.loaded / e.total;
            const overallPct = ((index + filePct) / totalFiles) * 100;
            showProgress(overallPct);
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
      if (modal?.classList.contains("hidden")) return;
      
      if (e.key === "Escape") {
        closeModal();
        return;
      }
      
      if (e.key === "Tab") {
        const focusableElements = modal.querySelectorAll(
          'a[href], button, textarea, input[type="text"], input[type="radio"], input[type="checkbox"], select, [tabindex]:not([tabindex="-1"])'
        );
        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];

        if (e.shiftKey) {
          if (document.activeElement === firstElement) {
            lastElement.focus();
            e.preventDefault();
          }
        } else {
          if (document.activeElement === lastElement) {
            firstElement.focus();
            e.preventDefault();
          }
        }
      }
    });

    fileInput?.addEventListener("change", () => handleFiles(fileInput.files));

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

        const files = e.dataTransfer?.files;
        if (files && files.length > 0) {
          handleFiles(files);
        }
      });
    }

    // ── Form submit ─────────────────────────────────────────────────────
    form?.addEventListener("submit", async (e) => {
      e.preventDefault();

      const files = selectedFiles;
      if (!files || files.length === 0 || !workspaceId || !window.workspaceSources) return;

      submitBtn.disabled = true;
      submitBtn.textContent = "Mengupload...";
      clearError();
      showProgress(0);

      try {
        const results = [];
        for (let i = 0; i < files.length; i++) {
          const file = files[i];
          const formData = new FormData();
          formData.append("file", file);
          formData.append("workspace_id", workspaceId);
          
          const data = await xhrUpload(formData, i, files.length);
          results.push(data);
        }

        // Refresh list
        await window.workspaceSources.fetchSources();

        // Start polling for newly uploaded source
        results.forEach(data => {
          if (data?.id) {
            window.workspaceSources.pollSourceStatus(data.id);
          }
        });

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

