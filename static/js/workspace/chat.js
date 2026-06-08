
/**
 * Handle workspace chat interactions
 * Tahap 5 & 6: Dynamic chat + source selection filter
 */

document.addEventListener('DOMContentLoaded', () => {
    const workspaceData = document.getElementById('workspace-data');
    if (!workspaceData) return;

    marked.setOptions({
        breaks: true
    });

    const workspaceId = workspaceData.dataset.workspaceId;
    const chatInput = document.getElementById('chat-input');
    const chatSubmitBtn = document.getElementById('chat-submit-btn');
    const messagesContainer = document.getElementById('chat-messages-container');

    const aiProvider = (workspaceData.dataset.aiProvider || 'gemini').toLowerCase();
    
    function getAiAvatarHtml() {
        if (aiProvider === 'deepseek' || aiProvider === 'openrouter') {
            return `<img class="h-5 w-5 shrink-0" src="/static/svg/deepseek-logo.svg" alt="DeepSeek AI Logo" />`;
        }
        return `<iconify-icon icon="simple-icons:googlegemini" class="text-base text-primary shrink-0"></iconify-icon>`;
    }

    let currentSessionId = null;
    let isWaitingForResponse = false;
    let loadingIntervalId = null;

    function renderEmptyState() {
        if (!messagesContainer || messagesContainer.children.length > 0) return;
 
        messagesContainer.innerHTML = `
            <div id="chat-empty-state" class="flex min-h-full w-full max-w-3xl flex-1 flex-col items-center justify-center px-4 py-12 text-center">
                <div class="mb-5 flex h-14 w-14 items-center justify-center rounded-2xl border border-primary/25 bg-primary/10 text-primary shadow-[0_20px_70px_rgba(255,200,128,0.08)]">
                    <iconify-icon icon="tabler:sparkles" class="text-2xl"></iconify-icon>
                </div>
                <h1 class="font-['Newsreader'] text-3xl font-normal leading-tight text-zinc-100">Mulai dari sumber Anda</h1>
                <p class="mt-3 max-w-md font-['Manrope'] text-sm leading-6 text-stone-400">Pilih file di panel Sumber, lalu tanyakan ringkasan, perbandingan, atau poin penting yang perlu dicek.</p>
                <div class="mt-6 grid w-full max-w-xl gap-2 sm:grid-cols-3">
                    <button type="button" data-chat-prompt="Buat ringkasan singkat dari sumber yang dipilih." class="rounded-lg border border-neutral-800 bg-neutral-900/60 px-3 py-2 text-left font-['Manrope'] text-xs text-stone-300 transition hover:border-primary/40 hover:text-primary focus:outline-none focus:ring-2 focus:ring-primary/40">Ringkas sumber</button>
                    <button type="button" data-chat-prompt="Apa konsep paling penting dari sumber ini?" class="rounded-lg border border-neutral-800 bg-neutral-900/60 px-3 py-2 text-left font-['Manrope'] text-xs text-stone-300 transition hover:border-primary/40 hover:text-primary focus:outline-none focus:ring-2 focus:ring-primary/40">Cari konsep utama</button>
                    <button type="button" data-chat-prompt="Buat daftar pertanyaan latihan dari sumber ini." class="rounded-lg border border-neutral-800 bg-neutral-900/60 px-3 py-2 text-left font-['Manrope'] text-xs text-stone-300 transition hover:border-primary/40 hover:text-primary focus:outline-none focus:ring-2 focus:ring-primary/40">Buat latihan</button>
                </div>
            </div>
        `;

        messagesContainer.querySelectorAll('[data-chat-prompt]').forEach((button) => {
            button.addEventListener('click', () => {
                if (chatInput.disabled) return;
                chatInput.value = button.dataset.chatPrompt || '';
                if (typeof checkSelection === 'function') checkSelection();
                chatInput.focus();
            });
        });
    }

    function clearEmptyState() {
        const empty = document.getElementById('chat-empty-state');
        if (empty) empty.remove();
    }

    function getCsrfToken() {
        return window.MythosCsrf?.getCsrfToken?.() || (
            document.cookie.match(/(?:^|;)\s*csrftoken=([^;]+)/)?.[1] || ''
        );
    }

    function escapeHtml(unsafe) {
        return window.MythosDom?.escapeHtml?.(unsafe) || (unsafe || '').toString()
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function renderUserMessage(text) {
        const msgDiv = document.createElement('div');
        clearEmptyState();
        msgDiv.className = 'w-full max-w-3xl flex flex-col justify-start items-end animate-slide-up';
// eslint-disable-next-line no-unsanitized/property
        msgDiv.innerHTML = `
            <div class="max-w-[85%] inline-flex justify-end items-start relative group/msg">
                <div class="absolute top-2 left-2 opacity-0 group-hover/msg:opacity-100 transition-opacity">
                    <button type="button" class="btn-copy-msg p-1 rounded-lg bg-neutral-950/60 border border-neutral-800 hover:bg-neutral-800 text-stone-400 hover:text-primary transition cursor-pointer focus:outline-none" title="Salin Pesan">
                        <iconify-icon icon="tabler:copy" class="text-xs"></iconify-icon>
                    </button>
                </div>
                <div class="self-stretch pl-8 pr-6 py-4 bg-primary/15 rounded-2xl rounded-tr-md border border-primary/30 inline-flex flex-col justify-start items-start shadow-[0_12px_40px_rgba(0,0,0,0.18)]">
                    <div class="text-zinc-200 text-base font-normal font-['Manrope'] leading-6 whitespace-pre-wrap">${escapeHtml(text)}</div>
                </div>
            </div>
        `;
        messagesContainer.appendChild(msgDiv);

        const copyBtn = msgDiv.querySelector('.btn-copy-msg');
        if (copyBtn) {
            copyBtn.addEventListener('click', () => {
                navigator.clipboard.writeText(text).then(() => {
                    const icon = copyBtn.querySelector('iconify-icon');
                    if (icon) {
                        icon.setAttribute('icon', 'tabler:check');
                        icon.classList.add('text-green-400');
                        setTimeout(() => {
                            icon.setAttribute('icon', 'tabler:copy');
                            icon.classList.remove('text-green-400');
                        }, 2000);
                    }
                    if (window.ToastManager) {
                        window.ToastManager.success('Pesan disalin ke clipboard.');
                    }
                }).catch(err => {
                    console.error('Failed to copy message:', err);
                });
            });
        }

        scrollToBottom();
    }

    function renderBotMessage(text, sources) {
        const msgDiv = document.createElement('div');
        clearEmptyState();
        msgDiv.className = 'w-full max-w-3xl flex justify-start items-start gap-3 sm:gap-4 animate-slide-up';

        let sourcesHtml = '';
        if (sources && sources.length > 0) {
            sourcesHtml = '<div class="mt-2 pt-2 border-t border-neutral-800 text-xs text-stone-400">Sumber: ' +
                sources.map(s => `<span class="text-primary">${escapeHtml(s.original_filename)}</span>`).join(', ') +
                '</div>';
        }

        const renderedMarkdown = window.MythosDom.renderMarkdown(text);

        // eslint-disable-next-line no-unsanitized/property
        msgDiv.innerHTML = `
            <div class="w-8 h-9 pt-1 inline-flex flex-col justify-start items-start shrink-0">
                <div class="w-8 h-8 bg-neutral-900 rounded-xl outline -outline-offset-1 outline-neutral-800 inline-flex justify-center items-center">
                    ${getAiAvatarHtml()}
                </div>
            </div>
            <div class="max-w-[85%] px-4 pt-3.5 pb-4 bg-neutral-900/70 rounded-2xl border border-neutral-800 inline-flex flex-col justify-start items-start gap-4 relative group/msg">
                <div class="absolute bottom-3 right-3 opacity-0 group-hover/msg:opacity-100 transition-opacity">
                    <button type="button" class="btn-copy-msg p-1.5 rounded-lg bg-neutral-950/60 border border-neutral-800 hover:bg-neutral-800 text-stone-400 hover:text-primary transition cursor-pointer focus:outline-none" title="Salin Markdown">
                        <iconify-icon icon="tabler:copy" class="text-sm"></iconify-icon>
                    </button>
                </div>
                <div class="self-stretch flex flex-col justify-start items-start gap-1.5 pr-6">
                    <div class="chat-markdown">${renderedMarkdown}</div>
                    ${sourcesHtml}
                </div>
            </div>
        `;
        messagesContainer.appendChild(msgDiv);

        const copyBtn = msgDiv.querySelector('.btn-copy-msg');
        if (copyBtn) {
            copyBtn.addEventListener('click', () => {
                navigator.clipboard.writeText(text).then(() => {
                    const icon = copyBtn.querySelector('iconify-icon');
                    if (icon) {
                        icon.setAttribute('icon', 'tabler:check');
                        icon.classList.add('text-green-400');
                        setTimeout(() => {
                            icon.setAttribute('icon', 'tabler:copy');
                            icon.classList.remove('text-green-400');
                        }, 2000);
                    }
                    if (window.ToastManager) {
                        window.ToastManager.success('Pesan disalin ke clipboard.');
                    }
                }).catch(err => {
                    console.error('Failed to copy message:', err);
                });
            });
        }

        scrollToBottom();
    }

    function renderLoading() {
        const msgDiv = document.createElement('div');
        msgDiv.id = 'chat-loading';
        clearEmptyState();
        msgDiv.className = 'w-full max-w-3xl flex justify-start items-start gap-3 sm:gap-4 animate-slide-up';
 
        msgDiv.innerHTML = `
            <div class="w-8 h-9 pt-1 inline-flex flex-col justify-start items-start shrink-0">
                <div class="w-8 h-8 bg-neutral-900 rounded-xl outline -outline-offset-1 outline-primary/30 inline-flex justify-center items-center relative overflow-hidden shadow-[0_0_15px_rgba(255,200,128,0.15)]">
                    <div class="absolute inset-0 bg-primary/10 animate-pulse"></div>
                    ${getAiAvatarHtml()}
                </div>
            </div>
            <div class="px-5 py-4 bg-neutral-900/80 rounded-2xl border border-primary/20 inline-flex items-center gap-3 relative overflow-hidden shadow-[0_8px_30px_rgba(0,0,0,0.2)]">
                <div class="absolute top-0 left-0 h-[1px] w-full bg-gradient-to-r from-transparent via-primary/50 to-transparent"></div>
                <span id="chat-loading-text" class="text-sm font-['Manrope'] font-medium text-primary/80 transition-all duration-300 animate-pulse">Menganalisis sumber...</span>
                <div class="flex items-center gap-1.5 px-1">
                    <div class="w-1.5 h-1.5 rounded-full bg-primary/70 animate-bounce" style="animation-delay: 0ms"></div>
                    <div class="w-1.5 h-1.5 rounded-full bg-primary/70 animate-bounce" style="animation-delay: 150ms"></div>
                    <div class="w-1.5 h-1.5 rounded-full bg-primary/70 animate-bounce" style="animation-delay: 300ms"></div>
                </div>
            </div>
        `;
        messagesContainer.appendChild(msgDiv);
        scrollToBottom();

        const loadingTexts = [
            "Menganalisis sumber...",
            "Mencari konteks relevan...",
            "Memahami instruksi...",
            "Menyusun jawaban..."
        ];
        let textIndex = 0;
        
        if (loadingIntervalId) clearInterval(loadingIntervalId);
        
        loadingIntervalId = setInterval(() => {
            const textElement = document.getElementById('chat-loading-text');
            if (textElement) {
                textIndex++;
                if (textIndex < loadingTexts.length) {
                    textElement.textContent = loadingTexts[textIndex];
                } else {
                    clearInterval(loadingIntervalId);
                }
            } else {
                clearInterval(loadingIntervalId);
            }
        }, 2500);
    }

    function removeLoading() {
        if (loadingIntervalId) {
            clearInterval(loadingIntervalId);
            loadingIntervalId = null;
        }
        const loading = document.getElementById('chat-loading');
        if (loading) loading.remove();
    }

    function scrollToBottom() {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    async function sendMessage() {
        if (isWaitingForResponse) return;

        const message = chatInput.value.trim();
        if (!message) return;

        chatInput.value = '';
        chatInput.style.height = 'auto';
        chatSubmitBtn.disabled = true;
        isWaitingForResponse = true;

        renderUserMessage(message);
        renderLoading();

        try {
            const payload = { message: message };

            if (currentSessionId) {
                payload.session_id = currentSessionId;
            }

            // Attach selected source IDs
            if (window.WorkspaceSelection && typeof window.WorkspaceSelection.getSelectedSourceIds === 'function') {
                payload.source_ids = window.WorkspaceSelection.getSelectedSourceIds();
            }

            const response = await fetch(`/api/workspace/${workspaceId}/chat/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify(payload)
            });

            const data = await response.json();
            removeLoading();

            if (response.ok) {
                currentSessionId = data.session_id;
                renderBotMessage(data.response, data.sources);
                document.dispatchEvent(new CustomEvent('quotaUsed'));
            } else {
                renderBotMessage(`Error: ${data.detail || data.message || 'Terjadi kesalahan'}`);
            }
        } catch (error) {
            removeLoading();
            renderBotMessage('Gagal menghubungi server.');
        } finally {
            chatSubmitBtn.disabled = false;
            isWaitingForResponse = false;
            chatInput.focus();
            updateDeleteButtonState();
        }
    }

    async function loadChatHistory() {
        try {
            const response = await fetch(`/api/workspace/${workspaceId}/chat/sessions/`);
            if (!response.ok) {
                updateDeleteButtonState();
                return;
            }
            const sessions = await response.json();
            if (sessions.length === 0) {
                updateDeleteButtonState();
                return;
            }

            // Load the most recent session
            const activeSession = sessions[0];
            currentSessionId = activeSession.id;

            const msgsResponse = await fetch(`/api/chat/session/${currentSessionId}/messages/`);
            if (!msgsResponse.ok) {
                updateDeleteButtonState();
                return;
            }
            const messages = await msgsResponse.json();

 
            messagesContainer.innerHTML = '';
            messages.forEach(msg => {
                if (msg.role === 'user') {
                    renderUserMessage(msg.content);
                } else {
                    const sources = msg.metadata ? msg.metadata.sources : [];
                    renderBotMessage(msg.content, sources);
                }
            });
            renderEmptyState();
        } catch (err) {
            console.error("Gagal memuat histori chat:", err);
            renderEmptyState();
        } finally {
            updateDeleteButtonState();
        }
    }

    function checkSelection() {
        if (window.WorkspaceSelection && typeof window.WorkspaceSelection.getSelectedSourceIds === 'function') {
            const selectedIds = window.WorkspaceSelection.getSelectedSourceIds();
            const hasSelection = selectedIds.length > 0;
            
            chatInput.disabled = !hasSelection;
            chatSubmitBtn.disabled = !hasSelection || chatInput.value.trim().length === 0;
            
            if (!hasSelection) {
                chatInput.placeholder = "Pilih setidaknya 1 dokumen di panel sumber...";
            } else {
                chatInput.placeholder = "Tanya sesuatu...";
            }
        }
    }

    document.addEventListener('sourceSelectionChanged', () => {
        checkSelection();
    });

    // Auto-resize textarea
    chatInput.addEventListener('input', function () {
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 160) + 'px';
        checkSelection();
    });

    // Enter to send, Shift+Enter for newline
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    chatSubmitBtn.addEventListener('click', () => sendMessage());

    // Delete Chat UI Logic
    const btnDeleteChat = document.getElementById('btn-delete-chat');
    const deleteChatModal = document.getElementById('delete-chat-modal');
    const btnConfirmDeleteChat = document.getElementById('btn-confirm-delete-chat');
    const btnCancelDeleteChat = document.getElementById('btn-cancel-delete-chat');
    const btnCloseDeleteChatModal = document.getElementById('btn-close-delete-chat-modal');
    const deleteChatBackdrop = document.getElementById('delete-chat-backdrop');

    function updateDeleteButtonState() {
        if (btnDeleteChat) {
            if (!currentSessionId) {
                btnDeleteChat.disabled = true;
                btnDeleteChat.classList.add('opacity-50', 'cursor-not-allowed');
                btnDeleteChat.classList.remove('cursor-pointer');
            } else {
                btnDeleteChat.disabled = false;
                btnDeleteChat.classList.remove('opacity-50', 'cursor-not-allowed');
                btnDeleteChat.classList.add('cursor-pointer');
            }
        }
    }

    function showDeleteChatModal() {
        if (deleteChatModal) {
            deleteChatModal.classList.remove('hidden');
            deleteChatModal.classList.add('flex');
        }
    }

    function hideDeleteChatModal() {
        if (deleteChatModal) {
            deleteChatModal.classList.add('hidden');
            deleteChatModal.classList.remove('flex');
        }
    }

    if (btnDeleteChat) {
        btnDeleteChat.addEventListener('click', () => {
            if (!currentSessionId) return;
            showDeleteChatModal();
        });
    }

    if (btnCancelDeleteChat) btnCancelDeleteChat.addEventListener('click', hideDeleteChatModal);
    if (btnCloseDeleteChatModal) btnCloseDeleteChatModal.addEventListener('click', hideDeleteChatModal);
    if (deleteChatBackdrop) deleteChatBackdrop.addEventListener('click', hideDeleteChatModal);

    if (btnConfirmDeleteChat) {
        btnConfirmDeleteChat.addEventListener('click', async () => {
            hideDeleteChatModal();
            if (isWaitingForResponse) return;

            isWaitingForResponse = true;
            if (btnDeleteChat) {
                btnDeleteChat.disabled = true;
                btnDeleteChat.classList.add('opacity-50', 'cursor-not-allowed');
            }

            try {
                const response = await fetch(`/api/workspace/${workspaceId}/chat/messages/`, {
                    method: 'DELETE',
                    headers: {
                        'X-CSRFToken': getCsrfToken()
                    }
                });

                if (response.ok) {
                    currentSessionId = null;
                    messagesContainer.innerHTML = '';
                    renderEmptyState();
                    if (window.ToastManager) {
                        window.ToastManager.success('Riwayat chat berhasil dihapus.');
                    }
                } else {
                    const data = await response.json();
                    if (window.ToastManager) {
                        window.ToastManager.error(data.detail || data.message || 'Gagal menghapus chat.');
                    }
                }
            } catch (error) {
                console.error('Error deleting chat:', error);
                if (window.ToastManager) {
                    window.ToastManager.error('Gagal menghubungi server.');
                }
            } finally {
                isWaitingForResponse = false;
                updateDeleteButtonState();
            }
        });
    }

    // Load initial history
    loadChatHistory();
    renderEmptyState();
    setTimeout(() => { if (typeof checkSelection === 'function') checkSelection(); }, 100);
});
