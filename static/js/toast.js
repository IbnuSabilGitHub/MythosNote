/**
 * ToastManager - Lightweight Toast Notification System
 * Manages toast lifecycle: show, stack, auto-dismiss, animations
 */
class ToastManager {
    static DEFAULT_DURATION = 5000; // 5 seconds
    static ACTION_DURATION = 0; // No auto-dismiss for action toasts

    static typeConfig = {
        success: {
            iconClass: 'text-green-500',
            borderClass: 'border-green-500/30',
            bgClass: 'bg-green-500/10',
        },
        error: {
            iconClass: 'text-red-500',
            borderClass: 'border-red-500/30',
            bgClass: 'bg-red-500/10',
        },
        warning: {
            iconClass: 'text-yellow-500',
            borderClass: 'border-yellow-500/30',
            bgClass: 'bg-yellow-500/10',
        },
        info: {
            iconClass: 'text-blue-500',
            borderClass: 'border-blue-500/30',
            bgClass: 'bg-blue-500/10',
        },
        delete: {
            iconClass: 'text-red-500',
            borderClass: 'border-red-500/30',
            bgClass: 'bg-red-500/10',
        },
    };

    static iconPaths = {
        success: 'M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z',
        error: 'M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z',
        warning: 'M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z',
        info: 'M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z',
    };

    /**
     * Show a toast notification
     * @param {string} type - Type: success, error, warning, info
     * @param {string} message - Toast message
     * @param {number} duration - Auto-dismiss duration (ms), 0 = no auto-dismiss
     */
    static show(type = 'info', message = '', duration = null) {
        if (!message) return;

        const config = this.typeConfig[type] || this.typeConfig.info;
        const template = document.getElementById('toast-template');
        const container = document.getElementById('toast-container');

        if (!template || !container) return;

        const toast = template.content.cloneNode(true);
        const toastElement = toast.querySelector('.toast-item');
        const iconElement = toast.querySelector('.toast-icon');
        const messageElement = toast.querySelector('.toast-message');
        const closeButton = toast.querySelector('.toast-close');

        // Set colors
        toastElement.classList.add(config.borderClass, config.bgClass);
        iconElement.classList.add(config.iconClass);
        iconElement.innerHTML = `<path fill-rule="evenodd" d="${this.iconPaths[type] || this.iconPaths.info}" clip-rule="evenodd" />`;

        messageElement.textContent = message;

        container.appendChild(toast);
        const toastNode = container.lastElementChild;

        // Close handler
        const handleClose = () => {
            this.dismiss(toastNode);
        };

        closeButton.addEventListener('click', handleClose);

        // Auto-dismiss
        const autoDismissDuration = duration !== null ? duration : this.DEFAULT_DURATION;
        if (autoDismissDuration > 0) {
            setTimeout(handleClose, autoDismissDuration);
        }

        return toastNode;
    }

    /**
     * Show confirmation toast with action buttons
     * @param {Object} options - Configuration
     *   - type: string (success, error, warning, info, delete)
     *   - title: string
     *   - message: string
     *   - confirmText: string (default: "Konfirmasi")
     *   - cancelText: string (default: "Batal")
     *   - onConfirm: function - called when confirm clicked
     *   - onCancel: function - called when cancel clicked
     */
    static showAction(options = {}) {
        const {
            type = 'info',
            title = '',
            message = '',
            confirmText = 'Konfirmasi',
            cancelText = 'Batal',
            onConfirm = null,
            onCancel = null,
        } = options;

        const config = this.typeConfig[type] || this.typeConfig.info;
        const template = document.getElementById('toast-action-template');
        const container = document.getElementById('toast-container');

        if (!template || !container) return;

        const toast = template.content.cloneNode(true);
        const toastElement = toast.querySelector('.toast-action-item');
        const iconElement = toast.querySelector('.toast-action-icon');
        const titleElement = toast.querySelector('.toast-action-title');
        const messageElement = toast.querySelector('.toast-action-message');
        const cancelButton = toast.querySelector('.toast-action-cancel');
        const confirmButton = toast.querySelector('.toast-action-confirm');

        // Set colors
        toastElement.classList.add(config.borderClass, config.bgClass);
        iconElement.classList.add(config.iconClass);
        iconElement.innerHTML = `<path fill-rule="evenodd" d="${this.iconPaths[type] || this.iconPaths.info}" clip-rule="evenodd" />`;

        titleElement.textContent = title;
        messageElement.textContent = message;
        cancelButton.textContent = cancelText;
        confirmButton.textContent = confirmText;

        container.appendChild(toast);
        const toastNode = container.lastElementChild;

        // Handle cancel
        cancelButton.addEventListener('click', () => {
            if (onCancel) onCancel();
            this.dismiss(toastNode);
        });

        // Handle confirm
        confirmButton.addEventListener('click', () => {
            if (onConfirm) onConfirm();
            this.dismiss(toastNode);
        });

        return toastNode;
    }

    /**
     * Dismiss a specific toast
     * @param {Element} element - Toast element to dismiss
     */
    static dismiss(element) {
        if (!element) return;

        element.classList.add('animate-slide-out-left');
        setTimeout(() => {
            if (element.parentNode) {
                element.parentNode.removeChild(element);
            }
        }, 300); // Match animation duration
    }

    /**
     * Dismiss all toasts
     */
    static dismissAll() {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const toasts = container.querySelectorAll('.toast-item, .toast-action-item');
        toasts.forEach(toast => this.dismiss(toast));
    }

    // Shorthand methods
    static success(message, duration = null) {
        return this.show('success', message, duration);
    }

    static error(message, duration = null) {
        return this.show('error', message, duration);
    }

    static warning(message, duration = null) {
        return this.show('warning', message, duration);
    }

    static info(message, duration = null) {
        return this.show('info', message, duration);
    }

    /**
     * Show confirmation dialog
     * @param {string} message - Confirmation message
     * @param {function} onConfirm - Callback on confirm
     * @param {Object} options - Additional options (title, confirmText, cancelText)
     */
    static confirm(message, onConfirm, options = {}) {
        return this.showAction({
            type: options.type || 'info',
            title: options.title || 'Konfirmasi',
            message: message,
            confirmText: options.confirmText || 'Konfirmasi',
            cancelText: options.cancelText || 'Batal',
            onConfirm: onConfirm,
            onCancel: options.onCancel || null,
        });
    }

    /**
     * Show delete confirmation
     * @param {string} itemName - Name of item to delete
     * @param {function} onConfirm - Callback on confirm
     */
    static delete(itemName, onConfirm) {
        return this.showAction({
            type: 'delete',
            title: 'Hapus Item',
            message: `Yakin hapus "${itemName}"? Aksi ini tidak bisa dibatalkan.`,
            confirmText: 'Hapus',
            cancelText: 'Batal',
            onConfirm: onConfirm,
        });
    }
}

// Auto-initialize on DOM ready
document.addEventListener('DOMContentLoaded', function() {
    window.ToastManager = ToastManager;
});
