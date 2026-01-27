"""Google Drive API endpoints.

Sprint 35: Drive Integration & File Context
Provides API endpoints for browsing and accessing Google Drive files.
"""
import os
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import get_db
from src.auth.decorators import get_current_user_optional
from src.models.user import User
from src.oauth_manager import TokenManager
from src.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/drive", tags=["Google Drive"])


# ============================================================================
# Pydantic Models
# ============================================================================

class DriveFile(BaseModel):
    """A Google Drive file."""
    id: str
    name: str
    mime_type: str
    web_view_link: Optional[str] = None
    icon_link: Optional[str] = None
    modified_time: Optional[str] = None
    size: Optional[int] = None
    parents: Optional[List[str]] = None
    is_folder: bool = False


class DriveFolder(BaseModel):
    """A Google Drive folder."""
    id: str
    name: str
    parent_id: Optional[str] = None
    children_count: int = 0


class FileContent(BaseModel):
    """Extracted content from a file."""
    file_id: str
    file_name: str
    mime_type: str
    content: str
    content_type: str = "text"  # text, markdown, html
    word_count: int = 0


class DriveSearchRequest(BaseModel):
    """Request to search Drive."""
    query: str = Field(..., min_length=1, max_length=500)
    folder_id: Optional[str] = None
    file_types: Optional[List[str]] = None
    max_results: int = Field(20, ge=1, le=100)


# ============================================================================
# Drive Service Helper
# ============================================================================

