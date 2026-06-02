import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import fs from 'fs';
import path from 'path';

// Load scripts into jsdom
function loadScript(filepath) {
    const code = fs.readFileSync(path.resolve(process.cwd(), filepath), 'utf8');
    // Using eval to run inside the jsdom environment
    window.eval(code);
}

describe('Core DOM (dom.js)', () => {
    beforeEach(() => {
        window.MythosDom = undefined;
        loadScript('static/js/core/dom.js');
    });

    it('should escape HTML characters correctly', () => {
        const { escapeHtml } = window.MythosDom;
        expect(escapeHtml('<div>&"\'</div>')).toBe('&lt;div&gt;&amp;&quot;&#039;&lt;/div&gt;');
        expect(escapeHtml('')).toBe('');
        expect(escapeHtml(null)).toBe('');
    });
});

describe('Core API (api.js)', () => {
    beforeEach(() => {
        window.MythosApi = undefined;
        window.MythosCsrf = { getCsrfToken: () => 'test-csrf-token' };
        loadScript('static/js/core/api.js');
        vi.stubGlobal('fetch', vi.fn());
    });

    afterEach(() => {
        vi.unstubAllGlobals();
    });

    it('should attach CSRF token to headers', async () => {
        const { apiFetch } = window.MythosApi;
        fetch.mockResolvedValueOnce({
            ok: true,
            status: 200,
            json: async () => ({ success: true })
        });

        await apiFetch('/test');

        expect(fetch).toHaveBeenCalledWith('/test', expect.objectContaining({
            headers: expect.objectContaining({
                'X-CSRFToken': 'test-csrf-token'
            })
        }));
    });

    it('should parse response error correctly', async () => {
        const { apiFetch } = window.MythosApi;
        fetch.mockResolvedValueOnce({
            ok: false,
            status: 400,
            json: async () => ({ detail: 'Bad Request Detail' })
        });

        await expect(apiFetch('/test')).rejects.toThrow('Bad Request Detail');
    });
});
