export async function fetchSources(workspaceId = null) {
  try {
    const id = workspaceId || this.workspaceId;

    // Snapshot selection BEFORE showLoadingState wipes the container
    const existingItems = this.container?.querySelectorAll("[data-source-item]") ?? [];
    const selectionSnapshot =
      existingItems.length > 0
        ? new Set(
            Array.from(existingItems)
              .filter((item) => {
                const cb = item.querySelector("[data-source-checkbox]");
                return cb && cb.checked && !cb.disabled;
              })
              .map((item) => item.dataset.sourceId)
          )
        : null; // null → first load, keep defaults

    this.showLoadingState();

    const response = await fetch(`/api/sources/?workspace_id=${id}`);

    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const data = await response.json();
    this.renderSourceList(data.results || data, selectionSnapshot);
  } catch (error) {
    console.error("Failed to fetch sources:", error);
    this.showErrorState("Gagal memuat sumber. Silakan refresh halaman.");
  }
}

export function renderSourceList(sources, selectionSnapshot = undefined) {
  if (!this.container) {
    console.warn("Source list container not found");
    return;
  }

  this.updatePanelSummary(sources || []);

  // Handle empty state
  if (!sources || sources.length === 0) {
// eslint-disable-next-line no-unsanitized/property
    this.container.innerHTML = `
      <div class="flex min-h-56 w-full flex-col items-center justify-center rounded-xl border border-dashed border-neutral-800 bg-neutral-900/30 px-4 py-8 text-center">
        <div class="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
          <iconify-icon icon="tabler:file-upload" class="text-xl"></iconify-icon>
        </div>
        <div class="text-stone-300 text-sm font-medium font-['Manrope']">Belum ada sumber</div>
        <div class="text-stone-500 text-xs mt-1 font-['Manrope']">Upload 1-${this.maxSources} file utama untuk mulai chat.</div>
      </div>
    `;
    return;
  }

  // ── Determine previous selection ──────────────────────────────────────
  // Priority: snapshot passed from fetchSources > items still in DOM > null (first render)
  let previouslyChecked = selectionSnapshot;
  if (previouslyChecked === undefined) {
    // Called directly (e.g. after upload modal closes) — read current DOM
    const existingItems = this.container.querySelectorAll("[data-source-item]");
    if (existingItems.length > 0) {
      previouslyChecked = new Set();
      existingItems.forEach((item) => {
        const cb = item.querySelector("[data-source-checkbox]");
        if (cb && cb.checked && !cb.disabled) {
          previouslyChecked.add(item.dataset.sourceId);
        }
      });
    } else {
      previouslyChecked = null; // first render
    }
  }

  // Clear container
  this.container.innerHTML = "";

  // Create list items
  const listHTML = sources.map((source) => this.createSourceItemHTML(source)).join("");
// eslint-disable-next-line no-unsanitized/property
  this.container.innerHTML = listHTML;

  // ── Restore selection state ───────────────────────────────────────────
  // previouslyChecked === null means first render: keep all-checked defaults.
  // Otherwise, restore exactly the saved set.
  if (previouslyChecked !== null) {
    this.container.querySelectorAll("[data-source-item]").forEach((item) => {
      const cb = item.querySelector("[data-source-checkbox]");
      if (!cb || cb.disabled) return;
      cb.checked = previouslyChecked.has(item.dataset.sourceId);
    });
    window.WorkspaceSelection?.reinit?.();
    window.WorkspaceSelection?.updateCounter?.();
  }

  // Attach event listeners to delete buttons
  this.container.querySelectorAll("[data-delete-source]").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const sourceId = btn.dataset.deleteSource;
      const fileName =
        btn.getAttribute("aria-label")?.replace("Hapus ", "") || "sumber";

      if (confirm(`Apakah Anda yakin ingin menghapus sumber "${fileName}"?`)) {
        this.deleteSource(sourceId);
      }
    });
  });
}


export function updatePanelSummary(sources) {
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

export function showLoadingState() {
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

export function showErrorState(message = "Gagal memuat sumber. Silakan refresh halaman.") {
  if (!this.container) return;

// eslint-disable-next-line no-unsanitized/property
  this.container.innerHTML = `
    <div class="flex flex-col items-center justify-center py-8 text-center">
      <div class="text-red-400 text-sm font-medium">${this.escapeHTML(message)}</div>
      <button
        onclick="window.workspaceSources?.fetchSources()"
        class="mt-3 px-3 py-1.5 rounded bg-red-500/20 text-red-300 hover:bg-red-500/30 transition-colors text-xs font-medium"
      >
        Coba lagi
      </button>
    </div>
  `;
}

export function showErrorToast(message) {
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

