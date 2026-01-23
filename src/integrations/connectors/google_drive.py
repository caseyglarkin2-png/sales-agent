"""
Google Drive Integration Connector
====================================

Full Google Drive integration for file browsing and import.

Ship Ship Ship: Deploy file browser, test with real user OAuth.
"""

from typing import List, Optional, Dict
from datetime import datetime
from pydantic import BaseModel
from fastapi import HTTPException

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import logging

logger = logging.getLogger(__name__)


class DriveFile(BaseModel):
    """Represents a Google Drive file"""
    id: str
    name: str
    mime_type: str
    size: Optional[int] = None
    created_time: Optional[datetime] = None
    modified_time: Optional[datetime] = None
    web_view_link: Optional[str] = None
    thumbnail_link: Optional[str] = None
    is_folder: bool = False
    parent_id: Optional[str] = None


class DriveFolder(BaseModel):
    """Represents a Google Drive folder"""
    id: str
    name: str
    parent_id: Optional[str] = None
    created_time: Optional[datetime] = None


class GoogleDriveConnector:
    """
    Google Drive integration connector.
    
    Provides file browsing, search, and import functionality.
    """
    
    # Supported file types for voice training
    VOICE_TRAINING_TYPES = {
        "application/vnd.google-apps.document",
        "application/vnd.google-apps.spreadsheet",
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
    }
    
    def __init__(self, credentials: Credentials):
        """
        Initialize Drive connector.
        
        Args:
            credentials: User's Google OAuth credentials with Drive scope
        """
        self.credentials = credentials
        self.service = build('drive', 'v3', credentials=credentials)
    
    async def list_files(
        self,
        folder_id: Optional[str] = None,
        page_size: int = 50,
        page_token: Optional[str] = None,
        mime_type: Optional[str] = None
    ) -> Dict:
        """
        List files in Drive folder.
        
        Args:
            folder_id: Folder ID (None for root)
            page_size: Number of files per page
            page_token: Token for next page
            mime_type: Filter by MIME type
            
        Returns:
            Dict with files list and next_page_token
        """
        try:
            # Build query
            query_parts = []
            
            if folder_id:
                query_parts.append(f"'{folder_id}' in parents")
            else:
                # Root folder
                query_parts.append("'root' in parents")
            
            # Exclude trashed files
            query_parts.append("trashed = false")
            
            # Filter by MIME type if specified
            if mime_type:
                query_parts.append(f"mimeType = '{mime_type}'")
            
            query = " and ".join(query_parts)
            
            # Execute request
            results = self.service.files().list(
                q=query,
                pageSize=page_size,
                pageToken=page_token,
                fields="nextPageToken, files(id, name, mimeType, size, createdTime, modifiedTime, webViewLink, thumbnailLink, parents)",
                orderBy="modifiedTime desc"
            ).execute()
            
            files = results.get('files', [])
            
            # Convert to DriveFile objects
            drive_files = []
            for file in files:
                is_folder = file.get('mimeType') == 'application/vnd.google-apps.folder'
                
                drive_file = DriveFile(
                    id=file['id'],
                    name=file['name'],
                    mime_type=file.get('mimeType', ''),
                    size=file.get('size'),
                    created_time=file.get('createdTime'),
                    modified_time=file.get('modifiedTime'),
                    web_view_link=file.get('webViewLink'),
                    thumbnail_link=file.get('thumbnailLink'),
                    is_folder=is_folder,
                    parent_id=file.get('parents', [None])[0] if file.get('parents') else None
                )
                drive_files.append(drive_file)
            
            return {
                'files': [f.dict() for f in drive_files],
                'next_page_token': results.get('nextPageToken')
            }
            
        except Exception as e:
            logger.error(f"Failed to list Drive files: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to list Drive files: {str(e)}")
    
    async def get_folders(
        self,
        parent_id: Optional[str] = None
    ) -> List[DriveFolder]:
        """
        Get list of folders.
        
        Args:
            parent_id: Parent folder ID (None for root)
            
        Returns:
            List of DriveFolder objects
        """
        try:
            # Build query for folders only
            if parent_id:
                query = f"'{parent_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            else:
                query = "'root' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            
            results = self.service.files().list(
                q=query,
                fields="files(id, name, parents, createdTime)",
                orderBy="name"
            ).execute()
            
            folders = results.get('files', [])
            
            return [
                DriveFolder(
                    id=folder['id'],
                    name=folder['name'],
                    parent_id=folder.get('parents', [None])[0] if folder.get('parents') else None,
                    created_time=folder.get('createdTime')
                )
                for folder in folders
            ]
            
        except Exception as e:
            logger.error(f"Failed to get Drive folders: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get folders: {str(e)}")
    
    async def search_files(
        self,
        query: str,
        file_types_only: bool = True,
        page_size: int = 25
    ) -> List[DriveFile]:
        """
        Search for files in Drive.
        
        Args:
            query: Search query (file name)
            file_types_only: Only return supported file types
            page_size: Max results
            
        Returns:
            List of matching DriveFile objects
        """
        try:
            # Build search query
            search_parts = [
                f"name contains '{query}'",
                "trashed = false"
            ]
            
            if file_types_only:
                # Only search for supported file types
                mime_conditions = " or ".join([
                    f"mimeType = '{mime}'"
                    for mime in self.VOICE_TRAINING_TYPES
                ])
                search_parts.append(f"({mime_conditions})")
            
            search_query = " and ".join(search_parts)
            
            results = self.service.files().list(
                q=search_query,
                pageSize=page_size,
                fields="files(id, name, mimeType, size, createdTime, modifiedTime, webViewLink, thumbnailLink)",
                orderBy="modifiedTime desc"
            ).execute()
            
            files = results.get('files', [])
            
            return [
                DriveFile(
                    id=file['id'],
                    name=file['name'],
                    mime_type=file.get('mimeType', ''),
                    size=file.get('size'),
                    created_time=file.get('createdTime'),
                    modified_time=file.get('modifiedTime'),
                    web_view_link=file.get('webViewLink'),
                    thumbnail_link=file.get('thumbnailLink'),
                    is_folder=False
                )
                for file in files
            ]
            
        except Exception as e:
            logger.error(f"Failed to search Drive files: {e}")
            raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
    
    async def get_file_info(self, file_id: str) -> DriveFile:
        """
        Get detailed info about a specific file.
        
        Args:
            file_id: Google Drive file ID
            
        Returns:
            DriveFile object
        """
        try:
            file = self.service.files().get(
                fileId=file_id,
                fields="id, name, mimeType, size, createdTime, modifiedTime, webViewLink, thumbnailLink, parents"
            ).execute()
            
            is_folder = file.get('mimeType') == 'application/vnd.google-apps.folder'
            
            return DriveFile(
                id=file['id'],
                name=file['name'],
                mime_type=file.get('mimeType', ''),
                size=file.get('size'),
                created_time=file.get('createdTime'),
                modified_time=file.get('modifiedTime'),
                web_view_link=file.get('webViewLink'),
                thumbnail_link=file.get('thumbnailLink'),
                is_folder=is_folder,
                parent_id=file.get('parents', [None])[0] if file.get('parents') else None
            )
            
        except Exception as e:
            logger.error(f"Failed to get file info {file_id}: {e}")
            raise HTTPException(status_code=404, detail=f"File not found: {str(e)}")
    
    def is_supported_file(self, mime_type: str) -> bool:
        """Check if file type is supported for voice training"""
        return mime_type in self.VOICE_TRAINING_TYPES
