function getCookie(name) {
  const cookies = document.cookie.split(';').map(c => c.trim());
  for (const c of cookies) {
    if (c.startsWith(name + '=')) return decodeURIComponent(c.split('=')[1]);
  }
  return null;
}

async function readJsonResponse(response) {
  try {
    return await response.json();
  } catch (error) {
    return null;
  }
}

function getRenameModalFields() {
  return {
    id: document.getElementById('rename-workspace-id'),
    name: document.getElementById('rename-workspace-name'),
    save: document.getElementById('renameSave'),
  };
}

function populateRenameModal(button) {
  const fields = getRenameModalFields();
  if (!fields.id || !fields.name) return;

  fields.id.value = button.dataset.workspaceId || '';
  fields.name.value = button.dataset.workspaceName || '';
}

async function deleteWorkspace(workspaceId, cardElement) {
  if (!confirm('Hapus workspace ini? Aksi tidak dapat dibatalkan.')) return;

  const csrftoken = getCookie('csrftoken');
  const response = await fetch(`/api/workspaces/${workspaceId}/`, {
    method: 'DELETE',
    headers: {
      'X-CSRFToken': csrftoken || '',
    },
    credentials: 'same-origin',
  });

  if (response.status === 204) {
    cardElement?.remove();
    return;
  }

  alert('Gagal menghapus workspace');
}

async function renameWorkspace() {
  const fields = getRenameModalFields();
  if (!fields.id || !fields.name || !fields.save) return;

  const workspaceId = fields.id.value;
  const name = fields.name.value.trim();
  if (!name) return alert('Nama tidak boleh kosong');

  const previousLabel = fields.save.textContent;
  const csrftoken = getCookie('csrftoken');

  fields.save.disabled = true;
  fields.save.textContent = 'Saving...';

  try {
    const response = await fetch(`/api/workspaces/${workspaceId}/rename/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrftoken || '',
      },
      credentials: 'same-origin',
      body: JSON.stringify({ name }),
    });

    if (response.ok) {
      window.location.reload();
      return;
    }

    const data = await readJsonResponse(response);
    alert(data?.name || 'Gagal mengganti nama');
  } catch (error) {
    console.error(error);
    alert('Gagal mengganti nama');
  } finally {
    fields.save.disabled = false;
    fields.save.textContent = previousLabel;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  document.addEventListener('click', async (event) => {
    const actionButton = event.target.closest('[data-action]');
    if (!actionButton) return;

    event.stopPropagation();

    const action = actionButton.dataset.action;
    const workspaceId = actionButton.dataset.workspaceId;

    if (action === 'rename') {
      populateRenameModal(actionButton);
      return;
    }

    if (action === 'delete') {
      try {
        await deleteWorkspace(workspaceId, actionButton.closest('[data-workspace-card]'));
      } catch (error) {
        console.error(error);
        alert('Gagal menghapus workspace');
      }
    }
  });

  document.getElementById('renameSave')?.addEventListener('click', async () => {
    await renameWorkspace();
  });
});
