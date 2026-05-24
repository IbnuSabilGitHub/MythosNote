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
    modal: document.getElementById('renameWorkspaceModal'),
    form: document.getElementById('renameWorkspaceForm'),
    id: document.getElementById('rename-workspace-id'),
    name: document.getElementById('rename-workspace-name'),
    save: document.getElementById('renameSave'),
  };
}

function getDeleteModalFields() {
  return {
    modal: document.getElementById('deleteWorkspaceModal'),
    title: document.getElementById('deleteWorkspaceTitle'),
    description: document.getElementById('deleteWorkspaceDescription'),
    cancel: document.getElementById('deleteWorkspaceCancel'),
    confirm: document.getElementById('deleteWorkspaceConfirm'),
  };
}

function showToast(type, message) {
  if (window.ToastManager && typeof window.ToastManager[type] === 'function') {
    window.ToastManager[type](message);
  }
}

let renameInFlight = false;
let deleteInFlight = false;

function setModalOpen(modal, open) {
  if (!modal) return;

  modal.classList.toggle('hidden', !open);
  modal.style.display = open ? 'flex' : 'none';
  modal.setAttribute('aria-hidden', open ? 'false' : 'true');
  document.body.classList.toggle('overflow-hidden', open);
}

function closeDeleteModal() {
  const fields = getDeleteModalFields();
  setModalOpen(fields.modal, false);

  if (fields.confirm) {
    fields.confirm.dataset.workspaceId = '';
    fields.confirm.dataset.workspaceName = '';
  }
}

function openDeleteModal(button) {
  const fields = getDeleteModalFields();
  const workspaceId = button.dataset.workspaceId || '';
  const workspaceName = button.dataset.workspaceName || 'workspace ini';

  if (!fields.modal || !fields.title || !fields.description || !fields.confirm) return;

  fields.title.textContent = 'Hapus Workspace?';
  fields.description.textContent = `Tindakan ini tidak dapat dibatalkan. Menghapus ${workspaceName} akan menghapus semua file, dokumen, dan analisis AI yang terkait secara permanen dari server.`;
  fields.confirm.dataset.workspaceId = workspaceId;
  fields.confirm.dataset.workspaceName = workspaceName;

  setModalOpen(fields.modal, true);
}

function updateWorkspaceCard(workspaceId, newName) {
  const card = document.querySelector(`[data-workspace-card][data-workspace-id="${workspaceId}"]`);
  if (!card) return;

  const heading = card.querySelector('h3');
  if (heading) {
    heading.textContent = newName;
  }

  card.dataset.workspaceName = newName;
  card.setAttribute('aria-label', `Open workspace ${newName}`);

  const renameButton = card.querySelector('[data-action="rename"]');
  if (renameButton) {
    renameButton.dataset.workspaceName = newName;
  }

  const deleteButton = card.querySelector('[data-action="delete"]');
  if (deleteButton) {
    deleteButton.dataset.workspaceName = newName;
  }
}

function populateRenameModal(button) {
  const fields = getRenameModalFields();
  if (!fields.id || !fields.name) return;

  fields.id.value = button.dataset.workspaceId || '';
  fields.name.value = button.dataset.workspaceName || '';
}

function closeRenameModal() {
  const fields = getRenameModalFields();
  setModalOpen(fields.modal, false);
}

async function deleteWorkspace(workspaceId, cardElement) {
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
    showToast('success', 'Workspace berhasil dihapus.');
    return;
  }

  showToast('error', 'Gagal menghapus workspace.');
}

async function renameWorkspace() {
  const fields = getRenameModalFields();
  if (!fields.id || !fields.name || !fields.save) return;
  if (renameInFlight || fields.save.disabled) return;

  const workspaceId = fields.id.value;
  const name = fields.name.value.trim();
  if (!name) {
    showToast('warning', 'Nama workspace tidak boleh kosong.');
    return;
  }

  const previousLabel = fields.save.textContent;
  const csrftoken = getCookie('csrftoken');

  renameInFlight = true;
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
      updateWorkspaceCard(workspaceId, name);
      closeRenameModal();
      showToast('success', 'Workspace berhasil diganti nama.');
      return;
    }

    const data = await readJsonResponse(response);
    showToast('error', data?.name || 'Gagal mengganti nama workspace.');
  } catch (error) {
    console.error(error);
    showToast('error', 'Gagal mengganti nama workspace.');
  } finally {
    fields.save.disabled = false;
    fields.save.textContent = previousLabel;
    renameInFlight = false;
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
      openDeleteModal(actionButton);
    }
  });

  document.addEventListener('click', (event) => {
    const card = event.target.closest('[data-workspace-card]');
    if (!card) return;

    if (event.target.closest('button, a, [role="menuitem"]')) return;

    const targetUrl = card.dataset.workspaceUrl;
    if (targetUrl) {
      window.location.href = targetUrl;
    }
  });

  document.addEventListener('keydown', (event) => {
    const card = event.target.closest('[data-workspace-card]');
    if (!card) return;

    if (event.target.closest('button, a, [role="menuitem"]')) return;
    if (event.key !== 'Enter' && event.key !== ' ') return;

    event.preventDefault();
    const targetUrl = card.dataset.workspaceUrl;
    if (targetUrl) {
      window.location.href = targetUrl;
    }
  });

  document.getElementById('renameWorkspaceForm')?.addEventListener('submit', async (event) => {
    event.preventDefault();
    await renameWorkspace();
  });

  const deleteFields = getDeleteModalFields();
  deleteFields.cancel?.addEventListener('click', closeDeleteModal);
  deleteFields.modal?.addEventListener('click', (event) => {
    if (event.target === deleteFields.modal) {
      closeDeleteModal();
    }
  });
  deleteFields.confirm?.addEventListener('click', async () => {
    const workspaceId = deleteFields.confirm?.dataset.workspaceId || '';
    if (!workspaceId || deleteInFlight || deleteFields.confirm.disabled) return;

    try {
      deleteInFlight = true;
      deleteFields.confirm.disabled = true;
      deleteFields.confirm.textContent = 'Menghapus...';

      const cardElement = document.querySelector(`[data-workspace-card][data-workspace-id="${workspaceId}"]`);
      await deleteWorkspace(workspaceId, cardElement);
      closeDeleteModal();
    } catch (error) {
      console.error(error);
      showToast('error', 'Gagal menghapus workspace.');
    } finally {
      deleteInFlight = false;
      deleteFields.confirm.disabled = false;
      deleteFields.confirm.textContent = 'Hapus';
    }
  });
});
