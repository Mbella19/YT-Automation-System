"""
Google Drive downloader utility
"""
import re
import gdown
from pathlib import Path
from utils.logger import setup_logger

logger = setup_logger()

def extract_file_id(url):
    """
    Extract file ID from various Google Drive URL formats
    
    Supported formats:
    - https://drive.google.com/file/d/FILE_ID/view
    - https://drive.google.com/open?id=FILE_ID
    - https://drive.google.com/uc?id=FILE_ID
    """
    patterns = [
        r'/file/d/([a-zA-Z0-9_-]+)',
        r'id=([a-zA-Z0-9_-]+)',
        r'/d/([a-zA-Z0-9_-]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

def download_from_drive(drive_url, output_path):
    """
    Download a file from Google Drive
    
    Args:
        drive_url: Google Drive URL (public link)
        output_path: Path where to save the downloaded file
    
    Returns:
        Path to downloaded file or None if failed
    """
    try:
        logger.info(f"Starting download from Google Drive: {drive_url}")
        
        # Extract file ID
        file_id = extract_file_id(drive_url)
        
        if not file_id:
            logger.error("Could not extract file ID from URL")
            return None
        
        logger.info(f"Extracted file ID: {file_id}")
        
        # Construct download URL
        download_url = f"https://drive.google.com/uc?id={file_id}"
        
        # Download file
        logger.info(f"Downloading to: {output_path}")
        output = gdown.download(download_url, str(output_path), quiet=False)
        
        if output:
            logger.info(f"Successfully downloaded file to: {output}")
            return Path(output)
        else:
            logger.error("Download failed")
            return None
            
    except Exception as e:
        logger.error(f"Error downloading from Google Drive: {str(e)}", exc_info=True)
        return None

