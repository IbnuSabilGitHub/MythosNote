(function () {
  /**
   * WorkspaceSelection
   * Manages source checkboxes: select all, per-item toggle, visual state.
   * Re-init after sources list re-renders via reinit().
   * Exposes getSelectedSourceIds() for chat.js to consume.
   */

  const container = document.querySelector("#source-list-container");
  const selectAllRow = document.querySelector("[data-select-all-row]");
  const selectAllCheckbox = document.querySelector("[data-select-all]");

  function getItems() {
    return Array.from(document.querySelectorAll("[data-source-item]"));
  }

  function updateItemVisual(item, checked) {
    const selectedClasses = (item.getAttribute("data-selected-classes") || "")
      .split(" ")
      .filter(Boolean);
    selectedClasses.forEach((cls) => item.classList.toggle(cls, checked));
  }

  function updateSelectAllState() {
    if (!selectAllCheckbox) return;
    const items = getItems().filter((item) => item.dataset.sourceReady !== "false");
    const allChecked =
      items.length > 0 && items.every((item) => {
        const cb = item.querySelector("[data-source-checkbox]");
        return cb && cb.checked;
      });
    selectAllCheckbox.checked = allChecked;
    selectAllCheckbox.indeterminate =
      !allChecked && items.some((item) => {
        const cb = item.querySelector("[data-source-checkbox]");
        return cb && cb.checked;
      });

    // Update counter badge in chat header
    updateSourceCounter();
  }

  function updateSourceCounter() {
    const counterEl = document.getElementById("chat-source-counter");
    const selectionInfoContainer = document.getElementById("selection-info-container");
    const selectedInfoText = document.getElementById("selected-info-text");

    const items = getItems();
    const readyItems = items.filter((item) => {
      const cb = item.querySelector("[data-source-checkbox]");
      return cb && !cb.disabled;
    });
    const checkedItems = readyItems.filter((item) => {
      const cb = item.querySelector("[data-source-checkbox]");
      return cb && cb.checked;
    });
    const total = readyItems.length;
    const selected = checkedItems.length;
    if (counterEl) {
      if (total === 0) {
        counterEl.textContent = "0 sumber";
      } else if (selected === total) {
        counterEl.textContent = `${total} sumber`;
      } else {
        counterEl.textContent = `${selected}/${total} sumber`;
      }
    }

    if (selectionInfoContainer && selectedInfoText) {
      if (selected > 0) {
        selectionInfoContainer.style.display = "flex";
        selectionInfoContainer.classList.remove("hidden");
        selectedInfoText.textContent = `${selected} sumber dipakai untuk chat`;
      } else {
        selectionInfoContainer.style.display = "none";
        selectionInfoContainer.classList.add("hidden");
      }
    }
    
    document.dispatchEvent(new CustomEvent('sourceSelectionChanged'));
  }

  function setAllItems(checked) {
    getItems().forEach((item) => {
      const cb = item.querySelector("[data-source-checkbox]");
      if (cb?.disabled) return;
      if (cb) cb.checked = checked;
      updateItemVisual(item, checked);
    });
  }

  function bindItemEvents() {
    getItems().forEach((item) => {
      const cb = item.querySelector("[data-source-checkbox]");
      if (!cb) return;

      // Prevent double-binding
      if (item.dataset.selectionBound) return;
      item.dataset.selectionBound = "1";

      updateItemVisual(item, cb.checked);

      cb.addEventListener("change", () => {
        updateItemVisual(item, cb.checked);
        updateSelectAllState();
      });

      item.addEventListener("click", (e) => {
        if (cb.disabled) return;
        if (e.target === cb) return;
        // Only toggle if not clicking delete button
        if (e.target.closest("[data-delete-source]")) return;
        cb.checked = !cb.checked;
        updateItemVisual(item, cb.checked);
        updateSelectAllState();
      });
    });

    updateSelectAllState();
  }

  // Select-all checkbox
  if (selectAllCheckbox) {
    selectAllCheckbox.addEventListener("change", () => {
      setAllItems(selectAllCheckbox.checked);
      updateSelectAllState();
    });
  }

  if (selectAllRow && selectAllCheckbox) {
    selectAllRow.addEventListener("click", (e) => {
      if (e.target === selectAllCheckbox) return;
      selectAllCheckbox.checked = !selectAllCheckbox.checked;
      setAllItems(selectAllCheckbox.checked);
      updateSelectAllState();
    });
  }

  // Reset selection button
  const resetBtn = document.getElementById("btn-reset-selection");
  if (resetBtn) {
    resetBtn.addEventListener("click", () => {
      setAllItems(false);
      updateSelectAllState();
    });
  }

  // Watch for DOM changes in the source list to re-bind new items
  if (container) {
    const observer = new MutationObserver(() => {
      bindItemEvents();
    });
    observer.observe(container, { childList: true, subtree: true });
  }

  window.WorkspaceSelection = {
    init() {
      bindItemEvents();
    },

    reinit() {
      bindItemEvents();
    },

    /**
     * Returns array of selected source UUIDs.
     * Empty array means "no filter → use all ready sources".
     */
    getSelectedSourceIds() {
      const items = getItems().filter((item) => item.dataset.sourceReady !== "false");
      return items
        .filter((item) => {
          const cb = item.querySelector("[data-source-checkbox]");
          return cb && cb.checked;
        })
        .map((item) => item.dataset.sourceId);
    },

    updateCounter() {
      updateSourceCounter();
    },
  };
})();
