function apiFetch(url, options) {
  if (window.MythosApi?.apiFetch) {
    return window.MythosApi.apiFetch(url, options);
  }
  return fetch(url, options).then(async (response) => {
    const data = await response.json().catch(() => null);
    if (!response.ok) {
      const err = new Error(data?.detail || `HTTP ${response.status}`);
      err.status = response.status;
      err.data = data;
      throw err;
    }
    return data;
  });
}

export function createGenerateJob(workspaceId, payload) {
  return apiFetch(`/api/workspace/${workspaceId}/generate/`, {
    method: "POST",
    body: payload,
  });
}

export function fetchGenerateJobs(workspaceId) {
  return apiFetch(`/api/workspace/${workspaceId}/generate/`);
}

export function fetchGenerateJob(jobId) {
  return apiFetch(`/api/generate/${jobId}/`);
}

export function deleteGenerateJob(jobId) {
  return apiFetch(`/api/generate/${jobId}/`, { method: "DELETE" });
}
