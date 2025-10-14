import os
import logging
import cloudinary
import cloudinary.uploader
import cloudinary.api
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure Cloudinary with fallback credentials
def configure_cloudinary():
    """Configure Cloudinary with environment variables or fallback credentials"""
    cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME', 'dwqclmigj')
    api_key = os.environ.get('CLOUDINARY_API_KEY')
    api_secret = os.environ.get('CLOUDINARY_API_SECRET')
    
    # If environment variables are not set, use fallback (for development)
    if not api_key or not api_secret:
        logging.warning("Cloudinary API credentials not found in environment variables. Using fallback configuration.")
        # For development/testing, we'll use unsigned URLs
        cloudinary.config(
            cloud_name=cloud_name,
            secure=True
        )
    else:
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True
        )

# Initialize Cloudinary configuration
configure_cloudinary()

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

def extract_public_id_from_url(url):
    """
    Extract public_id from Cloudinary URL.
    
    Args:
        url: Cloudinary URL
    
    Returns:
        str: Public ID or None if extraction failed
    """
    try:
        if not url or 'cloudinary.com' not in url:
            return None
        
        # Extract public_id from URL
        # Format: https://res.cloudinary.com/{cloud_name}/{resource_type}/upload/v{version}/{public_id}.{format}
        parts = url.split('/')
        if len(parts) >= 2:
            # Find the upload part and get everything after it
            upload_index = -1
            for i, part in enumerate(parts):
                if part == 'upload':
                    upload_index = i
                    break
            
            if upload_index != -1 and upload_index + 2 < len(parts):
                # Get public_id (everything after upload/v{version}/)
                public_id_with_format = '/'.join(parts[upload_index + 2:])
                # Remove file extension
                public_id = public_id_with_format.rsplit('.', 1)[0]
                return public_id
        
        return None
        
    except Exception as e:
        logging.error(f"Error extracting public_id from URL {url}: {str(e)}")
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

def delete_file_by_url(url, resource_type='raw'):
    """
    Delete a file from Cloudinary using its URL.
    
    Args:
        url: Cloudinary URL of the file to delete
        resource_type: Type of resource (image, video, raw)
    
    Returns:
        bool: True if deletion was successful, False otherwise
    """
    try:
        public_id = extract_public_id_from_url(url)
        if not public_id:
            logging.warning(f"Could not extract public_id from URL: {url}")
            return False
        
        return delete_file(public_id, resource_type)
        
    except Exception as e:
        logging.error(f"Error deleting file by URL {url}: {str(e)}")
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
