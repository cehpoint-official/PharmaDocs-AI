// Copyright (C) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
// All Rights Reserved

// File Upload Management System
class FileUploadManager {
    constructor() {
        this.maxFileSize = 10 * 1024 * 1024; // 10MB
        this.allowedTypes = {
            stp_file: ['.doc', '.docx'],
            raw_data_file: ['.csv', '.xlsx', '.xls'],
            logo: ['.jpg', '.jpeg', '.png', '.svg'],
            signature: ['.jpg', '.jpeg', '.png', '.svg']
        };
        this.init();
    }

    init() {
        this.bindFileUploadAreas();
        this.bindFileInputs();
        this.bindRemoveButtons();
    }

    bindFileUploadAreas() {
        document.querySelectorAll('.file-upload-area').forEach(area => {
            const targetId = area.dataset.target;
            const fileInput = area.querySelector('.file-input') || document.getElementById(targetId);

            if (!fileInput) return;

            // Drag and drop events
            area.addEventListener('dragover', (e) => {
                e.preventDefault();
                area.classList.add('dragover');
            });

            area.addEventListener('dragleave', (e) => {
                e.preventDefault();
                area.classList.remove('dragover');
            });

            area.addEventListener('drop', (e) => {
                e.preventDefault();
                area.classList.remove('dragover');

                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    this.handleFileSelection(fileInput, files[0], area);
                }
            });

            // Click to browse
            area.addEventListener('click', (e) => {
                if (!e.target.closest('.file-upload-preview') && !e.target.closest('button')) {
                    fileInput.click();
                }
            });
        });
    }

    bindFileInputs() {
        document.querySelectorAll('.file-input').forEach(input => {
            input.addEventListener('change', (e) => {
                const file = e.target.files[0];
                const area = input.closest('.file-upload-area');

                if (file) {
                    this.handleFileSelection(input, file, area);
                }
            });
        });

        // Handle regular file inputs without upload areas
        document.querySelectorAll('input[type="file"]:not(.file-input)').forEach(input => {
            input.addEventListener('change', (e) => {
                const file = e.target.files[0];
                if (file) {
                    this.validateFile(file, this.getFileTypeFromInput(input));
                }
            });
        });
    }

    bindRemoveButtons() {
        document.addEventListener('click', (e) => {
            if (e.target.closest('.remove-file')) {
                e.preventDefault();
                const button = e.target.closest('.remove-file');
                const area = button.closest('.file-upload-area');
                const input = area.querySelector('.file-input');

                this.removeFile(input, area);
            }
        });
    }

    handleFileSelection(input, file, area) {
        // Validate file
        const fileType = this.getFileTypeFromInput(input);
        if (!this.validateFile(file, fileType)) {
            return;
        }

        // Update input
        const dt = new DataTransfer();
        dt.items.add(file);
        input.files = dt.files;

        // Update UI
        if (area) {
            this.showFilePreview(area, file);
        }

        // Trigger change event
        input.dispatchEvent(new Event('change', { bubbles: true }));
    }

    validateFile(file, fileType) {
        // Check file size
        if (file.size > this.maxFileSize) {
            this.showError(`File size must be less than ${this.formatFileSize(this.maxFileSize)}`);
            return false;
        }

        // Check file type
        if (fileType && this.allowedTypes[fileType]) {
            const extension = '.' + file.name.split('.').pop().toLowerCase();
            if (!this.allowedTypes[fileType].includes(extension)) {
                this.showError(`Invalid file type. Allowed types: ${this.allowedTypes[fileType].join(', ')}`);
                return false;
            }
        }

        return true;
    }

    getFileTypeFromInput(input) {
        const id = input.id || input.name;

        if (id.includes('stp')) return 'stp_file';
        if (id.includes('raw_data') || id.includes('data')) return 'raw_data_file';
        if (id.includes('logo')) return 'logo';
        if (id.includes('signature')) return 'signature';

        return null;
    }

    showFilePreview(area, file) {
        const placeholder = area.querySelector('.file-upload-placeholder');
        const preview = area.querySelector('.file-upload-preview');
        const fileName = preview.querySelector('.file-name');

        if (placeholder && preview && fileName) {
            placeholder.classList.add('d-none');
            preview.classList.remove('d-none');
            fileName.textContent = file.name;
        }
    }

    removeFile(input, area) {
        // Clear input
        input.value = '';

        // Update UI
        if (area) {
            const placeholder = area.querySelector('.file-upload-placeholder');
            const preview = area.querySelector('.file-upload-preview');

            if (placeholder && preview) {
                placeholder.classList.remove('d-none');
                preview.classList.add('d-none');
            }
        }

        // Trigger change event
        input.dispatchEvent(new Event('change', { bubbles: true }));
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';

        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));

        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    showError(message) {
        // Try to find existing error display
        let errorDiv = document.getElementById('fileUploadError');

        if (!errorDiv) {
            // Create error div if it doesn't exist
            errorDiv = document.createElement('div');
            errorDiv.id = 'fileUploadError';
            errorDiv.className = 'alert alert-danger alert-dismissible fade show mt-3';
            errorDiv.innerHTML = `
                <i class="fas fa-exclamation-triangle me-2"></i>
                <span id="fileErrorMessage"></span>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;

            // Insert at the top of the main content area
            const container = document.querySelector('.container') || document.querySelector('.container-fluid') || document.body;
            const firstChild = container.firstElementChild;
            container.insertBefore(errorDiv, firstChild);
        }

        const errorMessage = document.getElementById('fileErrorMessage');
        if (errorMessage) {
            errorMessage.textContent = message;
        }

        errorDiv.classList.remove('d-none');

        // Auto-hide after 5 seconds
        setTimeout(() => {
            if (errorDiv) {
                errorDiv.classList.add('d-none');
            }
        }, 5000);
    }

    // Utility method to get files from areas
    getUploadedFiles() {
        const files = {};

        document.querySelectorAll('.file-input').forEach(input => {
            if (input.files && input.files[0]) {
                files[input.name || input.id] = input.files[0];
            }
        });

        return files;
    }

    // Progress tracking for uploads
    showUploadProgress(progress, status) {
        const progressDiv = document.getElementById('uploadProgress');
        const progressBar = progressDiv?.querySelector('.progress-bar');
        const statusText = document.getElementById('progressStatus');

        if (progressDiv && progressBar) {
            progressDiv.classList.remove('d-none');
            progressBar.style.width = `${progress}%`;
            progressBar.textContent = `${progress}%`;
        }

        if (statusText && status) {
            statusText.textContent = status;
        }
    }

    hideUploadProgress() {
        const progressDiv = document.getElementById('uploadProgress');
        if (progressDiv) {
            progressDiv.classList.add('d-none');
        }
    }

    // Reset all file inputs
    resetAllFiles() {
        document.querySelectorAll('.file-input').forEach(input => {
            const area = input.closest('.file-upload-area');
            this.removeFile(input, area);
        });

        document.querySelectorAll('input[type="file"]:not(.file-input)').forEach(input => {
            input.value = '';
        });
    }

    // Validate all required files
    validateRequiredFiles() {
        const requiredInputs = document.querySelectorAll('.file-input[required]');
        const missing = [];

        requiredInputs.forEach(input => {
            if (!input.files || !input.files[0]) {
                const label = input.closest('.mb-3')?.querySelector('label')?.textContent || input.name;
                missing.push(label);
            }
        });

        if (missing.length > 0) {
            this.showError(`Please upload the following required files: ${missing.join(', ')}`);
            return false;
        }

        return true;
    }
}

// Cloudinary upload utilities
class CloudinaryUploader {
    constructor() {
        this.uploadUrl = 'https://api.cloudinary.com/v1_1/your-cloud-name/upload'; // This should be configured
        this.uploadPreset = 'pharma_docs'; // This should be configured
    }

    async uploadFile(file, folder = null) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('upload_preset', this.uploadPreset);

        if (folder) {
            formData.append('folder', folder);
        }

        try {
            const response = await fetch(this.uploadUrl, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`Upload failed: ${response.statusText}`);
            }

            const result = await response.json();
            return {
                success: true,
                url: result.secure_url,
                publicId: result.public_id
            };

        } catch (error) {
            console.error('Cloudinary upload error:', error);
            return {
                success: false,
                error: error.message
            };
        }
    }

    async uploadMultipleFiles(files, folder = null, onProgress = null) {
        const results = [];
        const total = files.length;

        for (let i = 0; i < files.length; i++) {
            const file = files[i];

            if (onProgress) {
                onProgress((i / total) * 100, `Uploading ${file.name}...`);
            }

            const result = await this.uploadFile(file, folder);
            results.push({
                file: file,
                result: result
            });
        }

        if (onProgress) {
            onProgress(100, 'Upload complete');
        }

        return results;
    }
}

// Initialize file upload manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.fileUploadManager = new FileUploadManager();
    window.cloudinaryUploader = new CloudinaryUploader();
});

// Export for global use
window.FileUploadManager = FileUploadManager;
window.CloudinaryUploader = CloudinaryUploader;
