document.addEventListener("DOMContentLoaded", () => {
  // Get workspace ID from data attribute or URL
  const workspaceContainer = document.querySelector("[data-workspace-id]");
  const workspaceId =
    workspaceContainer?.dataset.workspaceId ||
    new URLSearchParams(window.location.search).get("workspace_id");

  if (workspaceId && window.WorkspaceSources) {
    window.workspaceSources = new window.WorkspaceSources(workspaceId);
    window.workspaceSources.fetchSources();
  }

  if (window.WorkspaceLayout) {
    window.WorkspaceLayout.init();
  }

  if (window.WorkspaceSelection) {
    window.WorkspaceSelection.init();
  }
});
