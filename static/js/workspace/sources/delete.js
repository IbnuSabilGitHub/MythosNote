export async function deleteSource(sourceId) {
  const item = this.container?.querySelector(`[data-source-id="${sourceId}"]`);
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
        "X-CSRFToken": this.getCSRFToken(),
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
    this.showErrorToast("Failed to delete source. Please try again.");
  }
}

