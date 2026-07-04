/**
 * Reusable functions for admin CRUD operations
 */

class AdminUtils {
    /**
     * Read the CSRF token rendered by the template's <meta name="csrf-token">.
     * Returns empty string if the meta tag is missing (will then fail server-side
     * CSRF check, which is the correct behavior — never silently bypass CSRF).
     */
    static getCsrfToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') || '' : '';
    }

    /**
     * Ensure form data carries the CSRF token. Works for FormData and URLSearchParams.
     * Mirrors the server check at app.py:_csrf_is_valid() which accepts the token
     * in the form field '_csrf_token', JSON body '_csrf', or X-CSRF-Token header.
     */
    static stampCsrf(body) {
        const token = this.getCsrfToken();
        if (!token) return body;
        if (body instanceof FormData) {
            // Don't overwrite if the form already supplied one.
            if (!body.has('_csrf_token')) body.append('_csrf_token', token);
        } else if (body && typeof body === 'object' && !(body instanceof URLSearchParams)) {
            body._csrf = token;
        }
        return body;
    }

    static async fetchWithAuth(url, options = {}) {
        try {
            const csrfToken = this.getCsrfToken();
            const headers = {
                'X-Requested-With': 'XMLHttpRequest',
                ...(options.headers || {}),
            };
            // HIGH-11 fix: every state-changing request must carry the CSRF token.
            // Send as header (covers JSON / fetch). Form-encoded bodies are stamped
            // separately below via stampCsrf() so the server's _csrf_is_valid() check
            // finds '_csrf_token' in request.form.
            if (csrfToken && options.method && options.method.toUpperCase() !== 'GET') {
                headers['X-CSRF-Token'] = csrfToken;
            }
            if (options.body && !(options.body instanceof FormData)) {
                headers['Content-Type'] = headers['Content-Type'] || 'application/json';
            }
            const response = await fetch(url, { ...options, headers });
            if (!response.ok) {
                let error = {};
                try { error = await response.json(); } catch (_) { /* non-json */ }
                throw new Error(error.message || `HTTP ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            AdminToast.show('error', error.message || 'An error occurred');
            throw error;
        }
    }

    static async createResource(url, formData) {
        // HIGH-11: stamp CSRF into the form body so form-encoded POSTs pass the
        // server's _csrf_is_valid() check at app.py:653.
        this.stampCsrf(formData);
        return await this.fetchWithAuth(url, {
            method: 'POST',
            body: formData
        });
    }

    static async updateResource(url, formData) {
        this.stampCsrf(formData);
        return await this.fetchWithAuth(url, {
            method: 'PUT',
            body: formData
        });
    }

    static async deleteResource(url) {
        return await this.fetchWithAuth(url, {
            method: 'DELETE'
        });
    }

    static async getResource(url) {
        return await this.fetchWithAuth(url);
    }

    static serializeForm(form) {
        const formData = new FormData(form);
        const fileInputs = form.querySelectorAll('input[type="file"]');
        
        // Only append file inputs that have files selected
        fileInputs.forEach(input => {
            if (input.files.length === 0) {
                formData.delete(input.name);
            }
        });
        
        return formData;
    }

    static setupImagePreview(inputId, previewId) {
        const input = document.getElementById(inputId);
        const preview = document.getElementById(previewId);
        
        if (!input || !preview) return;

        input.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    preview.src = e.target.result;
                    preview.style.display = 'block';
                };
                reader.readAsDataURL(this.files[0]);
            }
        });
    }

    static initializeDataTable(tableId, options = {}) {
        const defaultOptions = {
            pageLength: 10,
            responsive: true,
            order: [[0, 'desc']],
            language: {
                search: 'Search:',
                lengthMenu: 'Show _MENU_ entries',
                info: 'Showing _START_ to _END_ of _TOTAL_ entries',
                paginate: {
                    first: 'First',
                    last: 'Last',
                    next: 'Next',
                    previous: 'Previous'
                }
            }
        };

        return new DataTable(`#${tableId}`, { ...defaultOptions, ...options });
    }

    static confirmDelete(message = 'Are you sure you want to delete this item?') {
        return confirm(message);
    }

    static showLoadingSpinner() {
        const spinner = document.createElement('div');
        spinner.className = 'loading-spinner';
        spinner.innerHTML = '<div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div>';
        document.body.appendChild(spinner);
    }

    static hideLoadingSpinner() {
        const spinner = document.querySelector('.loading-spinner');
        if (spinner) {
            spinner.remove();
        }
    }

    static handleFormSubmit(form, submitCallback) {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            AdminUtils.showLoadingSpinner();
            
            try {
                const formData = AdminUtils.serializeForm(this);
                await submitCallback(formData);
                form.reset();
                
                // Reset image preview if exists
                const preview = form.querySelector('.image-preview');
                if (preview) {
                    preview.style.display = 'none';
                    preview.src = '';
                }
            } catch (error) {
                console.error('Form submission error:', error);
            } finally {
                AdminUtils.hideLoadingSpinner();
            }
        });
    }

    static formatDate(dateString) {
        return new Date(dateString).toLocaleString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    static formatCurrency(amount) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'INR'
        }).format(amount);
    }
}

// Add styles for loading spinner
const style = document.createElement('style');
style.textContent = `
    .loading-spinner {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0, 0, 0, 0.5);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 9999;
    }
`;
document.head.appendChild(style);