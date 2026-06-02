export function getStatusClass(status) {
  const classMap = {
    pending: "status-pending bg-yellow-500/20 text-yellow-300",
    queued: "status-pending bg-yellow-500/20 text-yellow-300",
    processing: "status-processing bg-primary/10 text-primary",
    ready: "status-ready bg-green-500/20 text-green-300",
    failed: "status-failed bg-red-500/20 text-red-300",
  };
  return classMap[status] || "bg-neutral-700/50 text-stone-300";
}

export function getStatusLabel(status) {
  const labelMap = {
    pending: "Menunggu",
    queued: "Menunggu",
    processing: "Memproses",
    ready: "Siap",
    failed: "Gagal",
  };
  return labelMap[status] || "Unknown";
}

export function escapeHTML(text) {
  const shared = window.MythosDom?.escapeHtml;
  if (typeof shared === "function") return shared(text);

  // Fallback escape (untuk case ketika core/dom belum diload).
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

export function createSourceItemHTML(source) {
  const statusClass = this.getStatusClass(source.status);
  const statusLabel = this.getStatusLabel(source.status);
  const fileName = source.original_filename || source.file_name || source.name || "Unknown";

  const ext = fileName.split(".").pop().toLowerCase();
  const fileIconMap = {
    pdf: "tabler:pdf",
    md: "tabler:markdown",
    docx: "tabler:file-type-docx",
  };
  const fileIcon = fileIconMap[ext] || "tabler:txt";

  const isReady = source.status === "ready";

  const checkboxClasses = isReady
    ? "h-4 w-4 rounded-xs border border-primary bg-primary accent-primary focus:outline-none focus:ring-2 focus:ring-primary/40"
    : "h-4 w-4 rounded-xs border border-neutral-700 bg-neutral-950 accent-primary opacity-40 cursor-not-allowed";

  const nameClasses = isReady
    ? "text-zinc-200 text-sm font-medium"
    : "text-stone-300 text-sm font-normal";

  // Format file size
  let sizeLabel = "";
  if (source.file_size) {
    const kb = source.file_size / 1024;
    sizeLabel =
      kb < 1024 ? `${kb.toFixed(0)} KB` : `${(kb / 1024).toFixed(1)} MB`;
  }

  // Format created_at
  let timeLabel = "";
  if (source.created_at) {
    const diff = Date.now() - new Date(source.created_at).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 60) timeLabel = `${mins || 1} menit lalu`;
    else if (mins < 1440) timeLabel = `${Math.floor(mins / 60)} jam lalu`;
    else timeLabel = `${Math.floor(mins / 1440)} hari lalu`;
  }

  const typeLabel = ext.toUpperCase();
  const meta = [typeLabel, sizeLabel, timeLabel].filter(Boolean).join(" \u2022 ");

  const isProcessing =
    source.status === "processing" ||
    source.status === "pending" ||
    source.status === "queued";
  const isFailed = source.status === "failed";

  const errorTitle =
    isFailed && source.error_message
      ? ` title="${this.escapeHTML(source.error_message.slice(0, 120))}"`
      : "";

  const badgeAnimClass = isProcessing ? " animate-pulse" : "";

  let progressHTML = "";
  if (isProcessing) {
    const prg = source.progress || 0;
    progressHTML = `
      <div class="progress-bar-wrap w-full bg-neutral-800 rounded-full h-1.5 mt-1.5 overflow-hidden">
        <div class="progress-bar-inner bg-primary h-1.5 rounded-full transition-all duration-300" style="width: ${prg}%"></div>
      </div>
    `;
  }

  let errorHTML = "";
  if (isFailed && source.error_message) {
    errorHTML = `
      <div class="error-reason-wrap self-stretch mt-1.5 text-red-400 text-xs font-normal font-['Manrope'] leading-5 truncate hover:text-red-300 transition" title="${this.escapeHTML(source.error_message)}">
        Gagal: ${this.escapeHTML(source.error_message)}
      </div>
    `;
  }

  return `
    <div class="source-item self-stretch p-2.5 relative bg-neutral-900/45 rounded-lg border border-neutral-800 inline-flex justify-start items-start gap-2.5 ${isReady ? "cursor-pointer hover:border-primary/35 hover:bg-neutral-900/80 focus-within:border-primary/35 focus-within:bg-neutral-900/80" : "cursor-not-allowed opacity-80"} transition shadow-[0_8px_28px_rgba(0,0,0,0.10)]"
      data-source-id="${this.escapeHTML(source.id)}"
      data-source-item
      data-source-ready="${isReady ? "true" : "false"}"
      data-selected-classes="bg-neutral-900 border-primary/60 shadow-[inset_0_0_0_1px_rgba(255,200,128,0.18),0_12px_40px_rgba(0,0,0,0.18)]">
      <div class="pt-1 inline-flex flex-col justify-start items-start">
        <input type="checkbox" data-source-checkbox
          class="${checkboxClasses}" ${isReady ? "checked" : "disabled"}
          aria-label="Pilih ${this.escapeHTML(fileName)}" />
      </div>
      <div class="flex-1 inline-flex flex-col justify-start items-start gap-1 min-w-0">
        <div class="self-stretch inline-flex justify-start items-center gap-1">
          <iconify-icon icon="${fileIcon}" class="text-primary text-sm shrink-0"></iconify-icon>
          <div class="min-w-0 flex-1 overflow-hidden">
            <div class="${nameClasses} truncate font-['Manrope'] leading-6" title="${this.escapeHTML(fileName)}">
              ${this.escapeHTML(fileName)}
            </div>
          </div>
        </div>
        <div class="self-stretch flex items-center justify-between gap-2 overflow-hidden">
          <div class="text-stone-300/70 text-xs font-normal font-['Manrope'] leading-5 truncate">${this.escapeHTML(meta)}</div>
          <span class="status-badge ${statusClass}${badgeAnimClass} px-1.5 py-0.5 rounded-md text-[10px] font-semibold whitespace-nowrap shrink-0"${errorTitle}>
            ${statusLabel}
          </span>
        </div>
        ${progressHTML}
        ${errorHTML}
      </div>
      <a
        href="/api/sources/${this.escapeHTML(source.id)}/download/"
        download="${this.escapeHTML(fileName)}"
        class="shrink-0 mt-0.5 p-1 rounded hover:bg-neutral-800 text-stone-500 hover:text-primary focus:outline-none focus:ring-2 focus:ring-primary/40 transition cursor-pointer"
        title="Download sumber"
        aria-label="Download ${this.escapeHTML(fileName)}"
      >
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
      </a>
      <button
        data-delete-source="${this.escapeHTML(source.id)}"
        class="shrink-0 mt-0.5 p-1 rounded hover:bg-red-500/20 text-stone-500 hover:text-red-400 focus:outline-none focus:ring-2 focus:ring-red-500/40 transition cursor-pointer"
        title="Hapus sumber"
        aria-label="Hapus ${this.escapeHTML(fileName)}"
      >
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
        </svg>
      </button>
    </div>
  `;
}

