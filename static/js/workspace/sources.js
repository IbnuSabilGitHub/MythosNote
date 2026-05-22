(function () {
  /**
   * WorkspaceSources - Handles Sources panel dynamic rendering and API interactions
   */
  class WorkspaceSources {
    constructor(workspaceId) {
      this.workspaceId = workspaceId;
      this.container = document.querySelector("#source-list-container");
      this.pollIntervals = new Map(); // Track polling timers
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

      // Handle empty state
      if (!sources || sources.length === 0) {
        this.container.innerHTML = `
          <div class="flex flex-col items-center justify-center py-8 text-center">
            <div class="text-stone-400 text-sm">No sources uploaded.</div>
            <div class="text-stone-500 text-xs mt-1">Upload your first source to get started.</div>
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
            this.deleteSource(sourceId);
          });
        });
    }

    /**
     * Create HTML for a single source item
     * @param {Object} source - Source object
     * @returns {string} HTML string
     */
    createSourceItemHTML(source) {
      const statusClass = this.getStatusClass(source.status);
      const statusLabel = this.getStatusLabel(source.status);
      const fileName = source.file_name || source.name || "Unknown";

      return `
        <div class="source-item" data-source-id="${source.id}">
          <div class="flex items-center justify-between p-3 rounded border border-neutral-700 hover:border-neutral-600 transition-colors">
            <div class="flex items-center gap-3 flex-1 min-w-0">
              <div class="flex-1 min-w-0">
                <div class="text-sm font-medium text-stone-200 truncate">
                  ${this.escapeHTML(fileName)}
                </div>
                <div class="text-xs text-stone-500 mt-1">
                  ID: ${source.id}
                </div>
              </div>
            </div>
            <div class="flex items-center gap-3 ml-2">
              <span class="status-badge ${statusClass} px-2 py-1 rounded text-xs font-medium whitespace-nowrap">
                ${statusLabel}
              </span>
              <button
                data-delete-source="${source.id}"
                class="p-1.5 rounded hover:bg-red-500/20 text-stone-400 hover:text-red-400 transition-colors"
                title="Delete source"
                aria-label="Delete source ${this.escapeHTML(fileName)}"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          </div>
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
        pending: "status-pending bg-yellow-500/20 text-yellow-300",
        processing: "status-pending bg-blue-500/20 text-blue-300",
        ready: "status-ready bg-green-500/20 text-green-300",
        failed: "status-failed bg-red-500/20 text-red-300",
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
        pending: "Pending",
        processing: "Processing",
        ready: "Ready",
        failed: "Failed",
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

          // Update UI element
          this.updateSourceItemStatus(sourceId, status);

          // Stop polling if ready or failed
          if (status === "ready" || status === "failed") {
            clearInterval(this.pollIntervals.get(sourceId));
            this.pollIntervals.delete(sourceId);
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
     * Update status badge for a source item
     * @param {string|number} sourceId - Source ID
     * @param {string} status - New status
     */
    updateSourceItemStatus(sourceId, status) {
      const item = this.container?.querySelector(
        `[data-source-id="${sourceId}"]`
      );

      if (!item) return;

      const badge = item.querySelector(".status-badge");
      if (badge) {
        badge.className = `status-badge ${this.getStatusClass(status)} px-2 py-1 rounded text-xs font-medium whitespace-nowrap`;
        badge.textContent = this.getStatusLabel(status);
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
              <svg class="w-6 h-6 text-[#FFC880]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            </div>
            <div class="text-sm text-stone-400">Loading sources...</div>
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
