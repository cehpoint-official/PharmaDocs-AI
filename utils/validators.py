# Copyright (C) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
# All Rights Reserved.

import os
import logging

def validate_file_type(filename, allowed_extensions):
    """
    Validate file type based on extension.

    Args:
        filename: Name of the file
        allowed_extensions: List of allowed extensions (without dots)

    Returns:
        bool: True if file type is allowed, False otherwise
    """
    if not filename:
        return False

    # Get file extension
    file_extension = filename.rsplit('.', 1)[-1].lower()

    # Check if extension is in allowed list
    return file_extension in [ext.lower() for ext in allowed_extensions]

def validate_file_size(file, max_size_mb=10):
    """
    Validate file size.

    Args:
        file: File object
        max_size_mb: Maximum file size in MB

    Returns:
        bool: True if file size is within limit, False otherwise
    """
    try:
        # Seek to end to get file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)  # Reset pointer to beginning

        # Convert MB to bytes
        max_size_bytes = max_size_mb * 1024 * 1024

        return file_size <= max_size_bytes

    except Exception as e:
        logging.error(f"Error validating file size: {str(e)}")
        return False

def validate_document_data(document_type, form_data):
    """
    Validate document-specific data.

    Args:
        document_type: Type of document (AMV, PV, etc.)
        form_data: Form data dictionary

    Returns:
        tuple: (is_valid, error_message)
    """
    try:
        # Common required fields
        required_fields = ['title', 'company_id']

        for field in required_fields:
            if not form_data.get(field):
                return False, f"Missing required field: {field}"

        # Document type specific validation
        if document_type == 'AMV':
            return validate_amv_data(form_data)
        elif document_type == 'PV':
            return validate_pv_data(form_data)
        elif document_type == 'Stability':
            return validate_stability_data(form_data)
        elif document_type == 'Degradation':
            return validate_degradation_data(form_data)

        return True, None

    except Exception as e:
        logging.error(f"Validation error: {str(e)}")
        return False, "Validation error occurred"

def validate_amv_data(form_data):
    """Validate AMV-specific data."""
    # AMV specific validation
    amv_required = ['product_name', 'active_ingredient']

    for field in amv_required:
        if field in form_data and not form_data[field]:
            return False, f"AMV requires: {field}"

    return True, None

def validate_pv_data(form_data):
    """Validate PV-specific data."""
    # PV specific validation
    pv_required = ['process_name', 'batch_size']

    for field in pv_required:
        if field in form_data and not form_data[field]:
            return False, f"PV requires: {field}"

    return True, None

def validate_stability_data(form_data):
    """Validate Stability-specific data."""
    # Stability specific validation
    stability_required = ['study_type', 'storage_conditions']

    for field in stability_required:
        if field in form_data and not form_data[field]:
            return False, f"Stability study requires: {field}"

    return True, None

def validate_degradation_data(form_data):
    """Validate Degradation-specific data."""
    # Degradation specific validation
    degradation_required = ['degradation_type', 'stress_conditions']

    for field in degradation_required:
        if field in form_data and not form_data[field]:
            return False, f"Degradation study requires: {field}"

    return True, None

def validate_email(email):
    """
    Validate email format.

    Args:
        email: Email string

    Returns:
        bool: True if email is valid, False otherwise
    """
    import re

    if not email:
        return False

    # Basic email regex pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """
    Validate password strength.

    Args:
        password: Password string

    Returns:
        tuple: (is_valid, error_message)
    """
    if not password:
        return False, "Password is required"

    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    # Check for at least one uppercase, lowercase, and digit
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)

    if not (has_upper and has_lower and has_digit):
        return False, "Password must contain at least one uppercase letter, one lowercase letter, and one digit"

    return True, None
