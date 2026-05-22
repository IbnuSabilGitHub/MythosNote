(function () {
  const createSelectionController = () => {
    const selectAllRow = document.querySelector("[data-select-all-row]");
    const selectAllCheckbox = document.querySelector("[data-select-all]");
    const items = Array.from(document.querySelectorAll("[data-source-item]"));

    const updateItemState = (item, checked) => {
      const selectedClasses = (item.getAttribute("data-selected-classes") || "")
        .split(" ")
        .filter(Boolean);
      selectedClasses.forEach((className) => {
        item.classList.toggle(className, checked);
      });
    };

    const updateSelectAllState = () => {
      if (!selectAllCheckbox) return;
      const allChecked = items.length > 0 && items.every((item) => {
        const checkbox = item.querySelector("[data-source-checkbox]");
        return checkbox && checkbox.checked;
      });
      selectAllCheckbox.checked = allChecked;
    };

    const setAllItems = (checked) => {
      items.forEach((item) => {
        const checkbox = item.querySelector("[data-source-checkbox]");
        if (checkbox) {
          checkbox.checked = checked;
        }
        updateItemState(item, checked);
      });
    };

    if (selectAllCheckbox) {
      selectAllCheckbox.addEventListener("change", () => {
        setAllItems(selectAllCheckbox.checked);
      });
    }

    if (selectAllRow && selectAllCheckbox) {
      selectAllRow.addEventListener("click", (event) => {
        if (event.target === selectAllCheckbox) return;
        selectAllCheckbox.checked = !selectAllCheckbox.checked;
        setAllItems(selectAllCheckbox.checked);
      });
    }

    items.forEach((item) => {
      const checkbox = item.querySelector("[data-source-checkbox]");
      if (!checkbox) return;

      updateItemState(item, checkbox.checked);

      checkbox.addEventListener("change", () => {
        updateItemState(item, checkbox.checked);
        updateSelectAllState();
      });

      item.addEventListener("click", (event) => {
        if (event.target === checkbox) return;
        checkbox.checked = !checkbox.checked;
        updateItemState(item, checkbox.checked);
        updateSelectAllState();
      });
    });

    updateSelectAllState();
  };

  window.WorkspaceSelection = {
    init() {
      createSelectionController();
    }
  };
})();
