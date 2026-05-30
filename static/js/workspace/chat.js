/**
 * Handle workspace chat interactions
 * Tahap 5 & 6: Dynamic chat + source selection filter
 */

document.addEventListener('DOMContentLoaded', () => {
    const workspaceData = document.getElementById('workspace-data');
    if (!workspaceData) return;

    const workspaceId = workspaceData.dataset.workspaceId;
    const chatInput = document.getElementById('chat-input');
    const chatSubmitBtn = document.getElementById('chat-submit-btn');
    const messagesContainer = document.getElementById('chat-messages-container');

    let currentSessionId = null;
    let isWaitingForResponse = false;

    function getCsrfToken() {
        const cookieValue = document.cookie.match(/(?:^|;)\s*csrftoken=([^;]+)/);
        return cookieValue ? cookieValue[1] : '';
    }

    function escapeHtml(unsafe) {
        return (unsafe || '').toString()
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function renderUserMessage(text) {
        const msgDiv = document.createElement('div');
        msgDiv.className = 'w-full max-w-3xl self-end flex flex-col justify-start items-end';
        msgDiv.innerHTML = `
            <div class="max-w-[85%] inline-flex justify-end items-start">
                <div class="self-stretch pl-4 pr-6 py-4 bg-[#FFC880]/15 rounded-2xl rounded-tr-md border border-[#FFC880]/30 inline-flex flex-col justify-start items-start">
                    <div class="text-zinc-200 text-base font-normal font-['Manrope'] leading-6 whitespace-pre-wrap">${escapeHtml(text)}</div>
                </div>
            </div>
        `;
        messagesContainer.appendChild(msgDiv);
        scrollToBottom();
    }

    function renderBotMessage(text, sources) {
        const msgDiv = document.createElement('div');
        msgDiv.className = 'w-full max-w-3xl inline-flex justify-start items-start gap-4';

        let sourcesHtml = '';
        if (sources && sources.length > 0) {
            sourcesHtml = '<div class="mt-2 pt-2 border-t border-neutral-800 text-xs text-stone-400">Sumber: ' +
                sources.map(s => `<span class="text-[#FFC880]">${escapeHtml(s.original_filename)}</span>`).join(', ') +
                '</div>';
        }

        msgDiv.innerHTML = `
            <div class="w-8 h-9 pt-1 inline-flex flex-col justify-start items-start shrink-0">
                <div class="w-8 h-8 bg-neutral-900 rounded-xl outline -outline-offset-1 outline-neutral-800 inline-flex justify-center items-center">
                    <iconify-icon icon="tabler:robot" class="text-stone-300"></iconify-icon>
                </div>
            </div>
            <div class="flex-1 px-4 pt-3.5 pb-4 bg-neutral-900/70 rounded-2xl border border-neutral-800 inline-flex flex-col justify-start items-start gap-4">
                <div class="self-stretch flex flex-col justify-start items-start gap-1.5">
                    <div class="text-zinc-200 text-sm font-normal font-['Space_Grotesk'] leading-6 tracking-tight whitespace-pre-wrap">${escapeHtml(text)}</div>
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
        msgDiv.className = 'w-full max-w-3xl inline-flex justify-start items-start gap-4';
        msgDiv.innerHTML = `
            <div class="w-8 h-9 pt-1 inline-flex flex-col justify-start items-start shrink-0">
                <div class="w-8 h-8 bg-neutral-900 rounded-xl outline -outline-offset-1 outline-neutral-800 inline-flex justify-center items-center">
                    <iconify-icon icon="tabler:robot" class="text-stone-300"></iconify-icon>
                </div>
            </div>
            <div class="flex-1 px-4 pt-3.5 pb-4 bg-neutral-900/70 rounded-2xl border border-neutral-800 inline-flex flex-col justify-start items-start gap-4 animate-pulse">
                <div class="h-4 bg-neutral-800 rounded w-1/4"></div>
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

            // Tahap 6: attach selected source IDs (empty = all ready sources)
            if (window.WorkspaceSelection && typeof window.WorkspaceSelection.getSelectedSourceIds === 'function') {
                const selectedIds = window.WorkspaceSelection.getSelectedSourceIds();
                if (selectedIds.length > 0) {
                    payload.source_ids = selectedIds;
                }
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

    // Auto-resize textarea
    chatInput.addEventListener('input', function () {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
        chatSubmitBtn.disabled = this.value.trim().length === 0 || isWaitingForResponse;
    });

    // Enter to send, Shift+Enter for newline
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    chatSubmitBtn.addEventListener('click', () => sendMessage());
});
