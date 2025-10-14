# Copyright (C) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
# All Rights Reserved.

import logging
from datetime import datetime
from flask import request
from models import ActivityLog
from app import db

def log_activity(user_id, action, details=None):
    """
    Log user activity.

    Args:
        user_id: ID of the user performing the action
        action: Action being performed
        details: Additional details about the action
    """
    try:
        # Get client IP address
        ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        if ip_address:
            ip_address = ip_address.split(',')[0].strip()

        # Create activity log entry
        activity = ActivityLog(
            user_id=user_id,
            action=action,
            details=details,
            ip_address=ip_address,
            timestamp=datetime.utcnow()
        )

        db.session.add(activity)
        db.session.commit()

        logging.info(f"Activity logged: {action} by user {user_id}")

    except Exception as e:
        logging.error(f"Error logging activity: {str(e)}")
        # Don't raise exception as this is a logging function

def format_file_size(size_bytes):
    """
    Format file size in human readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        str: Formatted size string
    """
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"

def generate_document_number(document_type, company_id):
    """
    Generate a unique document number.

    Args:
        document_type: Type of document (AMV, PV, etc.)
        company_id: ID of the company

    Returns:
        str: Generated document number
    """
    from models import Document

    try:
        # Get current count of documents of this type for this company
        count = Document.query.filter_by(
            document_type=document_type,
            company_id=company_id
        ).count() + 1

        # Generate number based on type and count
        type_prefixes = {
            'AMV': 'AMV/P',
            'PV': 'PV/P',
            'Stability': 'STB/P',
            'Degradation': 'DEG/P'
        }

        prefix = type_prefixes.get(document_type, 'DOC/P')
        document_number = f"{prefix}/{count:03d}"

        return document_number

    except Exception as e:
        logging.error(f"Error generating document number: {str(e)}")
        return f"{document_type}/P/001"

def sanitize_filename(filename):
    """
    Sanitize filename for safe storage.

    Args:
        filename: Original filename

    Returns:
        str: Sanitized filename
    """
    import re

    if not filename:
        return "unnamed"

    # Remove special characters and spaces
    sanitized = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)

    # Remove multiple underscores
    sanitized = re.sub(r'_+', '_', sanitized)

    # Ensure it's not too long
    if len(sanitized) > 100:
        name, ext = sanitized.rsplit('.', 1) if '.' in sanitized else (sanitized, '')
        sanitized = f"{name[:90]}.{ext}" if ext else name[:100]

    return sanitized

def calculate_rsd(values):
    """
    Calculate Relative Standard Deviation (RSD).

    Args:
        values: List of numeric values

    Returns:
        float: RSD percentage
    """
    import statistics

    try:
        if not values or len(values) < 2:
            return 0.0

        mean = statistics.mean(values)
        if mean == 0:
            return 0.0

        stdev = statistics.stdev(values)
        rsd = (stdev / mean) * 100

        return round(rsd, 2)

    except Exception as e:
        logging.error(f"Error calculating RSD: {str(e)}")
        return 0.0

def parse_concentration_data(data_string):
    """
    Parse concentration data from string format.

    Args:
        data_string: String containing concentration values

    Returns:
        list: List of float values
    """
    try:
        if not data_string:
            return []

        # Split by comma, semicolon, or space
        import re
        values = re.split(r'[,;\s]+', data_string.strip())

        # Convert to float and filter out invalid values
        parsed_values = []
        for value in values:
            try:
                parsed_values.append(float(value))
            except ValueError:
                continue

        return parsed_values

    except Exception as e:
        logging.error(f"Error parsing concentration data: {str(e)}")
        return []

def get_current_timestamp():
    """Get current timestamp in ISO format."""
    return datetime.now().isoformat()

def is_file_allowed(filename, allowed_extensions):
    """
    Check if file extension is allowed.

    Args:
        filename: Name of the file
        allowed_extensions: List of allowed extensions

    Returns:
        bool: True if allowed, False otherwise
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions


def parse_date(d: datetime):
    return datetime.strptime(d, "%Y-%m-%d") if d else None
