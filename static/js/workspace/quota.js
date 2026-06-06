/**
 * Workspace Quota Monitor
 * Fetch kuota AI harian, tampilkan badge di header + popover detail.
 * Re-fetch otomatis setelah event chat/generate/upload berhasil.
 */

document.addEventListener('DOMContentLoaded', () => {
    const badge = document.getElementById('quota-badge-btn');
    const badgeLabel = document.getElementById('quota-badge-label');
    const badgeIcon = document.getElementById('quota-badge-icon');
    const popover = document.getElementById('quota-popover');

    const promptLabel = document.getElementById('quota-prompt-label');
    const promptBar = document.getElementById('quota-prompt-bar');
    const generateLabel = document.getElementById('quota-generate-label');
    const generateBar = document.getElementById('quota-generate-bar');
    const uploadLabel = document.getElementById('quota-upload-label');
    const uploadBar = document.getElementById('quota-upload-bar');

    if (!badge) return;

    // ─── Colour helpers ───────────────────────────────────────────────────────

    /**
     * Returns Tailwind class for progress bar fill colour based on usage %.
     */
    function barColour(pct) {
        if (pct >= 90) return 'bg-red-500';
        if (pct >= 70) return 'bg-yellow-400';
        return 'bg-primary';
    }

    /**
     * Returns Tailwind class for label text colour.
     */
    function labelColour(pct) {
        if (pct >= 90) return 'text-red-400';
        if (pct >= 70) return 'text-yellow-400';
        return 'text-stone-400';
    }

    /**
     * Returns the worst pct across all quota types to drive badge colour.
     */
    function worstPct(...pcts) {
        return Math.max(...pcts);
    }

    // ─── Apply quota data to DOM ──────────────────────────────────────────────

    function applyQuota(quota) {
        const { prompt, generate, upload } = quota;

        // Badge text — show remaining prompts (most-used resource)
        badgeLabel.textContent = `${prompt.remaining} chat`;

        // Badge colour based on worst metric
        const worst = worstPct(prompt.pct, generate.pct, upload.pct);
        badge.classList.remove('text-stone-400', 'text-yellow-400', 'text-red-400', 'border-neutral-800/80', 'border-yellow-500/30', 'border-red-500/30');
        if (worst >= 90) {
            badge.classList.add('text-red-400', 'border-red-500/30');
            badgeIcon.setAttribute('icon', 'tabler:bolt-off');
        } else if (worst >= 70) {
            badge.classList.add('text-yellow-400', 'border-yellow-500/30');
            badgeIcon.setAttribute('icon', 'tabler:bolt');
        } else {
            badge.classList.add('text-stone-400', 'border-neutral-800/80');
            badgeIcon.setAttribute('icon', 'tabler:bolt');
        }

        // Show badge (initially hidden)
        badge.classList.remove('hidden');
        badge.classList.add('inline-flex');

        // Prompt row
        promptLabel.textContent = `${prompt.used}/${prompt.limit}`;
        promptLabel.className = `font-manrope text-xs font-semibold ${labelColour(prompt.pct)}`;
        promptBar.style.width = `${prompt.pct}%`;
        promptBar.className = `h-full rounded-full transition-all duration-500 ${barColour(prompt.pct)}`;

        // Generate row
        generateLabel.textContent = `${generate.used}/${generate.limit}`;
        generateLabel.className = `font-manrope text-xs font-semibold ${labelColour(generate.pct)}`;
        generateBar.style.width = `${generate.pct}%`;
        generateBar.className = `h-full rounded-full transition-all duration-500 ${barColour(generate.pct)}`;

        // Upload row
        uploadLabel.textContent = `${upload.used}/${upload.limit}`;
        uploadLabel.className = `font-manrope text-xs font-semibold ${labelColour(upload.pct)}`;
        uploadBar.style.width = `${upload.pct}%`;
        uploadBar.className = `h-full rounded-full transition-all duration-500 ${barColour(upload.pct)}`;
        
        // Dynamic reset time
        const resetTextEl = document.getElementById('quota-reset-text');
        if (resetTextEl && quota.reset_at) {
            try {
                const date = new Date(quota.reset_at);
                const timeString = date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
                
                const timeZoneName = Intl.DateTimeFormat('id-ID', { timeZoneName: 'short' })
                    .formatToParts(date)
                    .find(part => part.type === 'timeZoneName')?.value;
                    
                let tz = timeZoneName || '';
                if (tz.includes('WIB')) tz = 'WIB';
                else if (tz.includes('WITA')) tz = 'WITA';
                else if (tz.includes('WIT')) tz = 'WIT';
                else if (tz.includes('GMT') || tz.includes('UTC')) {
                    // keep as is
                } else {
                    const offset = -date.getTimezoneOffset();
                    const sign = offset >= 0 ? '+' : '-';
                    const offsetHours = Math.floor(Math.abs(offset) / 60);
                    tz = `GMT${sign}${offsetHours}`;
                }
                const hours = String(date.getHours()).padStart(2, '0');
                const minutes = String(date.getMinutes()).padStart(2, '0');
                resetTextEl.textContent = `Reset otomatis pada pukul ${hours}.${minutes} ${tz}`;
            } catch (e) {
                console.error('Failed to parse reset date:', e);
            }
        }
    }

    // ─── Fetch quota from API ─────────────────────────────────────────────────

    async function fetchQuota() {
        try {
            const res = await fetch('/api/quota/');
            if (!res.ok) return;
            const data = await res.json();
            applyQuota(data);
        } catch (err) {
            console.error('Gagal memuat kuota:', err);
        }
    }

    // ─── Popover toggle ───────────────────────────────────────────────────────

    let popoverOpen = false;

    function openPopover() {
        popover.classList.remove('hidden');
        badge.setAttribute('aria-expanded', 'true');
        popoverOpen = true;
    }

    function closePopover() {
        popover.classList.add('hidden');
        badge.setAttribute('aria-expanded', 'false');
        popoverOpen = false;
    }

    badge.addEventListener('click', (e) => {
        e.stopPropagation();
        if (popoverOpen) {
            closePopover();
        } else {
            openPopover();
        }
    });

    document.addEventListener('click', (e) => {
        if (popoverOpen && !popover.contains(e.target) && e.target !== badge) {
            closePopover();
        }
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && popoverOpen) closePopover();
    });

    // ─── Re-fetch after AI actions ────────────────────────────────────────────

    // Listen for custom events dispatched by chat.js / generate/index.js
    document.addEventListener('quotaUsed', () => {
        fetchQuota();
    });

    // ─── Initial fetch ────────────────────────────────────────────────────────

    fetchQuota();
});
