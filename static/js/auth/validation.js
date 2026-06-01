document.addEventListener('DOMContentLoaded', () => {
    // Utility Functions
    const debounce = (func, wait) => {
        let timeout;
        return (...args) => {
            clearTimeout(timeout);
            timeout = setTimeout(() => func(...args), wait);
        };
    };

    // Constants & Configuration
    const VALIDATION_RULES = {
        email: (value) => {
            if (value.length > 254) return 'Email maksimal 254 karakter';
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            return emailRegex.test(value) ? '' : 'Format email tidak valid';
        },
        password: (value) => {
            if (value.length < 8) return 'Password minimal 8 karakter';
            if (value.length > 128) return 'Password maksimal 128 karakter';
            return '';
        },
        password_confirm: (value, form, input) => {
            const passwordFieldName = input.dataset.matchPassword || 'password';
            const passwordInput = form.querySelector(`input[name="${passwordFieldName}"]`);
            const password = passwordInput ? passwordInput.value : '';
            return value === password ? '' : 'Confirm password harus sama dengan password';
        }
    };

    const ERROR_CLASS = 'outline-red-500/50';
    const DEFAULT_CLASS = 'outline-stone-700';
    const DISABLED_CLASSES = ['opacity-50', 'cursor-not-allowed'];

    // Error UI Management
    const createErrorElement = () => {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'js-error-msg flex items-start gap-2 self-stretch mt-2';
        errorDiv.innerHTML = `
            <svg class="h-4 w-4 shrink-0 text-red-500 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />
            </svg>
            <span class="font-['Manrope'] text-xs font-normal text-red-500 error-text"></span>
        `;
        return errorDiv;
    };

    const findOrCreateErrorElement = (input) => {
        let errorElement = input.parentNode.querySelector('.js-error-msg');
        if (!errorElement) {
            errorElement = createErrorElement();
            input.parentNode.appendChild(errorElement);
        }
        return errorElement;
    };

    const showError = (input, errorMessage) => {
        const errorElement = findOrCreateErrorElement(input);
        errorElement.querySelector('.error-text').textContent = errorMessage;
        errorElement.style.display = 'flex';
        
        input.classList.remove(DEFAULT_CLASS);
        input.classList.add(ERROR_CLASS);
    };

    const clearError = (input) => {
        const errorElement = input.parentNode.querySelector('.js-error-msg');
        if (errorElement) {
            errorElement.style.display = 'none';
        }
        
        input.classList.remove(ERROR_CLASS);
        input.classList.add(DEFAULT_CLASS);
    };

    // Form State Management
    const createFormState = () => ({
        errors: {},
        
        setError(fieldName, errorMessage) {
            this.errors[fieldName] = errorMessage;
        },
        
        clearError(fieldName) {
            this.errors[fieldName] = '';
        },
        
        hasErrors() {
            return Object.values(this.errors).some(value => value !== '');
        },
        
        isSubmittable() {
            return !this.hasErrors();
        }
    });

    const updateSubmitButton = (form, formState) => {
        const submitButton = form.querySelector('button[type="submit"]');
        if (!submitButton) return;

        const requiredInputs = form.querySelectorAll('input[required]');
        const hasEmptyRequired = Array.from(requiredInputs).some(input => input.value.trim() === '');
        
        const shouldDisable = formState.hasErrors() || hasEmptyRequired;
        
        submitButton.disabled = shouldDisable;
        
        if (shouldDisable) {
            submitButton.classList.add(...DISABLED_CLASSES);
        } else {
            submitButton.classList.remove(...DISABLED_CLASSES);
        }
    };

    const trimNonPasswordInputs = (inputs) => {
        inputs.forEach(input => {
            if (input.type !== 'password') {
                input.value = input.value.trim();
            }
        });
    };

    // Input Validation Logic
    const validateInput = (input, form, formState) => {
        const fieldName = input.name;
        const value = input.value;
        
        if (value === '') {
            clearError(input);
            formState.clearError(fieldName);
            return;
        }

        const ruleKey = getRuleKey(fieldName, form, input);
        if (!ruleKey || !VALIDATION_RULES[ruleKey]) return;

        const errorMessage = VALIDATION_RULES[ruleKey](value, form, input);
        formState.setError(fieldName, errorMessage);

        if (errorMessage) {
            showError(input, errorMessage);
        } else {
            clearError(input);
        }
    };

    const getRuleKey = (fieldName, form, input = null) => {
        if (input && input.dataset.validationRule) {
            return input.dataset.validationRule;
        }

        if (fieldName === 'new_password1') {
            return 'password';
        }
        if (fieldName === 'new_password2') {
            return 'password_confirm';
        }
        return fieldName;
    };

    const handlePasswordConfirmInput = (input, form, formState, debouncedValidate) => {
        const value = input.value;
        
        if (value.length >= 8) {
            debouncedValidate();
        } else {
            clearError(input);
            formState.clearError(input.name);
            updateSubmitButton(form, formState);
            
            // Still check for errors to maintain disabled state
            const errorMessage = VALIDATION_RULES.password_confirm(value, form, input);
            if (errorMessage) {
                formState.setError(input.name, errorMessage);
            }
        }
    };

    // Form Initialization
    const setupFormValidation = (form) => {
        const formState = createFormState();
        const inputs = form.querySelectorAll('input[name]');
        
        // Trim non-password inputs on submit and blur
        form.addEventListener('submit', () => trimNonPasswordInputs(inputs));
        
        inputs.forEach(input => {
            if (input.type !== 'password') {
                input.addEventListener('blur', () => {
                    input.value = input.value.trim();
                });
            }

            setupInputValidation(input, form, formState);
        });

        // Initial button state check
        updateSubmitButton(form, formState);
    };

    const setupInputValidation = (input, form, formState) => {
        const fieldName = input.name;
        const ruleKey = getRuleKey(fieldName, form, input);
        
        if (!ruleKey || !VALIDATION_RULES[ruleKey]) {
            // Input without validation rules - just track for button state
            input.addEventListener('input', () => updateSubmitButton(form, formState));
            return;
        }

        const validate = () => {
            validateInput(input, form, formState);
            updateSubmitButton(form, formState);
        };

        const debouncedValidate = debounce(validate, 400);

        input.addEventListener('input', (event) => {
            if (fieldName === 'password_confirm') {
                handlePasswordConfirmInput(input, form, formState, debouncedValidate);
            } else {
                debouncedValidate();
            }
            
            // Immediate check for required fields during typing
            setTimeout(() => updateSubmitButton(form, formState), 10);
        });

        input.addEventListener('blur', validate);
    };

    // Application Entry Point
    const initialize = () => {
        const authForms = document.querySelectorAll(
            'form[action*="signin"], form[action*="signup"], form[data-auth-kind="password-reset-confirm"]'
        );
        authForms.forEach(setupFormValidation);
    };

    initialize();
});
