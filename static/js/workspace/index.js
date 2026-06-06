document.addEventListener("DOMContentLoaded", () => {
  const wsData = document.getElementById("workspace-data");
  const workspaceId =
    wsData?.dataset.workspaceId ||
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

  window.WorkspaceUploadModal?.init?.(workspaceId);
});

