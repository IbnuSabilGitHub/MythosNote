document.addEventListener('DOMContentLoaded', () => {
	const LOADING_BUTTON_SELECTOR = 'button[data-loading-button]';
	const LOADING_DISABLED_CLASSES = ['opacity-70', 'cursor-not-allowed'];
	const LOADING_SPINNER_SVG = `
		<svg class="h-4 w-4 shrink-0 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden="true">
			<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3"></circle>
			<path class="opacity-75" fill="currentColor" d="M12 2a10 10 0 0 1 10 10h-3a7 7 0 1 0-7 7v3A10 10 0 0 1 12 2Z"></path>
		</svg>
	`;

	const setButtonLoadingState = (button, isLoading) => {
		if (!button) return;

		if (button.dataset.originalHtml === undefined) {
			button.dataset.originalHtml = button.innerHTML;
		}

		if (isLoading) {
			const loadingLabel = button.dataset.loadingText || button.textContent.trim() || 'Memproses';
			button.disabled = true;
			button.setAttribute('aria-busy', 'true');
			button.innerHTML = `
				<span class="inline-flex items-center justify-center gap-2">
					${LOADING_SPINNER_SVG}
					<span>${loadingLabel}</span>
				</span>
			`;
			button.classList.add(...LOADING_DISABLED_CLASSES);
			return;
		}

		button.disabled = false;
		button.removeAttribute('aria-busy');
		button.innerHTML = button.dataset.originalHtml || button.innerHTML;
		button.classList.remove(...LOADING_DISABLED_CLASSES);
	};

	const getLoadingButton = (form, submitter) => {
		if (submitter instanceof HTMLButtonElement && submitter.matches(LOADING_BUTTON_SELECTOR)) {
			return submitter;
		}

		return form.querySelector(`${LOADING_BUTTON_SELECTOR}[type="submit"]`);
	};

	const setupLoadingButton = (button) => {
		if (button.dataset.loadingSetup === 'true') return;
		button.dataset.loadingSetup = 'true';

		const resetState = () => setButtonLoadingState(button, false);
		button.addEventListener('blur', resetState);
	};

	const initializeLoadingButtons = () => {
		document.querySelectorAll(LOADING_BUTTON_SELECTOR).forEach(setupLoadingButton);

		document.querySelectorAll('form').forEach((form) => {
			form.addEventListener('submit', (event) => {
				const loadingButton = getLoadingButton(form, event.submitter);
				if (!loadingButton) return;

				window.setTimeout(() => {
					if (!event.defaultPrevented) {
						setButtonLoadingState(loadingButton, true);
					}
				}, 0);
			});
		});
	};

	initializeLoadingButtons();
});
