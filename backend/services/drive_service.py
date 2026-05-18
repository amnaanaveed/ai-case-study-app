import os
import logging
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

logger = logging.getLogger(__name__)

def upload_to_drive(file_path: str, access_token: str) -> str:
    """Uploads a file directly to the logged-in user's Google Drive."""
    try:
        logger.info(f"Uploading '{file_path}' using Frontend User Token...")
        
        # Build credentials directly from the user's frontend login token
        creds = Credentials(token=access_token)
        service = build('drive', 'v3', credentials=creds)
        
        file_name = os.path.basename(file_path)
        
        # Uploads directly to the user's main "My Drive"
        file_metadata = {
            'name': file_name
        }
        media = MediaFileUpload(file_path, mimetype='application/pdf')
        
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()
        
        return file.get('webViewLink')
        
    except Exception as e:
        logger.error(f"User Drive upload failed: {e}")
        raise e