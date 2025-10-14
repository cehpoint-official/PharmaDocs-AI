import os
import logging
import cloudinary
import cloudinary.uploader
import cloudinary.api
from werkzeug.utils import secure_filename

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET'),
    secure=True
)

def upload_file(file, folder=None, resource_type='auto'):
    """
    Upload a file to Cloudinary.
    
    Args:
        file: File object from Flask request
        folder: Optional folder name in Cloudinary
        resource_type: Type of resource (auto, image, video, raw)
    
    Returns:
        str: Secure URL of uploaded file or None if upload failed
    """
    try:
        if not file or not file.filename:
            return None
        
        # Secure the filename
        filename = secure_filename(file.filename)
        
        # Upload options
        upload_options = {
            'resource_type': resource_type,
            'use_filename': True,
            'unique_filename': True,
            'overwrite': False
        }
        
        if folder:
            upload_options['folder'] = folder
        
        # Upload to Cloudinary
        result = cloudinary.uploader.upload(file, **upload_options)
        
        logging.info(f"File uploaded successfully: {result['secure_url']}")
        return result['secure_url']
        
    except Exception as e:
        logging.error(f"Cloudinary upload error: {str(e)}")
        return None

def upload_file_from_path(file_path, folder=None, resource_type='auto'):
    """
    Upload a file from local path to Cloudinary.
    
    Args:
        file_path: Local file path
        folder: Optional folder name in Cloudinary
        resource_type: Type of resource (auto, image, video, raw)
    
    Returns:
        str: Secure URL of uploaded file or None if upload failed
    """
    try:
        if not os.path.exists(file_path):
            logging.error(f"File not found: {file_path}")
            return None
        
        # Upload options
        upload_options = {
            'resource_type': resource_type,
            'use_filename': True,
            'unique_filename': True,
            'overwrite': False
        }
        
        if folder:
            upload_options['folder'] = folder
        
        # Upload to Cloudinary
        result = cloudinary.uploader.upload(file_path, **upload_options)
        
        logging.info(f"File uploaded successfully: {result['secure_url']}")
        return result['secure_url']
        
    except Exception as e:
        logging.error(f"Cloudinary upload error: {str(e)}")
        return None

def delete_file(public_id, resource_type='image'):
    """
    Delete a file from Cloudinary.
    
    Args:
        public_id: Public ID of the file to delete
        resource_type: Type of resource (image, video, raw)
    
    Returns:
        bool: True if deletion was successful, False otherwise
    """
    try:
        result = cloudinary.uploader.destroy(public_id, resource_type=resource_type)
        
        if result['result'] == 'ok':
            logging.info(f"File deleted successfully: {public_id}")
            return True
        else:
            logging.warning(f"File deletion result: {result}")
            return False
            
    except Exception as e:
        logging.error(f"Cloudinary deletion error: {str(e)}")
        return False

def get_file_info(public_id, resource_type='image'):
    """
    Get information about a file in Cloudinary.
    
    Args:
        public_id: Public ID of the file
        resource_type: Type of resource (image, video, raw)
    
    Returns:
        dict: File information or None if not found
    """
    try:
        result = cloudinary.api.resource(public_id, resource_type=resource_type)
        return result
        
    except cloudinary.exceptions.NotFound:
        logging.warning(f"File not found: {public_id}")
        return None
    except Exception as e:
        logging.error(f"Error getting file info: {str(e)}")
        return None

def generate_signed_url(public_id, resource_type='image', expires_at=None, transformation=None):
    """
    Generate a signed URL for secure access to a file.
    
    Args:
        public_id: Public ID of the file
        resource_type: Type of resource (image, video, raw)
        expires_at: Expiration timestamp
        transformation: Optional transformation parameters
    
    Returns:
        str: Signed URL or None if generation failed
    """
    try:
        options = {
            'resource_type': resource_type,
            'sign_url': True
        }
        
        if expires_at:
            options['expires_at'] = expires_at
        
        if transformation:
            options['transformation'] = transformation
        
        url = cloudinary.utils.cloudinary_url(public_id, **options)[0]
        return url
        
    except Exception as e:
        logging.error(f"Error generating signed URL: {str(e)}")
        return None
