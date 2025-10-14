// Copyright (C) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
// All Rights Reserved

// Document Creation Management System
class DocumentCreationManager {
    constructor() {
        this.currentDocumentType = 'AMV';
        this.formData = {};
        this.init();
    }

    init() {
        this.bindDocumentTypeSelection();
        this.bindFormSubmission();
        this.bindParameterUpdates();
        this.loadInitialParameters();
        this.bindDraftSaving();
        this.handleUrlParameters();
    }

    bindDocumentTypeSelection() {
        document.querySelectorAll('input[name="document_type"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                this.currentDocumentType = e.target.value;
                this.loadDocumentParameters(e.target.value);
                this.updateFormValidation();
                this.updateUrlParameter(e.target.value); // 🔹 keep URL in sync
            });
        });
    }

    updateUrlParameter(type) {
        const url = new URL(window.location);
        url.searchParams.set("type", type);
        history.replaceState(null, "", url);
    }

    bindFormSubmission() {
        const form = document.getElementById('createDocumentForm');
        if (!form) return;

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.handleFormSubmission(form);
        });
    }

    bindParameterUpdates() {
        // Listen for changes in basic form fields
        document.querySelectorAll('#title, #company_id, #product_name').forEach(input => {
            input.addEventListener('input', () => {
                this.updateDocumentPreview();
            });
        });

        // Auto-generate document number
        document.getElementById('company_id')?.addEventListener('change', () => {
            this.generateDocumentNumber();
        });
    }

    bindDraftSaving() {
        // Auto-save draft every 30 seconds
        setInterval(() => {
            this.autoSaveDraft();
        }, 30000);

        // Save on beforeunload
        window.addEventListener('beforeunload', () => {
            this.autoSaveDraft();
        });
    }

    handleUrlParameters() {
        const urlParams = new URLSearchParams(window.location.search);
        const docType = urlParams.get('type');
        const editId = urlParams.get('edit');

        if (docType) {
            this.selectDocumentType(docType);
        }

        if (editId) {
            this.loadDocumentForEditing(editId);
        }
    }

    loadDocumentParameters(documentType) {
        const parametersContainer = document.getElementById('documentParameters');
        const templatesContainer = document.getElementById('parameterTemplates');

        if (!parametersContainer || !templatesContainer) return;

        // Clear current parameters
        parametersContainer.innerHTML = '';

        // Get template for document type
        const templateId = `${documentType.toLowerCase()}Parameters`;
        const template = templatesContainer.querySelector(`#${templateId}`);

        if (template) {
            // Clone and append template content
            const content = template.cloneNode(true);
            content.classList.remove('d-none');
            content.removeAttribute('id');
            parametersContainer.appendChild(content);

            // Bind new parameter events
            this.bindParameterEvents(parametersContainer);
        }
    }

    bindParameterEvents(container) {
        // Bind events for newly loaded parameters
        container.querySelectorAll('input, select, textarea').forEach(element => {
            element.addEventListener('change', () => {
                this.updateFormData();
                this.validateForm();
            });
        });
    }

    selectDocumentType(type) {
        const radio = document.querySelector(`input[name="document_type"][value="${type}"]`);
        if (radio) {
            radio.checked = true;
            radio.dispatchEvent(new Event('change'));
        }
    }

    async generateDocumentNumber() {
        const companyId = document.getElementById('company_id')?.value;
        const documentType = this.currentDocumentType;
        const documentNumberInput = document.getElementById('document_number');

        if (!companyId || !documentType || !documentNumberInput) return;

        // Only generate if field is empty
        if (documentNumberInput.value.trim()) return;

        try {
            const response = await fetch('/api/generate-document-number', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    company_id: companyId,
                    document_type: documentType
                })
            });

            if (response.ok) {
                const result = await response.json();
                documentNumberInput.value = result.document_number;
            }
        } catch (error) {
            console.error('Error generating document number:', error);
        }
    }

    async handleFormSubmission(form) {
        const submitBtn = form.querySelector('button[type="submit"]');

        // Validate form
        if (!this.validateForm()) {
            return;
        }

        // Validate files
        if (!window.fileUploadManager?.validateRequiredFiles()) {
            return;
        }

        // Show loading state
        this.setSubmitLoadingState(submitBtn, true);
        this.showProgressBar('Preparing document...', 10);

        try {
            // Prepare form data
            const formData = new FormData(form);

            // Add current document type if not already in form
            if (!formData.has('document_type')) {
                formData.append('document_type', this.currentDocumentType);
            }

            this.showProgressBar('Uploading files...', 30);

            // Submit to backend
            const response = await fetch('/documents/create', {
                method: 'POST',
                body: formData
            });

            this.showProgressBar('Processing...', 70);

            const result = await response.json();

            if (result.success) {
                this.showProgressBar('Document created successfully!', 100);

                // Clear draft
                this.clearDraft();

                // Redirect to document view or dashboard
                setTimeout(() => {
                    if (result.redirect_url) {
                        window.location.href = result.redirect_url;
                    } else {
                        window.location.href = `/documents/${result.document_id}`;
                    }
                }, 1000);

            } else {
                throw new Error(result.error || 'Document creation failed');
            }

        } catch (error) {
            console.error('Form submission error:', error);
            this.showError(error.message);
            this.hideProgressBar();
        } finally {
            this.setSubmitLoadingState(submitBtn, false);
        }
    }

    validateForm() {
        const errors = [];

        // Validate required basic fields
        const requiredFields = ['title', 'company_id'];
        requiredFields.forEach(fieldName => {
            const field = document.getElementById(fieldName) || document.querySelector(`[name="${fieldName}"]`);
            if (field && !field.value.trim()) {
                errors.push(`${fieldName.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())} is required`);
                field.classList.add('is-invalid');
            } else if (field) {
                field.classList.remove('is-invalid');
            }
        });

        // Document type specific validation
        const typeErrors = this.validateDocumentTypeFields();
        errors.push(...typeErrors);

        if (errors.length > 0) {
            this.showError(errors.join('\n'));
            return false;
        }

        return true;
    }

    validateDocumentTypeFields() {
        const errors = [];
        const parametersContainer = document.getElementById('documentParameters');

        if (!parametersContainer) return errors;

        // Check for required fields in parameters
        parametersContainer.querySelectorAll('input[required], select[required]').forEach(field => {
            if (!field.value.trim()) {
                const label = field.closest('.mb-3')?.querySelector('label')?.textContent || field.name;
                errors.push(`${label} is required for ${this.currentDocumentType} documents`);
                field.classList.add('is-invalid');
            } else {
                field.classList.remove('is-invalid');
            }
        });

        return errors;
    }

    updateFormData() {
        const form = document.getElementById('createDocumentForm');
        if (!form) return;

        this.formData = {};

        // Get all form data
        const formData = new FormData(form);
        for (let [key, value] of formData.entries()) {
            this.formData[key] = value;
        }

        // Add uploaded files info
        const files = window.fileUploadManager?.getUploadedFiles() || {};
        this.formData.files = Object.keys(files);
    }

    updateDocumentPreview() {
        // Update any preview elements
        const title = document.getElementById('title')?.value || 'Untitled Document';
        const docType = this.currentDocumentType;

        // Update page title or preview if exists
        const previewTitle = document.getElementById('documentPreviewTitle');
        if (previewTitle) {
            previewTitle.textContent = `${docType}: ${title}`;
        }
    }

    loadInitialParameters() {
        // Load parameters for initially selected document type
        const selectedType = document.querySelector('input[name="document_type"]:checked');
        if (selectedType) {
            this.currentDocumentType = selectedType.value;
            this.loadDocumentParameters(selectedType.value);
        }
    }

    updateFormValidation() {
        // Update form validation rules based on document type
        const form = document.getElementById('createDocumentForm');
        if (!form) return;

        // Remove existing validation classes
        form.querySelectorAll('.is-invalid').forEach(el => {
            el.classList.remove('is-invalid');
        });

        // Set required attributes based on document type
        this.setDocumentTypeRequirements();
    }

    setDocumentTypeRequirements() {
        const parametersContainer = document.getElementById('documentParameters');
        if (!parametersContainer) return;

        // Set required fields based on document type
        const requirements = {
            'AMV': ['active_ingredient', 'analytical_method'],
            'PV': ['process_name', 'batch_size'],
            'Stability': ['study_type', 'storage_conditions'],
            'Degradation': ['degradation_type', 'stress_conditions'],
            'Compatibility': ['drug_name', 'excipients', 'storage_conditions', 'duration'] // 🔹 new
        };

        const currentReqs = requirements[this.currentDocumentType] || [];

        // Clear all required attributes first
        parametersContainer.querySelectorAll('input, select').forEach(field => {
            field.removeAttribute('required');
        });

        // Set required attributes for current document type
        currentReqs.forEach(fieldName => {
            const field = parametersContainer.querySelector(`[name="${fieldName}"]`);
            if (field) {
                field.setAttribute('required', 'true');
            }
        });
    }

    // Draft management
    async autoSaveDraft() {
        if (!this.hasFormData()) return;

        this.updateFormData();

        try {
            localStorage.setItem('documentDraft', JSON.stringify({
                timestamp: Date.now(),
                documentType: this.currentDocumentType,
                formData: this.formData
            }));
        } catch (error) {
            console.error('Error saving draft:', error);
        }
    }

    loadDraft() {
        try {
            const draft = localStorage.getItem('documentDraft');
            if (!draft) return false;

            const draftData = JSON.parse(draft);
            const age = Date.now() - draftData.timestamp;

            // Only load drafts less than 24 hours old
            if (age > 24 * 60 * 60 * 1000) {
                this.clearDraft();
                return false;
            }

            // Show draft restoration prompt
            if (confirm('A draft document was found. Would you like to restore it?')) {
                this.restoreDraft(draftData);
                return true;
            }

        } catch (error) {
            console.error('Error loading draft:', error);
        }

        return false;
    }

    restoreDraft(draftData) {
        // Select document type
        this.selectDocumentType(draftData.documentType);

        // Restore form data
        setTimeout(() => {
            Object.entries(draftData.formData).forEach(([key, value]) => {
                if (key === 'files') return;

                const field = document.getElementById(key) || document.querySelector(`[name="${key}"]`);
                if (field) {
                    field.value = value;
                }
            });

            this.showNotification('Draft restored successfully', 'info');
        }, 100);
    }

    clearDraft() {
        localStorage.removeItem('documentDraft');
    }

    hasFormData() {
        const title = document.getElementById('title')?.value;
        const companyId = document.getElementById('company_id')?.value;
        return !!(title || companyId);
    }

    // Document editing
    async loadDocumentForEditing(documentId) {
        try {
            const response = await fetch(`/documents/${documentId}`);
            if (!response.ok) return;

            const document = await response.json();

            // Populate form with document data
            this.populateFormWithDocument(document);

        } catch (error) {
            console.error('Error loading document for editing:', error);
        }
    }

    populateFormWithDocument(document) {
        // Set document type
        this.selectDocumentType(document.document_type);

        // Populate basic fields
        setTimeout(() => {
            const fields = {
                'title': document.title,
                'company_id': document.company_id,
                'document_number': document.document_number,
                'product_name': document.product_name
            };

            Object.entries(fields).forEach(([key, value]) => {
                const field = document.getElementById(key);
                if (field && value) {
                    field.value = value;
                }
            });

            // Populate metadata fields
            if (document.metadata) {
                try {
                    const metadata = JSON.parse(document.metadata);
                    Object.entries(metadata).forEach(([key, value]) => {
                        const field = document.querySelector(`[name="${key}"]`);
                        if (field && value) {
                            field.value = value;
                        }
                    });
                } catch (error) {
                    console.error('Error parsing document metadata:', error);
                }
            }
        }, 200);
    }

    // UI helper methods
    setSubmitLoadingState(button, isLoading) {
        if (isLoading) {
            button.disabled = true;
            button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Creating Document...';
        } else {
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-magic me-2"></i>Create Document';
        }
    }

    showProgressBar(status, progress) {
        if (window.fileUploadManager) {
            window.fileUploadManager.showUploadProgress(progress, status);
        }
    }

    hideProgressBar() {
        if (window.fileUploadManager) {
            window.fileUploadManager.hideUploadProgress();
        }
    }

    showError(message) {
        if (window.fileUploadManager) {
            window.fileUploadManager.showError(message);
        } else {
            alert(message);
        }
    }

    showNotification(message, type = 'info') {
        if (window.dashboardManager) {
            window.dashboardManager.showNotification(message, type);
        }
    }
}

// Save as draft functionality
window.saveAsDraft = async function() {
    const manager = window.documentCreationManager;
    if (!manager) return;

    try {
        manager.updateFormData();
        await manager.autoSaveDraft();
        manager.showNotification('Draft saved successfully', 'success');
    } catch (error) {
        console.error('Error saving draft:', error);
        manager.showNotification('Error saving draft', 'danger');
    }
};

// Initialize document creation manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.documentCreationManager = new DocumentCreationManager();

    // Try to load draft after a short delay
    setTimeout(() => {
        window.documentCreationManager.loadDraft();
    }, 500);
});

// Export for global use
window.DocumentCreationManager = DocumentCreationManager;
