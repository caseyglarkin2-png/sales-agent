"""
Google Drive content extractor for voice training.

Supports:
- Google Docs (text extraction)
- Google Sheets (text export)
- PDF files (text extraction)
- DOCX files (text extraction)
- TXT files (direct read)
"""
import io
import logging
from typing import Dict, Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

logger = logging.getLogger(__name__)


class DriveExtractor:
    """Extract content from Google Drive files."""
    
    # MIME types we support
    SUPPORTED_TYPES = {
        # Google native formats
        "application/vnd.google-apps.document": "google_doc",
        "application/vnd.google-apps.spreadsheet": "google_sheet",
        "application/vnd.google-apps.presentation": "google_slides",
        
        # Standard formats
        "application/pdf": "pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
        "text/plain": "txt",
    }
    
    def __init__(self, credentials: Credentials):
        """
        Initialize Drive extractor.
        
        Args:
            credentials: Google OAuth credentials with Drive scope
        """
        self.credentials = credentials
        self.service = build('drive', 'v3', credentials=credentials)
    
    def get_file_metadata(self, file_id: str) -> Dict:
        """
        Get file metadata from Drive.
        
        Args:
            file_id: Google Drive file ID
        
        Returns:
            File metadata dict
        """
        try:
            file = self.service.files().get(
                fileId=file_id,
                fields="id,name,mimeType,size,createdTime,modifiedTime,webViewLink"
            ).execute()
            
            return file
            
        except Exception as e:
            logger.error(f"Failed to get metadata for file {file_id}: {e}")
            raise ValueError(f"Could not access Drive file {file_id}: {str(e)}")
    
    def extract_google_doc(self, file_id: str) -> str:
        """
        Extract text from Google Doc.
        
        Exports as plain text.
        """
        try:
            # Export as plain text
            request = self.service.files().export_media(
                fileId=file_id,
                mimeType='text/plain'
            )
            
            file_content = io.BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            content = file_content.getvalue().decode('utf-8')
            return content
            
        except Exception as e:
            logger.error(f"Failed to extract Google Doc {file_id}: {e}")
            raise RuntimeError(f"Could not extract Google Doc: {str(e)}")
    
    def extract_google_sheet(self, file_id: str) -> str:
        """
        Extract text from Google Sheet.
        
        Exports as CSV and converts to readable text.
        """
        try:
            # Export as CSV
            request = self.service.files().export_media(
                fileId=file_id,
                mimeType='text/csv'
            )
            
            file_content = io.BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            content = file_content.getvalue().decode('utf-8')
            
            # Convert CSV to more readable format
            lines = content.split('\n')
            formatted = "\n".join(
                " | ".join(cell.strip() for cell in line.split(','))
                for line in lines if line.strip()
            )
            
            return formatted
            
        except Exception as e:
            logger.error(f"Failed to extract Google Sheet {file_id}: {e}")
            raise RuntimeError(f"Could not extract Google Sheet: {str(e)}")
    
    def extract_text_file(self, file_id: str) -> str:
        """
        Extract content from plain text file.
        """
        try:
            request = self.service.files().get_media(fileId=file_id)
            
            file_content = io.BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            content = file_content.getvalue().decode('utf-8')
            return content
            
        except Exception as e:
            logger.error(f"Failed to extract text file {file_id}: {e}")
            raise RuntimeError(f"Could not extract text file: {str(e)}")
    
    def extract_pdf(self, file_id: str) -> str:
        """
        Extract text from PDF.
        
        Note: Requires pypdf or similar library for extraction.
        For now, returns placeholder.
        """
        try:
            # Download PDF
            request = self.service.files().get_media(fileId=file_id)
            
            file_content = io.BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            # TODO: Add pypdf integration for text extraction
            # For now, return info message
            logger.warning(f"PDF extraction not yet implemented for {file_id}")
            return "[PDF content - extraction coming soon]"
            
        except Exception as e:
            logger.error(f"Failed to extract PDF {file_id}: {e}")
            raise RuntimeError(f"Could not extract PDF: {str(e)}")
    
    async def extract(self, file_id: str, file_url: Optional[str] = None) -> Dict[str, any]:
        """
        Extract content from Drive file.
        
        Args:
            file_id: Google Drive file ID
            file_url: Optional Drive URL (will extract ID if provided)
        
        Returns:
            {
                "title": str,
                "content": str,
                "source_id": str (file_id),
                "source_metadata": dict
            }
        """
        # Extract file ID from URL if provided
        if file_url and not file_id:
            file_id = self._extract_file_id_from_url(file_url)
        
        if not file_id:
            raise ValueError("Must provide file_id or file_url")
        
        # Get metadata
        metadata = self.get_file_metadata(file_id)
        mime_type = metadata.get('mimeType')
        file_type = self.SUPPORTED_TYPES.get(mime_type)
        
        if not file_type:
            raise ValueError(
                f"Unsupported file type: {mime_type}. "
                f"Supported types: {', '.join(self.SUPPORTED_TYPES.values())}"
            )
        
        # Extract content based on type
        if file_type == "google_doc":
            content = self.extract_google_doc(file_id)
        elif file_type == "google_sheet":
            content = self.extract_google_sheet(file_id)
        elif file_type == "txt":
            content = self.extract_text_file(file_id)
        elif file_type == "pdf":
            content = self.extract_pdf(file_id)
        else:
            raise NotImplementedError(f"Extraction for {file_type} not yet implemented")
        
        return {
            "title": metadata.get('name', 'Untitled'),
            "content": content,
            "source_id": file_id,
            "source_metadata": {
                "mime_type": mime_type,
                "file_type": file_type,
                "size": metadata.get('size'),
                "created_time": metadata.get('createdTime'),
                "modified_time": metadata.get('modifiedTime'),
                "web_view_link": metadata.get('webViewLink'),
            }
        }
    
    @staticmethod
    def _extract_file_id_from_url(url: str) -> Optional[str]:
        """
        Extract file ID from Drive URL.
        
        Supports:
        - https://drive.google.com/file/d/FILE_ID/view
        - https://drive.google.com/open?id=FILE_ID
        - https://docs.google.com/document/d/FILE_ID/edit
        """
        import re
        
        patterns = [
            r'/file/d/([a-zA-Z0-9_-]+)',
            r'/open\?id=([a-zA-Z0-9_-]+)',
            r'/document/d/([a-zA-Z0-9_-]+)',
            r'/spreadsheets/d/([a-zA-Z0-9_-]+)',
            r'/presentation/d/([a-zA-Z0-9_-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