async def get_drive_service(user_id: Optional[UUID], db: AsyncSession):
    """Get Drive service using user's OAuth token."""
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    
    if not user_id:
        logger.warning("No user ID provided for Drive access")
        return None
    
    try:
        token_manager = TokenManager(db)
        token_data = await token_manager.get_valid_token(user_id, "google")
        
        if not token_data:
            logger.warning(f"No valid Google token for user {user_id}")
            return None
        
        credentials = Credentials(
            token=token_data.get("access_token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.environ.get("GOOGLE_CLIENT_ID"),
            client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
        )
        
        service = build("drive", "v3", credentials=credentials)
        return service
        
    except Exception as e:
        logger.error(f"Failed to get Drive service: {e}")
        return None


async def get_drive_service_fallback():
    """Get Drive service using service account (fallback)."""
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if not creds_json:
        return None
    
    try:
        import json
        creds_data = json.loads(creds_json)
        credentials = service_account.Credentials.from_service_account_info(
            creds_data,
            scopes=["https://www.googleapis.com/auth/drive.readonly"]
        )
        service = build("drive", "v3", credentials=credentials)
        return service
    except Exception as e:
        logger.error(f"Failed to get Drive service (fallback): {e}")
        return None


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/folders", response_model=List[DriveFolder])
async def list_folders(
    parent_id: Optional[str] = Query(None, description="Parent folder ID, or 'root'"),
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """List folders in Drive."""
    service = await get_drive_service(user.id if user else None, db)
    if not service:
        service = await get_drive_service_fallback()
    
    if not service:
        raise HTTPException(status_code=503, detail="Drive service not available")
    
    try:
        # Build query
        query = "mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        if parent_id and parent_id != "root":
            query += f" and '{parent_id}' in parents"
        elif parent_id == "root":
            query += " and 'root' in parents"
        
        results = service.files().list(
            q=query,
            fields="files(id, name, parents)",
            orderBy="name",
            pageSize=100
        ).execute()
        
        folders = []
        for f in results.get("files", []):
            folders.append(DriveFolder(
                id=f["id"],
                name=f["name"],
                parent_id=f.get("parents", [None])[0] if f.get("parents") else None
            ))
        
        return folders
        
    except Exception as e:
        logger.error(f"Failed to list folders: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files", response_model=List[DriveFile])
async def list_files(
    folder_id: Optional[str] = Query(None, description="Folder ID to list files from"),
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """List files in a folder."""
    service = await get_drive_service(user.id if user else None, db)
    if not service:
        service = await get_drive_service_fallback()
    
    if not service:
        raise HTTPException(status_code=503, detail="Drive service not available")
    
    try:
        query = "trashed = false"
        if folder_id:
            query += f" and '{folder_id}' in parents"
        
        results = service.files().list(
            q=query,
            fields="files(id, name, mimeType, webViewLink, iconLink, modifiedTime, size, parents)",
            orderBy="modifiedTime desc",
            pageSize=50
        ).execute()
        
        files = []
        for f in results.get("files", []):
            files.append(DriveFile(
                id=f["id"],
                name=f["name"],
                mime_type=f["mimeType"],
                web_view_link=f.get("webViewLink"),
                icon_link=f.get("iconLink"),
                modified_time=f.get("modifiedTime"),
                size=int(f["size"]) if f.get("size") else None,
                parents=f.get("parents"),
                is_folder=f["mimeType"] == "application/vnd.google-apps.folder"
            ))
        
        return files
        
    except Exception as e:
        logger.error(f"Failed to list files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/file/{file_id}", response_model=DriveFile)
async def get_file(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """Get file metadata."""
    service = await get_drive_service(user.id if user else None, db)
    if not service:
        service = await get_drive_service_fallback()
    
    if not service:
        raise HTTPException(status_code=503, detail="Drive service not available")
    
    try:
        f = service.files().get(
            fileId=file_id,
            fields="id, name, mimeType, webViewLink, iconLink, modifiedTime, size, parents"
        ).execute()
        
        return DriveFile(
            id=f["id"],
            name=f["name"],
            mime_type=f["mimeType"],
            web_view_link=f.get("webViewLink"),
            icon_link=f.get("iconLink"),
            modified_time=f.get("modifiedTime"),
            size=int(f["size"]) if f.get("size") else None,
            parents=f.get("parents"),
            is_folder=f["mimeType"] == "application/vnd.google-apps.folder"
        )
        
    except Exception as e:
        logger.error(f"Failed to get file {file_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/file/{file_id}/content", response_model=FileContent)
async def get_file_content(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """Extract content from a file."""
    import io
    from googleapiclient.http import MediaIoBaseDownload
    
    service = await get_drive_service(user.id if user else None, db)
    if not service:
        service = await get_drive_service_fallback()
    
    if not service:
        raise HTTPException(status_code=503, detail="Drive service not available")
    
    try:
        # Get file metadata
        file_meta = service.files().get(
            fileId=file_id,
            fields="id, name, mimeType"
        ).execute()
        
        mime_type = file_meta["mimeType"]
        file_name = file_meta["name"]
        
        # Handle Google Docs (export as plain text)
        if mime_type == "application/vnd.google-apps.document":
            content = service.files().export(
                fileId=file_id,
                mimeType="text/plain"
            ).execute()
            text = content.decode("utf-8") if isinstance(content, bytes) else content
            
        # Handle Google Sheets (export as CSV)
        elif mime_type == "application/vnd.google-apps.spreadsheet":
            content = service.files().export(
                fileId=file_id,
                mimeType="text/csv"
            ).execute()
            text = content.decode("utf-8") if isinstance(content, bytes) else content
            
        # Handle Google Slides (export as plain text)
        elif mime_type == "application/vnd.google-apps.presentation":
            content = service.files().export(
                fileId=file_id,
                mimeType="text/plain"
            ).execute()
            text = content.decode("utf-8") if isinstance(content, bytes) else content
            
        # Handle text files
        elif mime_type.startswith("text/"):
            request = service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
            text = fh.getvalue().decode("utf-8")
            
        # Handle PDFs (basic extraction)
        elif mime_type == "application/pdf":
            # For now, return placeholder - full PDF extraction in Task 35.4
            text = f"[PDF content extraction for {file_name} - requires pdf library]"
            
        else:
            text = f"[Cannot extract text from {mime_type}]"
        
        word_count = len(text.split())
        
        return FileContent(
            file_id=file_id,
            file_name=file_name,
            mime_type=mime_type,
            content=text,
            word_count=word_count
        )
        
    except Exception as e:
        logger.error(f"Failed to get file content {file_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=List[DriveFile])
async def search_files(
    request: DriveSearchRequest,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """Search for files in Drive."""
    service = await get_drive_service(user.id if user else None, db)
    if not service:
        service = await get_drive_service_fallback()
    
    if not service:
        raise HTTPException(status_code=503, detail="Drive service not available")
    
    try:
        # Build query
        query = f"fullText contains '{request.query}' and trashed = false"
        
        if request.folder_id:
            query += f" and '{request.folder_id}' in parents"
        
        if request.file_types:
            type_queries = []
            for ft in request.file_types:
                if ft == "document":
                    type_queries.append("mimeType = 'application/vnd.google-apps.document'")
                elif ft == "spreadsheet":
                    type_queries.append("mimeType = 'application/vnd.google-apps.spreadsheet'")
                elif ft == "presentation":
                    type_queries.append("mimeType = 'application/vnd.google-apps.presentation'")
                elif ft == "pdf":
                    type_queries.append("mimeType = 'application/pdf'")
            if type_queries:
                query += f" and ({' or '.join(type_queries)})"
        
        results = service.files().list(
            q=query,
            fields="files(id, name, mimeType, webViewLink, iconLink, modifiedTime, size, parents)",
            orderBy="modifiedTime desc",
            pageSize=request.max_results
        ).execute()
        
        files = []
        for f in results.get("files", []):
            files.append(DriveFile(
                id=f["id"],
                name=f["name"],
                mime_type=f["mimeType"],
                web_view_link=f.get("webViewLink"),
                icon_link=f.get("iconLink"),
                modified_time=f.get("modifiedTime"),
                size=int(f["size"]) if f.get("size") else None,
                parents=f.get("parents"),
                is_folder=f["mimeType"] == "application/vnd.google-apps.folder"
            ))
        
        return files
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# HTMX-friendly endpoints
# ============================================================================

@router.get("/files/html")
async def list_files_html(
    folder_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """List files as HTML fragment for HTMX."""
    try:
        files = await list_files(folder_id, db, user)
        
        if not files:
            return HTMLResponse('<p class="text-gray-500 text-center py-4">No files found</p>')
        
        html_parts = ['<div class="space-y-2">']
        for f in files:
            icon = "📁" if f.is_folder else "📄"
            size_str = f"{f.size // 1024}KB" if f.size else ""
            
            if f.is_folder:
                html_parts.append(f'''
                <div class="flex items-center justify-between p-2 hover:bg-gray-50 rounded cursor-pointer"
                     hx-get="/api/drive/files/html?folder_id={f.id}"
                     hx-target="#file-list"
                     hx-swap="innerHTML">
                    <div class="flex items-center space-x-2">
                        <span>{icon}</span>
                        <span class="font-medium">{f.name}</span>
                    </div>
                </div>
                ''')
            else:
                html_parts.append(f'''
                <div class="flex items-center justify-between p-2 hover:bg-gray-50 rounded">
                    <div class="flex items-center space-x-2">
                        <span>{icon}</span>
                        <span>{f.name}</span>
                    </div>
                    <div class="flex items-center space-x-2 text-sm text-gray-500">
                        <span>{size_str}</span>
                        <button class="text-blue-600 hover:underline"
                                hx-post="/api/drive/attach"
                                hx-vals='{{"file_id": "{f.id}", "file_name": "{f.name}"}}'
                                hx-target="#attached-files"
                                hx-swap="beforeend">
                            Attach
                        </button>
                    </div>
                </div>
                ''')
        
        html_parts.append('</div>')
        return HTMLResponse(''.join(html_parts))
        
    except Exception as e:
        return HTMLResponse(f'<p class="text-red-500">Error: {str(e)}</p>', status_code=500)


@router.post("/attach")
async def attach_file(
    file_id: str = Query(...),
    file_name: str = Query(...),
):
    """Attach a file to the current context (HTMX)."""
    html = f'''
    <div class="flex items-center justify-between bg-blue-50 px-3 py-2 rounded mb-2" id="attached-{file_id}">
        <span class="text-sm">📎 {file_name}</span>
        <button class="text-red-500 hover:text-red-700 text-sm"
                hx-delete="/api/drive/detach?file_id={file_id}"
                hx-target="#attached-{file_id}"
                hx-swap="outerHTML">
            ✕
        </button>
        <input type="hidden" name="file_ids" value="{file_id}">
    </div>
    '''
    return HTMLResponse(html)


@router.delete("/detach")
async def detach_file(file_id: str = Query(...)):
    """Remove an attached file (HTMX)."""
    return HTMLResponse("")  # Empty response removes the element
