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
    const items = getItems();
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
    if (!counterEl) return;
    const items = getItems();
    const readyItems = items.filter((item) => {
      const cb = item.querySelector("[data-source-checkbox]");
      return cb; // only items with checkbox = source items
    });
    const checkedItems = readyItems.filter((item) => {
      const cb = item.querySelector("[data-source-checkbox]");
      return cb && cb.checked;
    });
    const total = readyItems.length;
    const selected = checkedItems.length;
    if (total === 0) {
      counterEl.textContent = "0 sumber";
    } else if (selected === total || selected === 0) {
      counterEl.textContent = `${total} sumber`;
    } else {
      counterEl.textContent = `${selected}/${total} sumber`;
    }
  }

  function setAllItems(checked) {
    getItems().forEach((item) => {
      const cb = item.querySelector("[data-source-checkbox]");
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
      const items = getItems();
      const allCount = items.length;
      if (allCount === 0) return [];

      const selected = items
        .filter((item) => {
          const cb = item.querySelector("[data-source-checkbox]");
          return cb && cb.checked;
        })
        .map((item) => item.dataset.sourceId);

      // If all selected (or none selected) → send empty = fallback all
      if (selected.length === 0 || selected.length === allCount) return [];
      return selected;
    },

    updateCounter() {
      updateSourceCounter();
    },
  };
})();
