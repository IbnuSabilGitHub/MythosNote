document.addEventListener("DOMContentLoaded", () => {
  // ── WorkspaceSources init ──────────────────────────────────────────────────
  const wsData = document.getElementById("workspace-data");
  const workspaceId =
    wsData?.dataset.workspaceId ||
    new URLSearchParams(window.location.search).get("workspace_id");

  if (workspaceId && window.WorkspaceSources) {
    window.workspaceSources = new window.WorkspaceSources(workspaceId);
    window.workspaceSources.fetchSources();
  }

  // ── Panel helpers ──────────────────────────────────────────────────────────
  if (window.WorkspaceLayout) {
    window.WorkspaceLayout.init();
  }

  if (window.WorkspaceSelection) {
    window.WorkspaceSelection.init();
  }

  // ── Upload modal ───────────────────────────────────────────────────────────
  const modal       = document.getElementById("upload-modal");
  const backdrop    = document.getElementById("upload-modal-backdrop");
  const form        = document.getElementById("upload-source-form");
  const fileInput   = document.getElementById("source-file-input");
  const preview     = document.getElementById("upload-file-preview");
  const fileIcon    = document.getElementById("upload-file-icon");
  const fileName    = document.getElementById("upload-file-name");
  const fileSize    = document.getElementById("upload-file-size");
  const errorEl     = document.getElementById("upload-error");
  const submitBtn   = document.getElementById("btn-submit-upload");
  const openBtn     = document.getElementById("btn-add-source");
  const closeBtn    = document.getElementById("btn-close-upload-modal");
  const cancelBtn   = document.getElementById("btn-cancel-upload");
  const clearBtn    = document.getElementById("btn-clear-file");

  const MAX_BYTES   = 20 * 1024 * 1024; // 20 MB
  const ALLOWED_EXT = [".pdf", ".txt", ".md"];

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
  }

  function showError(msg) {
    errorEl.textContent = msg;
    errorEl.classList.remove("hidden");
    submitBtn.disabled = true;
  }

  function clearError() {
    errorEl.classList.add("hidden");
    errorEl.textContent = "";
  }

  function getFileIcon(ext) {
    if (ext === "pdf") return "tabler:pdf";
    if (ext === "md")  return "tabler:markdown";
    return "tabler:txt";
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
      showError(`Format tidak didukung. Gunakan: ${ALLOWED_EXT.join(", ")}`);
      return;
    }
    if (file.size > MAX_BYTES) {
      showError(`Ukuran file melebihi batas 20 MB.`);
      return;
    }

    // Show preview
    fileIcon.setAttribute("icon", getFileIcon(ext.slice(1)));
    fileName.textContent = file.name;
    fileSize.textContent = formatBytes(file.size);
    preview.classList.remove("hidden");
    preview.classList.add("flex");
    submitBtn.disabled = false;
  }

  // Open / close wiring
  openBtn?.addEventListener("click", openModal);
  closeBtn?.addEventListener("click", closeModal);
  cancelBtn?.addEventListener("click", closeModal);
  backdrop?.addEventListener("click", closeModal);

  // Escape key
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !modal.classList.contains("hidden")) closeModal();
  });

  // File input change
  fileInput?.addEventListener("change", () => {
    handleFile(fileInput.files[0]);
  });

  // Clear file button
  clearBtn?.addEventListener("click", () => {
    fileInput.value = "";
    preview.classList.add("hidden");
    preview.classList.remove("flex");
    submitBtn.disabled = true;
    clearError();
  });

  // Form submit
  form?.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!fileInput.files[0] || !workspaceId || !window.workspaceSources) return;

    submitBtn.disabled = true;
    submitBtn.textContent = "Mengupload...";
    clearError();

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);
    formData.append("workspace_id", workspaceId);

    try {
      await window.workspaceSources.uploadSource(formData);
      closeModal();

      if (window.showToast) window.showToast("Sumber berhasil diupload.", "success");
      else if (window.ToastManager?.success) window.ToastManager.success("Sumber berhasil diupload.");
    } catch (err) {
      showError("Upload gagal. Periksa koneksi dan coba lagi.");
      submitBtn.disabled = false;
      submitBtn.textContent = "Upload";
    }
  });
});
