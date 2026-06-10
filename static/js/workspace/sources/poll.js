export async function uploadSource(formData) {
  try {
    // Add workspace_id to formData
    if (!formData.has("workspace_id")) {
      formData.append("workspace_id", this.workspaceId);
    }

    const response = await fetch("/api/sources/upload/", {
      method: "POST",
      headers: {
        "X-CSRFToken": this.getCSRFToken(),
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

export async function pollSourceStatus(sourceId, interval = 2000) {
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
        if (this.debouncedFetchSources) {
          await this.debouncedFetchSources();
        } else {
          await this.fetchSources();
        }
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

export function updateSourceItemStatus(sourceId, statusOrData) {
  const item = this.container?.querySelector(`[data-source-id="${sourceId}"]`);
  if (!item) return;

  const status = typeof statusOrData === "string" ? statusOrData : statusOrData.status;
  const progress = typeof statusOrData === "string" ? 0 : statusOrData.progress || 0;
  const errorMessage =
    typeof statusOrData === "string" ? "" : statusOrData.error_message || "";

  const badge = item.querySelector(".status-badge");
  if (badge) {
    const isProcessing = ["processing", "pending", "queued"].includes(status);
    const badgeAnimClass = isProcessing ? " animate-pulse" : "";
    badge.className = `status-badge ${this.getStatusClass(status)}${badgeAnimClass} px-1.5 py-0.5 rounded-md text-[10px] font-semibold whitespace-nowrap`;
    badge.textContent = this.getStatusLabel(status);
    if (status === "failed" && errorMessage) {
      badge.setAttribute("title", this.escapeHTML(errorMessage.slice(0, 120)));
    }
  }

  // Update progress bar
  let prgBar = item.querySelector(".progress-bar-wrap");
  const isProcessing = ["processing", "pending", "queued"].includes(status);
  if (isProcessing) {
    if (!prgBar) {
      const flexContainer = item.querySelector(".flex-1");
      if (flexContainer) {
        prgBar = document.createElement("div");
        prgBar.className =
          "progress-bar-wrap w-full bg-neutral-800 rounded-full h-1.5 mt-1.5 overflow-hidden";
        prgBar.innerHTML =
          '<div class="progress-bar-inner bg-primary h-1.5 rounded-full transition-all duration-300" style="width: 0%"></div>';
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
  if (status === "failed" && errorMessage) {
    if (!errDiv) {
      const flexContainer = item.querySelector(".flex-1");
      if (flexContainer) {
        errDiv = document.createElement("div");
        errDiv.className =
          "error-reason-wrap self-stretch mt-1.5 text-red-400 text-xs font-normal font-['Manrope'] leading-5 whitespace-normal break-words hover:text-red-300 transition";
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

