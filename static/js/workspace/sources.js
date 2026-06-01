(function () {
  /**
   * WorkspaceSources - Handles Sources panel dynamic rendering and API interactions
   */
  class WorkspaceSources {
    constructor(workspaceId) {
      this.workspaceId = workspaceId;
      this.container = document.querySelector("#source-list-container");
      this.countEl = document.querySelector("[data-source-count]");
      this.statsEl = document.querySelector("[data-source-stats]");
      this.maxSources = 5;
      this.pollIntervals = new Map(); // Track polling timers
    }

    /**
     * Get CSRF token from cookie
     * @returns {string} CSRF token
     */
    getCSRFToken() {
      return document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '';
    }

    /**
     * Fetch sources list from API
     * @param {string|null} workspaceId - Optional workspace ID override
     */
    async fetchSources(workspaceId = null) {
      try {
        const id = workspaceId || this.workspaceId;
        this.showLoadingState();

        const response = await fetch(
          `/api/sources/?workspace_id=${id}`
        );

        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();
        this.renderSourceList(data.results || data);
      } catch (error) {
        console.error("Failed to fetch sources:", error);
        this.showErrorState(
          "Failed to load sources. Please refresh the page."
        );
      }
    }

    /**
     * Render sources list with status badges and delete buttons
     * @param {Array} sources - Sources data from API
     */
    renderSourceList(sources) {
      if (!this.container) {
        console.warn("Source list container not found");
        return;
      }

      this.updatePanelSummary(sources || []);

      // Handle empty state
      if (!sources || sources.length === 0) {
        this.container.innerHTML = `
          <div class="flex min-h-56 w-full flex-col items-center justify-center rounded-xl border border-dashed border-neutral-800 bg-neutral-900/30 px-4 py-8 text-center">
            <div class="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <iconify-icon icon="tabler:file-upload" class="text-xl"></iconify-icon>
            </div>
            <div class="text-stone-300 text-sm font-medium font-['Manrope']">Belum ada sumber</div>
            <div class="text-stone-500 text-xs mt-1 font-['Manrope']">Upload 1-5 file utama untuk mulai chat.</div>
          </div>
        `;
        return;
      }

      // Clear container
      this.container.innerHTML = "";

      // Create list items
      const listHTML = sources
        .map((source) => this.createSourceItemHTML(source))
        .join("");

      this.container.innerHTML = listHTML;

      // Attach event listeners to delete buttons
      this.container
        .querySelectorAll("[data-delete-source]")
        .forEach((btn) => {
          btn.addEventListener("click", (e) => {
            e.stopPropagation();
            const sourceId = btn.dataset.deleteSource;
            const fileName = btn.getAttribute("aria-label")?.replace("Hapus ", "") || "sumber";
            if (confirm(`Apakah Anda yakin ingin menghapus sumber "${fileName}"?`)) {
              this.deleteSource(sourceId);
            }
          });
        });
    }

    /**
     * Update compact panel metadata for source limits and status counts.
     * @param {Array} sources - Sources data from API
     */
    updatePanelSummary(sources) {
      const total = sources.length;
      const ready = sources.filter((source) => source.status === "ready").length;
      const processing = sources.filter((source) =>
        ["pending", "queued", "processing"].includes(source.status)
      ).length;
      const failed = sources.filter((source) => source.status === "failed").length;

      if (this.countEl) {
        this.countEl.textContent = `${total}/${this.maxSources} sumber`;
      }

      if (this.statsEl) {
        const parts = [`${ready} siap`, `${processing} proses`];
        if (failed > 0) parts.push(`${failed} gagal`);
        this.statsEl.textContent = parts.join(" • ");
      }
    }

    /**
     * Create HTML for a single source item
     * @param {Object} source - Source object
     * @returns {string} HTML string
     */
    createSourceItemHTML(source) {
      const statusClass = this.getStatusClass(source.status);
      const statusLabel = this.getStatusLabel(source.status);
      const fileName = source.original_filename || source.file_name || source.name || 'Unknown';
      const ext = fileName.split('.').pop().toLowerCase();
      const fileIconMap = { pdf: 'tabler:pdf', md: 'tabler:markdown', docx: 'tabler:file-type-docx' };
      const fileIcon = fileIconMap[ext] || 'tabler:txt';
      const isReady = source.status === 'ready';
      const checkboxClasses = isReady
        ? 'h-4 w-4 rounded-xs border border-primary bg-primary accent-primary focus:outline-none focus:ring-2 focus:ring-primary/40'
        : 'h-4 w-4 rounded-xs border border-neutral-700 bg-neutral-950 accent-primary opacity-40 cursor-not-allowed';
      const nameClasses = isReady
        ? 'text-zinc-200 text-sm font-medium'
        : 'text-stone-300 text-sm font-normal';

      // Format file size
      let sizeLabel = '';
      if (source.file_size) {
        const kb = source.file_size / 1024;
        sizeLabel = kb < 1024
          ? `${kb.toFixed(0)} KB`
          : `${(kb / 1024).toFixed(1)} MB`;
      }

      // Format created_at
      let timeLabel = '';
      if (source.created_at) {
        const diff = Date.now() - new Date(source.created_at).getTime();
        const mins = Math.floor(diff / 60000);
        if (mins < 60) timeLabel = `${mins || 1} menit lalu`;
        else if (mins < 1440) timeLabel = `${Math.floor(mins / 60)} jam lalu`;
        else timeLabel = `${Math.floor(mins / 1440)} hari lalu`;
      }

      const typeLabel = ext.toUpperCase();
      const meta = [typeLabel, sizeLabel, timeLabel].filter(Boolean).join(' \u2022 ');
      const isProcessing = source.status === 'processing' || source.status === 'pending' || source.status === 'queued';
      const isFailed = source.status === 'failed';
      const errorTitle = isFailed && source.error_message
        ? ` title="${this.escapeHTML(source.error_message.slice(0, 120))}"`
        : '';
      const badgeAnimClass = isProcessing ? ' animate-pulse' : '';

      let progressHTML = '';
      if (isProcessing) {
        const prg = source.progress || 0;
        progressHTML = `
          <div class="progress-bar-wrap w-full bg-neutral-800 rounded-full h-1.5 mt-1.5 overflow-hidden">
            <div class="progress-bar-inner bg-primary h-1.5 rounded-full transition-all duration-300" style="width: ${prg}%"></div>
          </div>
        `;
      }

      let errorHTML = '';
      if (isFailed && source.error_message) {
        errorHTML = `
          <div class="error-reason-wrap self-stretch mt-1.5 text-red-400 text-xs font-normal font-['Manrope'] leading-5 truncate hover:text-red-300 transition" title="${this.escapeHTML(source.error_message)}">
            Gagal: ${this.escapeHTML(source.error_message)}
          </div>
        `;
      }

      return `
        <div class="source-item self-stretch p-2.5 relative bg-neutral-900/45 rounded-lg border border-neutral-800 inline-flex justify-start items-start gap-2.5 ${isReady ? 'cursor-pointer hover:border-primary/35 hover:bg-neutral-900/80 focus-within:border-primary/35 focus-within:bg-neutral-900/80' : 'cursor-not-allowed opacity-80'} transition shadow-[0_8px_28px_rgba(0,0,0,0.10)]"
            data-source-id="${this.escapeHTML(source.id)}"
            data-source-item
            data-source-ready="${isReady ? 'true' : 'false'}"
            data-selected-classes="bg-neutral-900 border-primary/60 shadow-[inset_0_0_0_1px_rgba(255,200,128,0.18),0_12px_40px_rgba(0,0,0,0.18)]">
          <div class="pt-1 inline-flex flex-col justify-start items-start">
            <input type="checkbox" data-source-checkbox
              class="${checkboxClasses}" ${isReady ? 'checked' : 'disabled'}
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

    /**
     * Get CSS class for status badge
     * @param {string} status - Source status
     * @returns {string} CSS classes
     */
    getStatusClass(status) {
      const classMap = {
        pending:    "status-pending bg-yellow-500/20 text-yellow-300",
        queued:     "status-pending bg-yellow-500/20 text-yellow-300",
        processing: "status-processing bg-primary/10 text-primary",
        ready:      "status-ready bg-green-500/20 text-green-300",
        failed:     "status-failed bg-red-500/20 text-red-300",
      };
      return classMap[status] || "bg-neutral-700/50 text-stone-300";
    }

    /**
     * Get display label for status
     * @param {string} status - Source status
     * @returns {string} Display label
     */
    getStatusLabel(status) {
      const labelMap = {
        pending:    "Menunggu",
        queued:     "Menunggu",
        processing: "Memproses",
        ready:      "Siap",
        failed:     "Gagal",
      };
      return labelMap[status] || "Unknown";
    }

    /**
     * Upload a new source
     * @param {FormData} formData - Form data with file
     */
    async uploadSource(formData) {
      try {
        // Add workspace_id to formData
        if (!formData.has("workspace_id")) {
          formData.append("workspace_id", this.workspaceId);
        }

        const response = await fetch("/api/sources/upload/", {
          method: "POST",
          headers: {
            'X-CSRFToken': this.getCSRFToken(),
          },
          body: formData,
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();
        console.log("Source uploaded successfully:", data);

        // Refresh list
        await this.fetchSources();

        // Start polling status for new source
        if (data.id) {
          this.pollSourceStatus(data.id);
        }

        return data;
      } catch (error) {
        console.error("Upload failed:", error);
        throw error;
      }
    }

    /**
     * Poll source status until ready or failed
     * @param {string|number} sourceId - Source ID to poll
     * @param {number} interval - Poll interval in ms (default 2000)
     */
    async pollSourceStatus(sourceId, interval = 2000) {
      // Clear existing poll if any
      if (this.pollIntervals.has(sourceId)) {
        clearInterval(this.pollIntervals.get(sourceId));
      }

      const poll = async () => {
        try {
          const response = await fetch(`/api/sources/${sourceId}/status/`);

          if (!response.ok) throw new Error(`HTTP ${response.status}`);

          const data = await response.json();
          const status = data.status || data;

          // Update UI element with complete source data
          this.updateSourceItemStatus(sourceId, data);

          // Stop polling if ready or failed
          if (status === "ready" || status === "failed") {
            clearInterval(this.pollIntervals.get(sourceId));
            this.pollIntervals.delete(sourceId);
            await this.fetchSources();
          }
        } catch (error) {
          console.error(`Poll failed for source ${sourceId}:`, error);
          // Continue polling on error
        }
      };

      // Initial poll
      await poll();

      // Set up interval
      const intervalId = setInterval(poll, interval);
      this.pollIntervals.set(sourceId, intervalId);
    }

    /**
     * Update status badge, progress bar, and error message for a source item dynamically
     * @param {string|number} sourceId - Source ID
     * @param {string|Object} statusOrData - New status string or complete source data object
     */
    updateSourceItemStatus(sourceId, statusOrData) {
      const item = this.container?.querySelector(
        `[data-source-id="${sourceId}"]`
      );

      if (!item) return;

      const status = typeof statusOrData === 'string' ? statusOrData : statusOrData.status;
      const progress = typeof statusOrData === 'string' ? 0 : (statusOrData.progress || 0);
      const errorMessage = typeof statusOrData === 'string' ? "" : (statusOrData.error_message || "");

      const badge = item.querySelector(".status-badge");
      if (badge) {
        const isProcessing = status === 'processing' || status === 'pending' || status === 'queued';
        const badgeAnimClass = isProcessing ? ' animate-pulse' : '';
        badge.className = `status-badge ${this.getStatusClass(status)}${badgeAnimClass} px-1.5 py-0.5 rounded-md text-[10px] font-semibold whitespace-nowrap`;
        badge.textContent = this.getStatusLabel(status);
        if (status === 'failed' && errorMessage) {
          badge.setAttribute("title", this.escapeHTML(errorMessage.slice(0, 120)));
        }
      }

      // Update progress bar
      let prgBar = item.querySelector(".progress-bar-wrap");
      const isProcessing = status === 'processing' || status === 'pending' || status === 'queued';
      if (isProcessing) {
        if (!prgBar) {
          const flexContainer = item.querySelector(".flex-1");
          if (flexContainer) {
            prgBar = document.createElement("div");
            prgBar.className = "progress-bar-wrap w-full bg-neutral-800 rounded-full h-1.5 mt-1.5 overflow-hidden";
            prgBar.innerHTML = `<div class="progress-bar-inner bg-primary h-1.5 rounded-full transition-all duration-300" style="width: 0%"></div>`;
            flexContainer.appendChild(prgBar);
          }
        }
        if (prgBar) {
          const innerBar = prgBar.querySelector(".progress-bar-inner");
          if (innerBar) {
            innerBar.style.width = `${progress}%`;
          }
        }
      } else if (prgBar) {
        prgBar.remove();
      }

      // Update error message
      let errDiv = item.querySelector(".error-reason-wrap");
      if (status === 'failed' && errorMessage) {
        if (!errDiv) {
          const flexContainer = item.querySelector(".flex-1");
          if (flexContainer) {
            errDiv = document.createElement("div");
            errDiv.className = "error-reason-wrap self-stretch mt-1.5 text-red-400 text-xs font-normal font-['Manrope'] leading-5 truncate hover:text-red-300 transition";
            flexContainer.appendChild(errDiv);
          }
        }
        if (errDiv) {
          errDiv.textContent = `Gagal: ${errorMessage}`;
          errDiv.setAttribute("title", errorMessage);
        }
      } else if (errDiv) {
        errDiv.remove();
      }
    }

    /**
     * Delete a source
     * @param {string|number} sourceId - Source ID to delete
     */
    async deleteSource(sourceId) {
      const item = this.container?.querySelector(
        `[data-source-id="${sourceId}"]`
      );

      if (!item) {
        console.error("Source item not found in DOM");
        return;
      }

      // Store original HTML for rollback
      const originalHTML = item.innerHTML;

      try {
        // Show loading state
        item.style.opacity = "0.5";
        item.style.pointerEvents = "none";

        const response = await fetch(`/api/sources/${sourceId}/`, {
          method: "DELETE",
          headers: {
            'X-CSRFToken': this.getCSRFToken(),
          },
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        // Smooth removal
        item.style.transition = "opacity 0.2s, max-height 0.2s";
        item.style.opacity = "0";
        item.style.maxHeight = "0";
        item.style.overflow = "hidden";

        setTimeout(() => {
          item.remove();

          // Refresh list to check empty state
          if (
            !this.container ||
            this.container.querySelectorAll(".source-item").length === 0
          ) {
            this.renderSourceList([]);
          }
        }, 200);

        // Clear any polling for this source
        if (this.pollIntervals.has(sourceId)) {
          clearInterval(this.pollIntervals.get(sourceId));
          this.pollIntervals.delete(sourceId);
        }
      } catch (error) {
        console.error("Delete failed:", error);

        // Revert UI
        item.style.opacity = "1";
        item.style.pointerEvents = "auto";
        item.innerHTML = originalHTML;

        // Show error message
        this.showErrorToast(
          "Failed to delete source. Please try again."
        );
      }
    }

    /**
     * Show loading state in container
     */
    showLoadingState() {
      if (!this.container) return;

      this.container.innerHTML = `
        <div class="flex items-center justify-center py-8">
          <div class="flex flex-col items-center gap-3">
            <div class="animate-spin">
              <svg class="w-6 h-6 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            </div>
            <div class="text-sm text-stone-400 font-['Manrope']">Memuat sumber...</div>
          </div>
        </div>
      `;
    }

    /**
     * Show error state in container
     * @param {string} message - Error message
     */
    showErrorState(message = "Failed to load sources") {
      if (!this.container) return;

      this.container.innerHTML = `
        <div class="flex flex-col items-center justify-center py-8 text-center">
          <div class="text-red-400 text-sm font-medium">${this.escapeHTML(message)}</div>
          <button
            onclick="window.workspaceSources?.fetchSources()"
            class="mt-3 px-3 py-1.5 rounded bg-red-500/20 text-red-300 hover:bg-red-500/30 transition-colors text-xs font-medium"
          >
            Retry
          </button>
        </div>
      `;
    }

    /**
     * Show error toast notification
     * @param {string} message - Error message
     */
    showErrorToast(message) {
      if (window.showToast) {
        window.showToast(message, "error");
        return;
      }

      if (window.ToastManager && typeof window.ToastManager.error === "function") {
        window.ToastManager.error(message);
        return;
      }

      alert(message);
    }

    /**
     * Escape HTML special characters
     * @param {string} text - Text to escape
     * @returns {string} Escaped text
     */
    escapeHTML(text) {
      const div = document.createElement("div");
      div.textContent = text;
      return div.innerHTML;
    }
  }

  window.WorkspaceSources = WorkspaceSources;
})();
