/**
 * Django Messages Integration with ToastManager
 * Displays Django messages framework notifications via toast system
 */

document.addEventListener('DOMContentLoaded', function() {
    // Check if messages were passed from Django template
    if (typeof window.djangoMessages !== 'undefined' && window.djangoMessages.length > 0) {
        window.djangoMessages.forEach(msg => {
            const type = msg.tags || 'info';
            const text = msg.text || '';
            
            if (text && window.ToastManager && typeof window.ToastManager[type] === 'function') {
                window.ToastManager[type](text);
            }
        });
    }
});
