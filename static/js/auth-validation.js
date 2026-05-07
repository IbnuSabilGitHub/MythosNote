document.addEventListener('DOMContentLoaded', () => {
    // Utility Debounce
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // Validation rules
    const rules = {
        email: (val) => {
            const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            return re.test(val) ? '' : 'Format email tidak valid';
        },
        password: (val) => {
            return val.length >= 6 ? '' : 'Password minimal 6 karakter';
        },
        username: (val) => {
            if (val.length < 3) return 'Username minimal 3 karakter';
            if (val.length > 20) return 'Username maksimal 20 karakter';
            return '';
        },
        password_confirm: (val, form) => {
            const pass = form.querySelector('input[name="password"]').value;
            return val === pass ? '' : 'Confirm password harus sama dengan password';
        }
    };

    // State tracking
    const errors = {};

    function showError(input, errorMsg) {
        // Find or create error container
        let errDiv = input.parentNode.querySelector('.js-error-msg');
        if (!errDiv) {
            errDiv = document.createElement('div');
            errDiv.className = 'js-error-msg flex items-start gap-2 self-stretch mt-2';
            errDiv.innerHTML = `
                <svg class="h-4 w-4 shrink-0 text-red-500 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />
                </svg>
                <span class="font-['Manrope'] text-xs font-normal text-red-500 error-text"></span>
            `;
            input.parentNode.appendChild(errDiv);
        }
        errDiv.querySelector('.error-text').textContent = errorMsg;
        errDiv.style.display = 'flex';
        
        // Update input styling (assumes outline-stone-700 ->  outline-red-500/50 replacement)
        input.classList.remove('outline-stone-700');
        input.classList.add('outline-red-500/50');
    }

    function clearError(input) {
        let errDiv = input.parentNode.querySelector('.js-error-msg');
        if (errDiv) {
            errDiv.style.display = 'none';
        }
        input.classList.remove('outline-red-500/50');
        input.classList.add('outline-stone-700');
    }

    function updateSubmitButton(form) {
        const btn = form.querySelector('button[type="submit"]');
        const hasErrors = Object.values(errors).some(v => v !== '');
        
        // Check if required fields are empty
        const inputs = Array.from(form.querySelectorAll('input[required]'));
        const isEmpty = inputs.some(i => i.value.trim() === '');
        
        if (hasErrors || isEmpty) {
            btn.disabled = true;
            btn.classList.add('opacity-50', 'cursor-not-allowed');
        } else {
            btn.disabled = false;
            btn.classList.remove('opacity-50', 'cursor-not-allowed');
        }
    }

    const forms = document.querySelectorAll('form[action*="signin"], form[action*="signup"]');

    forms.forEach(form => {
        const inputs = form.querySelectorAll('input[name]');

        form.addEventListener('submit', () => {
            inputs.forEach(input => {
                if (input.type !== 'password') {
                    input.value = input.value.trim();
                }
            });
        });
        
        inputs.forEach(input => {
            input.addEventListener('blur', () => {
                if (input.type !== 'password') {
                    input.value = input.value.trim();
                }
            });

            const name = input.name;
            // Map input name to rule
            let ruleKey = name;
            if (name === 'username' && form.action.includes('signin')) {
                // Ignore username pattern on signin if it can be email or username, just check not empty
                ruleKey = null; 
            }

            if (ruleKey && rules[ruleKey]) {
                const validate = () => {
                    const val = input.value;
                    if (val === '') {
                        clearError(input);
                        errors[name] = '';
                    } else {
                        const errMsg = rules[ruleKey](val, form);
                        errors[name] = errMsg;
                        if (errMsg) {
                            showError(input, errMsg);
                        } else {
                            clearError(input);
                        }
                    }
                    updateSubmitButton(form);
                };

                const debouncedValidate = debounce(validate, 400);

                input.addEventListener('input', (e) => {
                    if (name === 'password_confirm') {
                        // Confirm password: only validate immediately if length >= 8, otherwise don't show error yet
                        if (e.target.value.length >= 8) {
                            debouncedValidate();
                        } else {
                            // Still clears errors if it becomes valid or empty but won't eagerly validate small strings
                            clearError(input);
                            errors[name] = '';
                            updateSubmitButton(form);
                            // Set internal error state so submit stays disabled
                            const errMsg = rules[ruleKey](e.target.value, form);
                            if (errMsg) errors[name] = errMsg; 
                        }
                    } else {
                        debouncedValidate();
                    }
                    // For requiredness check during typing
                    setTimeout(() => updateSubmitButton(form), 10);
                });

                input.addEventListener('blur', validate);
            } else {
                // Just for required field submit button toggle
                input.addEventListener('input', () => updateSubmitButton(form));
            }
        });

        // Initial check
        updateSubmitButton(form);
    });
});
