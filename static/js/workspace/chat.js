import { marked } from "marked";

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

    let currentSessionId = null;
    let isWaitingForResponse = false;

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
        msgDiv.innerHTML = `
            <div class="max-w-[85%] inline-flex justify-end items-start">
                <div class="self-stretch pl-4 pr-6 py-4 bg-primary/15 rounded-2xl rounded-tr-md border border-primary/30 inline-flex flex-col justify-start items-start shadow-[0_12px_40px_rgba(0,0,0,0.18)]">
                    <div class="text-zinc-200 text-base font-normal font-['Manrope'] leading-6 whitespace-pre-wrap">${escapeHtml(text)}</div>
                </div>
            </div>
        `;
        messagesContainer.appendChild(msgDiv);
        scrollToBottom();
    }

    function renderBotMessage(text, sources) {
        const msgDiv = document.createElement('div');
        clearEmptyState();
        msgDiv.className = 'w-full max-w-3xl inline-flex justify-start items-start gap-3 sm:gap-4 animate-slide-up';

        let sourcesHtml = '';
        if (sources && sources.length > 0) {
            sourcesHtml = '<div class="mt-2 pt-2 border-t border-neutral-800 text-xs text-stone-400">Sumber: ' +
                sources.map(s => `<span class="text-primary">${escapeHtml(s.original_filename)}</span>`).join(', ') +
                '</div>';
        }

        const renderedMarkdown = marked.parse(text);

        msgDiv.innerHTML = `
            <div class="w-8 h-9 pt-1 inline-flex flex-col justify-start items-start shrink-0">
                <div class="w-8 h-8 bg-neutral-900 rounded-xl outline -outline-offset-1 outline-neutral-800 inline-flex justify-center items-center">
                    <img class="h-5 w-5" src="/static/svg/deepseek-logo.svg" alt="DeepSeek AI Logo" />
                </div>
            </div>
            <div class="flex-1 px-4 pt-3.5 pb-4 bg-neutral-900/70 rounded-2xl border border-neutral-800 inline-flex flex-col justify-start items-start gap-4">
                <div class="self-stretch flex flex-col justify-start items-start gap-1.5">
                    <div class="chat-markdown">${renderedMarkdown}</div>
                    ${sourcesHtml}
                </div>
            </div>
        `;
        messagesContainer.appendChild(msgDiv);
        scrollToBottom();
    }

    function renderLoading() {
        const msgDiv = document.createElement('div');
        msgDiv.id = 'chat-loading';
        clearEmptyState();
        msgDiv.className = 'w-full max-w-3xl inline-flex justify-start items-start gap-3 sm:gap-4';
        msgDiv.innerHTML = `
            <div class="w-8 h-9 pt-1 inline-flex flex-col justify-start items-start shrink-0">
                <div class="w-8 h-8 bg-neutral-900 rounded-xl outline -outline-offset-1 outline-neutral-800 inline-flex justify-center items-center">
                    <img class="h-5 w-5" src="/static/svg/deepseek-logo.svg" alt="DeepSeek AI Logo" />
                </div>
            </div>
            <div class="min-w-0 flex-1 px-4 pt-3.5 pb-4 bg-neutral-900/70 rounded-2xl border border-neutral-800 inline-flex flex-col justify-start items-start gap-3 animate-pulse">
                <div class="h-3.5 bg-neutral-800 rounded w-1/4"></div>
                <div class="h-3.5 bg-neutral-800/80 rounded w-2/3"></div>
            </div>
        `;
        messagesContainer.appendChild(msgDiv);
        scrollToBottom();
    }

    function removeLoading() {
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
        }
    }

    async function loadChatHistory() {
        try {
            const response = await fetch(`/api/workspace/${workspaceId}/chat/sessions/`);
            if (!response.ok) return;
            const sessions = await response.json();
            if (sessions.length === 0) return;

            // Load the most recent session
            const activeSession = sessions[0];
            currentSessionId = activeSession.id;

            const msgsResponse = await fetch(`/api/chat/session/${currentSessionId}/messages/`);
            if (!msgsResponse.ok) return;
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

    // Load initial history
    loadChatHistory();
    renderEmptyState();
    setTimeout(() => { if (typeof checkSelection === 'function') checkSelection(); }, 100);
});
