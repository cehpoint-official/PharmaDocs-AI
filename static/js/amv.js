// AMV (Analytical Method Validation) Management System
// Copyright (C) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
// All Rights Reserved

class AMVManager {
    constructor() {
        this.currentInstrument = null;
        this.formData = {};
        this.init();
    }

    init() {
        this.bindInstrumentSelection();
        this.bindFormValidation();
        this.bindFileUploads();
        this.bindAutoGeneration();
        this.bindParameterValidation();
        this.bindAutoCalculations();
        this.bindSubmitButton();
        this.loadSavedData();
    }

    bindInstrumentSelection() {
        document.querySelectorAll('input[name="instrument_type"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                this.currentInstrument = e.target.value;
                this.showInstrumentParameters(e.target.value);
                this.updateFormValidation();
                this.autoSelectValidationParameters(e.target.value);
                this.saveFormData();
            });
        });
    }

    showInstrumentParameters(instrumentType) {
        // Hide all parameter sections
        document.querySelectorAll('.instrument-params').forEach(div => {
            div.style.display = 'none';
        });
        
        // Show relevant parameter section
        const paramDivId = instrumentType + '-params';
        const paramDiv = document.getElementById(paramDivId);
        
        if (paramDiv) {
            paramDiv.style.display = 'block';
            this.animateSection(paramDiv);
        }
    }

    animateSection(element) {
        element.style.opacity = '0';
        element.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            element.style.transition = 'all 0.3s ease';
            element.style.opacity = '1';
            element.style.transform = 'translateY(0)';
        }, 100);
    }

    bindFormValidation() {
        const form = document.getElementById('amvForm');
        if (!form) {
            console.error('Form with id "amvForm" not found');
            return;
        }

        form.addEventListener('submit', (e) => {
            if (!this.validateForm()) {
                e.preventDefault();
                return false;
            }
            
            this.showLoadingState();
        });

        // Real-time validation
        form.querySelectorAll('input, select, textarea').forEach(field => {
            field.addEventListener('blur', () => {
                this.validateField(field);
            });
            
            field.addEventListener('input', () => {
                this.clearFieldError(field);
                this.saveFormData();
            });
        });
    }

    validateForm() {
        const errors = [];
        
        // Required fields validation
        const requiredFields = [
            'document_title',
            'product_name', 
            'label_claim',
            'active_ingredient'
        ];
        
        requiredFields.forEach(fieldName => {
            const field = document.querySelector(`[name="${fieldName}"]`);
            if (field && !field.value.trim()) {
                errors.push(`${this.getFieldLabel(fieldName)} is required`);
                this.showFieldError(field, 'This field is required');
            }
        });

        // Instrument selection validation
        const instrumentSelected = document.querySelector('input[name="instrument_type"]:checked');
        if (!instrumentSelected) {
            errors.push('Please select an instrument type');
            this.showGeneralError('Please select an instrument type');
        }

        // Validation parameters validation
        const validationParamsSelected = document.querySelectorAll('input[name="val_params"]:checked');
        if (validationParamsSelected.length === 0) {
            errors.push('Please select at least one validation parameter');
            this.showGeneralError('Please select at least one validation parameter');
        }

        // Parameters to validate validation
        const parametersToValidateSelected = document.querySelectorAll('input[name="parameters_to_validate"]:checked');
        if (parametersToValidateSelected.length === 0) {
            errors.push('Please select at least one parameter to validate/verify');
            this.showGeneralError('Please select at least one parameter to validate/verify');
        }

        // File validation - only method_analysis_file is required
        const requiredFiles = ['method_analysis_file'];
        requiredFiles.forEach(fileName => {
            const fileInput = document.querySelector(`[name="${fileName}"]`);
            if (fileInput && !fileInput.files.length) {
                errors.push(`${this.getFieldLabel(fileName)} is required`);
                this.showFieldError(fileInput, 'This file is required');
            }
        });

        // Instrument-specific validation
        if (instrumentSelected) {
            const instrumentErrors = this.validateInstrumentParameters(instrumentSelected.value);
            errors.push(...instrumentErrors);
        }

        if (errors.length > 0) {
            this.showErrors(errors);
            return false;
        }

        return true;
    }

    validateInstrumentParameters(instrumentType) {
        const errors = [];
        const paramSection = document.getElementById(instrumentType + '-params');
        
        if (!paramSection) return errors;

        // Get required fields for this instrument
        const requiredFields = this.getRequiredFieldsForInstrument(instrumentType);
        
        requiredFields.forEach(fieldName => {
            const field = paramSection.querySelector(`[name="${fieldName}"]`);
            if (field) {
                // Skip validation if field is hidden (not in current instrument section)
                if (field.offsetParent === null) {
                    return;
                }
                
                // Special validation for wavelength fields
                if (fieldName.includes('wavelength')) {
                    if (!this.validateWavelengthField(field)) {
                        errors.push(`${this.getFieldLabel(fieldName)} is invalid for ${instrumentType.toUpperCase()}`);
                    }
                } else if (!field.value.trim()) {
                    errors.push(`${this.getFieldLabel(fieldName)} is required for ${instrumentType.toUpperCase()}`);
                    this.showFieldError(field, 'This field is required');
                }
            }
        });

        return errors;
    }

    getRequiredFieldsForInstrument(instrumentType) {
        const requirements = {
            'uv': ['uv_wavelength'],
            'aas': ['uv_wavelength'], // AAS uses same wavelength field as UV
            'hplc': ['hplc_wavelength', 'hplc_flow_rate'],
            'gc': ['hplc_wavelength', 'hplc_flow_rate'], // GC uses same fields as HPLC
            'titration': ['titration_reference_volume']
        };
        
        return requirements[instrumentType] || [];
    }

    validateWavelengthField(field) {
        if (!field) return true;
        
        const value = parseFloat(field.value);
        const min = parseFloat(field.getAttribute('min'));
        const max = parseFloat(field.getAttribute('max'));
        
        // If field is empty, it's valid (optional)
        if (!field.value.trim()) {
            return true;
        }
        
        // If field has value, check if it's within range
        if (isNaN(value)) {
            this.showFieldError(field, 'Please enter a valid number');
            return false;
        }
        
        if (min && value < min) {
            this.showFieldError(field, `Value must be at least ${min}`);
            return false;
        }
        
        if (max && value > max) {
            this.showFieldError(field, `Value must be no more than ${max}`);
            return false;
        }
        
        this.clearFieldError(field);
        return true;
    }

    validateField(field) {
        const value = field.value.trim();
        
        // Required field validation
        if (field.hasAttribute('required') && !value) {
            this.showFieldError(field, 'This field is required');
            return false;
        }

        // Number field validation
        if (field.type === 'number' && value) {
            const num = parseFloat(value);
            if (isNaN(num)) {
                this.showFieldError(field, 'Please enter a valid number');
                return false;
            }
            
            // Check for negative values where not allowed
            if (num < 0 && !field.name.includes('weight') && !field.name.includes('volume')) {
                this.showFieldError(field, 'Value must be positive');
                return false;
            }
        }

        // Email validation
        if (field.type === 'email' && value) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(value)) {
                this.showFieldError(field, 'Please enter a valid email address');
                return false;
            }
        }

        this.clearFieldError(field);
        return true;
    }

    showFieldError(field, message) {
        this.clearFieldError(field);
        
        field.classList.add('is-invalid');
        
        const errorDiv = document.createElement('div');
        errorDiv.className = 'invalid-feedback';
        errorDiv.textContent = message;
        
        field.parentNode.appendChild(errorDiv);
    }

    clearFieldError(field) {
        field.classList.remove('is-invalid');
        
        const errorDiv = field.parentNode.querySelector('.invalid-feedback');
        if (errorDiv) {
            errorDiv.remove();
        }
    }

    showGeneralError(message) {
        // Create or update general error alert
        let alertDiv = document.getElementById('generalError');
        if (!alertDiv) {
            alertDiv = document.createElement('div');
            alertDiv.id = 'generalError';
            alertDiv.className = 'alert alert-danger alert-dismissible fade show';
            alertDiv.style.position = 'fixed';
            alertDiv.style.top = '20px';
            alertDiv.style.right = '20px';
            alertDiv.style.zIndex = '9999';
            alertDiv.style.minWidth = '300px';
            
            document.body.appendChild(alertDiv);
        }
        
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            if (alertDiv) {
                alertDiv.remove();
            }
        }, 5000);
    }

    showErrors(errors) {
        const errorMessage = errors.join('\n');
        this.showGeneralError(errorMessage);
    }

    bindFileUploads() {
        document.querySelectorAll('.file-input').forEach(input => {
            input.addEventListener('change', (e) => {
                this.handleFileUpload(e.target);
            });
            
            // Drag and drop support
            const uploadArea = input.closest('.file-upload-area');
            if (uploadArea) {
                uploadArea.addEventListener('dragover', (e) => {
                    e.preventDefault();
                    uploadArea.classList.add('dragover');
                });
                
                uploadArea.addEventListener('dragleave', () => {
                    uploadArea.classList.remove('dragover');
                });
                
                uploadArea.addEventListener('drop', (e) => {
                    e.preventDefault();
                    uploadArea.classList.remove('dragover');
                    
                    const files = e.dataTransfer.files;
                    if (files.length > 0) {
                        input.files = files;
                        this.handleFileUpload(input);
                    }
                });
            }
        });
    }

    handleFileUpload(input) {
        const file = input.files[0];
        if (!file) return;

        // Validate file type
        const allowedTypes = this.getAllowedFileTypes(input.name);
        if (!allowedTypes.includes(file.type) && !this.isAllowedExtension(file.name, allowedTypes)) {
            this.showFieldError(input, 'Invalid file type');
            input.value = '';
            return;
        }

        // Validate file size (max 10MB)
        const maxSize = 10 * 1024 * 1024; // 10MB
        if (file.size > maxSize) {
            this.showFieldError(input, 'File size must be less than 10MB');
            input.value = '';
            return;
        }

        // Update UI
        const placeholder = input.nextElementSibling;
        if (placeholder) {
            placeholder.innerHTML = `
                <p class="mb-0 text-success">
                    <i class="fas fa-check-circle me-1"></i>${file.name}
                </p>
                <small class="text-muted">${this.formatFileSize(file.size)}</small>
            `;
        }

        this.clearFieldError(input);
        this.saveFormData();
    }

    getAllowedFileTypes(fieldName) {
        const types = {
            'stp_file': ['.doc', '.docx'],
            'method_analysis_file': ['.pdf'],
            'raw_data_file': ['.csv', '.xls', '.xlsx']
        };
        
        return types[fieldName] || [];
    }

    isAllowedExtension(filename, allowedTypes) {
        const extension = '.' + filename.split('.').pop().toLowerCase();
        return allowedTypes.includes(extension);
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    bindAutoGeneration() {
        // Auto-generate document number
        const titleField = document.getElementById('docTitle');
        const docNumberField = document.getElementById('docNumber');
        const companyField = document.getElementById('company');
        
        if (titleField && docNumberField && companyField) {
            titleField.addEventListener('input', () => {
                if (!docNumberField.value && titleField.value && companyField.value) {
                    this.generateDocumentNumber();
                }
            });
            
            companyField.addEventListener('change', () => {
                if (!docNumberField.value && titleField.value && companyField.value) {
                    this.generateDocumentNumber();
                }
            });
        }
    }

    async generateDocumentNumber() {
        try {
            const companyId = document.getElementById('company')?.value;
            if (!companyId) return;
            
            const response = await fetch('/amv/api/generate-number', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    company_id: companyId
                })
            });

            if (response.ok) {
                const result = await response.json();
                document.getElementById('docNumber').value = result.document_number;
            } else {
                // Fallback to local generation
                this.generateLocalDocumentNumber();
            }
        } catch (error) {
            console.error('Error generating document number:', error);
            this.generateLocalDocumentNumber();
        }
    }

    generateLocalDocumentNumber() {
        const currentYear = new Date().getFullYear();
        const randomNum = Math.floor(Math.random() * 1000) + 1;
        const docNumber = `AMV/${currentYear}/${randomNum.toString().padStart(4, '0')}`;
        document.getElementById('docNumber').value = docNumber;
    }

    bindParameterValidation() {
        // Validate parameter combinations
        document.querySelectorAll('input[name="val_params"]').forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                this.validateParameterCombinations();
            });
        });

        document.querySelectorAll('input[name="parameters_to_validate"]').forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                this.validateParameterCombinations();
            });
        });
    }

    validateParameterCombinations() {
        const validationParams = Array.from(document.querySelectorAll('input[name="val_params"]:checked'))
            .map(cb => cb.value);
        
        const parametersToValidate = Array.from(document.querySelectorAll('input[name="parameters_to_validate"]:checked'))
            .map(cb => cb.value);

        // Show recommendations based on selections
        this.showParameterRecommendations(validationParams, parametersToValidate);
    }

    showParameterRecommendations(validationParams, parametersToValidate) {
        // This could show helpful recommendations based on ICH guidelines
        // For now, just ensure basic validation
    }

    updateFormValidation() {
        // Update validation rules based on current instrument
        const paramSection = document.getElementById(this.currentInstrument + '-params');
        if (!paramSection) return;

        // Set required attributes based on instrument type
        const requiredFields = this.getRequiredFieldsForInstrument(this.currentInstrument);
        
        paramSection.querySelectorAll('input').forEach(field => {
            field.removeAttribute('required');
        });

        requiredFields.forEach(fieldName => {
            const field = paramSection.querySelector(`[name="${fieldName}"]`);
            if (field) {
                field.setAttribute('required', 'true');
            }
        });
    }

    showLoadingState() {
        const submitBtn = document.getElementById('submitBtn');
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Creating Document...';
        }
    }

    saveFormData() {
        const form = document.getElementById('amvForm');
        if (!form) return;

        const formData = new FormData(form);
        const data = {};
        
        for (let [key, value] of formData.entries()) {
            if (data[key]) {
                // Handle multiple values (checkboxes)
                if (Array.isArray(data[key])) {
                    data[key].push(value);
                } else {
                    data[key] = [data[key], value];
                }
            } else {
                data[key] = value;
            }
        }

        // Save to localStorage
        try {
            localStorage.setItem('amvFormData', JSON.stringify({
                timestamp: Date.now(),
                data: data,
                instrument: this.currentInstrument
            }));
        } catch (error) {
            console.error('Error saving form data:', error);
        }
    }

    loadSavedData() {
        try {
            const saved = localStorage.getItem('amvFormData');
            if (!saved) return;

            const { timestamp, data, instrument } = JSON.parse(saved);
            
            // Only load if less than 24 hours old
            if (Date.now() - timestamp > 24 * 60 * 60 * 1000) {
                localStorage.removeItem('amvFormData');
                return;
            }

            // Restore form data
            Object.entries(data).forEach(([key, value]) => {
                const field = document.querySelector(`[name="${key}"]`);
                if (field) {
                    // Skip file inputs - they can't be programmatically set
                    if (field.type === 'file') {
                        return;
                    }
                    
                    if (field.type === 'checkbox' || field.type === 'radio') {
                        if (Array.isArray(value)) {
                            value.forEach(val => {
                                const checkbox = document.querySelector(`[name="${key}"][value="${val}"]`);
                                if (checkbox) checkbox.checked = true;
                            });
                        } else {
                            field.checked = true;
                        }
                    } else {
                        field.value = value;
                    }
                }
            });

            // Restore instrument selection
            if (instrument) {
                const instrumentRadio = document.querySelector(`[name="instrument_type"][value="${instrument}"]`);
                if (instrumentRadio) {
                    instrumentRadio.checked = true;
                    this.showInstrumentParameters(instrument);
                }
            }

        } catch (error) {
            console.error('Error loading saved data:', error);
        }
    }

    bindAutoCalculations() {
        // Auto-calculate concentrations and dilutions
        this.bindConcentrationCalculations();
        this.bindDilutionCalculations();
        this.bindValidationParameterRecommendations();
    }

    bindSubmitButton() {
        const submitBtn = document.getElementById('submitBtn');
        if (submitBtn) {
            submitBtn.addEventListener('click', (e) => {
                // Let the form's submit event handle the validation
            });
        }
    }

    bindConcentrationCalculations() {
        // UV/AAS concentration calculations
        const uvFields = ['uv_weight_standard', 'uv_weight_sample', 'uv_final_concentration_standard'];
        uvFields.forEach(fieldName => {
            const field = document.querySelector(`[name="${fieldName}"]`);
            if (field) {
                field.addEventListener('input', () => {
                    this.calculateUVConcentrations();
                });
            }
        });

        // HPLC concentration calculations
        const hplcFields = ['hplc_weight_standard', 'hplc_weight_sample', 'hplc_final_concentration_standard'];
        hplcFields.forEach(fieldName => {
            const field = document.querySelector(`[name="${fieldName}"]`);
            if (field) {
                field.addEventListener('input', () => {
                    this.calculateHPLCConcentrations();
                });
            }
        });
    }

    bindDilutionCalculations() {
        // Auto-calculate dilution factors based on method parameters
        const methodFile = document.querySelector('[name="method_analysis_file"]');
        if (methodFile) {
            methodFile.addEventListener('change', (e) => {
                if (e.target.files.length > 0) {
                    this.extractMethodParameters(e.target.files[0]);
                }
            });
        }
    }

    bindValidationParameterRecommendations() {
        // Show recommendations based on selected parameters to validate
        document.querySelectorAll('input[name="parameters_to_validate"]').forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                this.showValidationRecommendations();
            });
        });
    }

    calculateUVConcentrations() {
        const weightStandard = parseFloat(document.querySelector('[name="uv_weight_standard"]')?.value || 0);
        const weightSample = parseFloat(document.querySelector('[name="uv_weight_sample"]')?.value || 0);
        const finalConcStandard = parseFloat(document.querySelector('[name="uv_final_concentration_standard"]')?.value || 0);
        
        if (weightStandard > 0 && finalConcStandard > 0) {
            // Calculate sample concentration based on standard
            const sampleConc = (weightSample / weightStandard) * finalConcStandard;
            const sampleField = document.querySelector('[name="uv_final_concentration_sample"]');
            if (sampleField && !sampleField.value) {
                sampleField.value = sampleConc.toFixed(3);
            }
        }
    }

    calculateHPLCConcentrations() {
        const weightStandard = parseFloat(document.querySelector('[name="hplc_weight_standard"]')?.value || 0);
        const weightSample = parseFloat(document.querySelector('[name="hplc_weight_sample"]')?.value || 0);
        const finalConcStandard = parseFloat(document.querySelector('[name="hplc_final_concentration_standard"]')?.value || 0);
        
        if (weightStandard > 0 && finalConcStandard > 0) {
            // Calculate sample concentration based on standard
            const sampleConc = (weightSample / weightStandard) * finalConcStandard;
            const sampleField = document.querySelector('[name="hplc_final_concentration_sample"]');
            if (sampleField && !sampleField.value) {
                sampleField.value = sampleConc.toFixed(3);
            }
        }
    }

    async extractMethodParameters(file) {
        try {
            this.showInfoMessage('Extracting method parameters from PDF...');
            
            const formData = new FormData();
            formData.append('method_file', file);
            formData.append('instrument_type', this.currentInstrument || 'hplc');
            
            const response = await fetch('/amv/api/extract-method', {
                method: 'POST',
                body: formData
            });
            
            if (response.ok) {
                const result = await response.json();
                this.populateExtractedParameters(result.parameters);
                this.showExtractionSummary(result.summary);
            } else {
                const error = await response.json();
                this.showGeneralError(error.error || 'Failed to extract parameters');
            }
        } catch (error) {
            console.error('Error extracting method parameters:', error);
            this.showGeneralError('Failed to extract method parameters');
        }
    }

    populateExtractedParameters(parameters) {
        // Populate form fields with extracted parameters
        Object.entries(parameters).forEach(([key, value]) => {
            if (typeof value === 'number' || typeof value === 'string') {
                // Map extracted parameters to form fields
                const fieldMapping = this.getFieldMapping();
                const fieldName = fieldMapping[key];
                
                if (fieldName) {
                    const field = document.querySelector(`[name="${fieldName}"]`);
                    if (field && !field.value) { // Only populate if field is empty
                        field.value = value;
                    }
                }
            }
        });
    }

    getFieldMapping() {
        const mapping = {
            'wavelength': this.currentInstrument === 'hplc' ? 'hplc_wavelength' : 'uv_wavelength',
            'flow_rate': 'hplc_flow_rate',
            'injection_volume': 'hplc_injection_volume',
            'weight_standard': this.currentInstrument === 'hplc' ? 'hplc_weight_standard' : 'uv_weight_standard',
            'weight_sample': this.currentInstrument === 'hplc' ? 'hplc_weight_sample' : 'uv_weight_sample',
            'concentration': this.currentInstrument === 'hplc' ? 'hplc_final_concentration_standard' : 'uv_final_concentration_standard'
        };
        
        return mapping;
    }

    showExtractionSummary(summary) {
        const existingAlert = document.getElementById('extractionSummary');
        if (existingAlert) {
            existingAlert.remove();
        }
        
        const alertDiv = document.createElement('div');
        alertDiv.id = 'extractionSummary';
        alertDiv.className = 'alert alert-success alert-dismissible fade show';
        alertDiv.style.position = 'fixed';
        alertDiv.style.top = '20px';
        alertDiv.style.right = '20px';
        alertDiv.style.zIndex = '9999';
        alertDiv.style.minWidth = '400px';
        alertDiv.style.maxWidth = '500px';
        
        alertDiv.innerHTML = `
            <h6><i class="fas fa-check-circle me-2"></i>Method Parameters Extracted</h6>
            <pre style="white-space: pre-wrap; font-size: 0.9em; margin: 0;">${summary}</pre>
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(alertDiv);
        
        // Auto-hide after 15 seconds
        setTimeout(() => {
            if (alertDiv) {
                alertDiv.remove();
            }
        }, 15000);
    }

    showValidationRecommendations() {
        const selectedParams = Array.from(document.querySelectorAll('input[name="parameters_to_validate"]:checked'))
            .map(cb => cb.value);
        
        const recommendations = this.getValidationRecommendations(selectedParams);
        
        if (recommendations.length > 0) {
            this.showRecommendations(recommendations);
        }
    }

    getValidationRecommendations(selectedParams) {
        const recommendations = [];
        
        if (selectedParams.includes('assay')) {
            recommendations.push('For Assay validation, consider including: Specificity, System Suitability, Precision, Linearity, Accuracy, and Robustness');
        }
        
        if (selectedParams.includes('dissolution')) {
            recommendations.push('For Dissolution validation, consider including: Specificity, System Suitability, Precision, Linearity, and Robustness');
        }
        
        if (selectedParams.includes('related_substances') || selectedParams.includes('organic_impurities')) {
            recommendations.push('For impurity methods, consider including: Specificity, LOD/LOQ, Linearity, and Precision');
        }
        
        return recommendations;
    }

    showRecommendations(recommendations) {
        const existingAlert = document.getElementById('validationRecommendations');
        if (existingAlert) {
            existingAlert.remove();
        }
        
        const alertDiv = document.createElement('div');
        alertDiv.id = 'validationRecommendations';
        alertDiv.className = 'alert alert-info alert-dismissible fade show';
        alertDiv.style.position = 'fixed';
        alertDiv.style.top = '80px';
        alertDiv.style.right = '20px';
        alertDiv.style.zIndex = '9999';
        alertDiv.style.minWidth = '400px';
        alertDiv.style.maxWidth = '500px';
        
        alertDiv.innerHTML = `
            <h6><i class="fas fa-lightbulb me-2"></i>Validation Recommendations</h6>
            <ul class="mb-0">
                ${recommendations.map(rec => `<li>${rec}</li>`).join('')}
            </ul>
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(alertDiv);
        
        // Auto-hide after 10 seconds
        setTimeout(() => {
            if (alertDiv) {
                alertDiv.remove();
            }
        }, 10000);
    }

    showInfoMessage(message) {
        const alertDiv = document.createElement('div');
        alertDiv.className = 'alert alert-info alert-dismissible fade show';
        alertDiv.style.position = 'fixed';
        alertDiv.style.top = '20px';
        alertDiv.style.right = '20px';
        alertDiv.style.zIndex = '9999';
        alertDiv.style.minWidth = '300px';
        
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(alertDiv);
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            if (alertDiv) {
                alertDiv.remove();
            }
        }, 5000);
    }

    getFieldLabel(fieldName) {
        const labels = {
            'document_title': 'Document Title',
            'product_name': 'Product Name',
            'label_claim': 'Label Claim',
            'active_ingredient': 'Active Ingredient',
            'stp_file': 'STP File',
            'method_analysis_file': 'Method Analysis File',
            'uv_wavelength': 'Wavelength',
            'hplc_wavelength': 'Wavelength',
            'hplc_flow_rate': 'Flow Rate',
            'titration_reference_volume': 'Reference Volume'
        };
        
        return labels[fieldName] || fieldName.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
    }

    autoSelectValidationParameters(instrumentType) {
        // Define validation parameters for each instrument type
        const validationParameters = {
            'uv': [
                'specificity',
                'system_suitability',
                'system_precision',
                'method_precision',
                'intermediate_precision',
                'linearity',
                'lod_loq',
                'lod_loq_precision',
                'range',
                'recovery',
                'robustness'
            ],
            'aas': [
                'specificity',
                'system_suitability',
                'system_precision',
                'method_precision',
                'intermediate_precision',
                'linearity',
                'lod_loq',
                'lod_loq_precision',
                'range',
                'recovery',
                'robustness'
            ],
            'hplc': [
                'specificity',
                'system_suitability',
                'system_precision',
                'method_precision',
                'intermediate_precision',
                'linearity',
                'lod_loq',
                'lod_loq_precision',
                'range',
                'recovery',
                'robustness'
            ],
            'uplc': [
                'specificity',
                'system_suitability',
                'system_precision',
                'method_precision',
                'intermediate_precision',
                'linearity',
                'lod_loq',
                'lod_loq_precision',
                'range',
                'recovery',
                'robustness'
            ],
            'gc': [
                'specificity',
                'system_suitability',
                'system_precision',
                'method_precision',
                'intermediate_precision',
                'linearity',
                'lod_loq',
                'lod_loq_precision',
                'range',
                'recovery',
                'robustness'
            ],
            'titration': [
                'specificity',
                'system_suitability',
                'system_precision',
                'method_precision',
                'intermediate_precision',
                'linearity',
                'lod_loq',
                'lod_loq_precision',
                'range',
                'recovery',
                'robustness'
            ]
        };
        
        // Get the parameters for the selected instrument type
        const selectedParams = validationParameters[instrumentType] || [];
        
        if (selectedParams.length > 0) {
            // First, uncheck all validation parameter checkboxes
            document.querySelectorAll('input[name="val_params"]').forEach(checkbox => {
                checkbox.checked = false;
            });
            
            // Then check the ones for the selected instrument type
            selectedParams.forEach(paramValue => {
                const checkbox = document.querySelector(`input[name="val_params"][value="${paramValue}"]`);
                if (checkbox) {
                    checkbox.checked = true;
                }
            });
            
            // Show the auto-selection notification
            const notification = document.getElementById('auto-selection-notification');
            if (notification) {
                notification.classList.remove('hidden');
                
                // Auto-hide the notification after 5 seconds
                setTimeout(() => {
                    notification.classList.add('hidden');
                }, 5000);
            }
            
            // Show a success message
            this.showInfoMessage(`Auto-selected ${selectedParams.length} validation parameters for ${instrumentType.toUpperCase()}`);
        }
    }
}

// Initialize AMV Manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.amvManager = new AMVManager();
});

// Export for global use
window.AMVManager = AMVManager;
