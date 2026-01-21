"""
Documents Routes - Document Management API
==========================================
REST API endpoints for document management.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Any, Optional
from pydantic import BaseModel
from datetime import datetime

from ..documents import (
    DocumentService,
    DocumentType,
    DocumentStatus,
    SharePermission,
    get_document_service,
)


router = APIRouter(prefix="/documents", tags=["Documents"])


# Request/Response models
class CreateFolderRequest(BaseModel):
    """Create folder request."""
    name: str
    parent_id: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None


class CreateDocumentRequest(BaseModel):
    """Create document request."""
    name: str
    file_name: str
    file_size: int
    mime_type: str
    storage_path: str
    document_type: Optional[str] = "other"
    folder_id: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[list[str]] = None
    deal_id: Optional[str] = None
    contact_id: Optional[str] = None
    account_id: Optional[str] = None


class UpdateDocumentRequest(BaseModel):
    """Update document request."""
    name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[list[str]] = None
    folder_id: Optional[str] = None


class AddVersionRequest(BaseModel):
    """Add version request."""
    file_name: str
    file_size: int
    mime_type: str
    storage_path: str
    notes: Optional[str] = None


class CreateShareRequest(BaseModel):
    """Create share request."""
    share_type: str = "link"
    recipient_email: Optional[str] = None
    permission: Optional[str] = "view"
    expires_in_days: Optional[int] = None
    password: Optional[str] = None


class ValidateShareRequest(BaseModel):
    """Validate share request."""
    password: Optional[str] = None


class RecordViewRequest(BaseModel):
    """Record view request."""
    viewer_email: Optional[str] = None
    duration_seconds: int = 0
    pages_viewed: int = 0
    total_pages: int = 0


def get_service() -> DocumentService:
    """Get document service instance."""
    return get_document_service()


# Folder endpoints
@router.post("/folders")
async def create_folder(request: CreateFolderRequest):
    """Create a folder."""
    service = get_service()
    
    folder = await service.create_folder(
        name=request.name,
        parent_id=request.parent_id,
        description=request.description,
        color=request.color,
    )
    
    return {
        "id": folder.id,
        "name": folder.name,
        "path": folder.path,
        "parent_id": folder.parent_id,
    }


@router.get("/folders")
async def list_folders(parent_id: Optional[str] = None):
    """List folders."""
    service = get_service()
    folders = await service.list_folders(parent_id=parent_id)
    
    return {
        "folders": [
            {
                "id": f.id,
                "name": f.name,
                "path": f.path,
                "parent_id": f.parent_id,
                "document_count": f.document_count,
                "subfolder_count": f.subfolder_count,
                "color": f.color,
            }
            for f in folders
        ]
    }


@router.get("/folders/{folder_id}")
async def get_folder(folder_id: str):
    """Get a folder."""
    service = get_service()
    folder = await service.get_folder(folder_id)
    
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    
    return {
        "id": folder.id,
        "name": folder.name,
        "path": folder.path,
        "parent_id": folder.parent_id,
        "description": folder.description,
        "document_count": folder.document_count,
        "subfolder_count": folder.subfolder_count,
        "created_at": folder.created_at.isoformat(),
    }


@router.delete("/folders/{folder_id}")
async def delete_folder(folder_id: str):
    """Delete a folder (must be empty)."""
    service = get_service()
    
    if not await service.delete_folder(folder_id):
        raise HTTPException(status_code=400, detail="Cannot delete folder (not empty or not found)")
    
    return {"success": True}


# Document CRUD
@router.post("")
async def create_document(request: CreateDocumentRequest):
    """Create a document."""
    service = get_service()
    
    try:
        doc_type = DocumentType(request.document_type) if request.document_type else DocumentType.OTHER
    except ValueError:
        doc_type = DocumentType.OTHER
    
    document = await service.create_document(
        name=request.name,
        file_name=request.file_name,
        file_size=request.file_size,
        mime_type=request.mime_type,
        storage_path=request.storage_path,
        document_type=doc_type,
        folder_id=request.folder_id,
        description=request.description,
        tags=request.tags or [],
        deal_id=request.deal_id,
        contact_id=request.contact_id,
        account_id=request.account_id,
    )
    
    return {
        "id": document.id,
        "name": document.name,
        "document_type": document.document_type.value,
        "current_version": document.current_version,
        "created_at": document.created_at.isoformat(),
    }


@router.get("")
async def list_documents(
    folder_id: Optional[str] = None,
    document_type: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    tags: Optional[str] = None,
    limit: int = Query(default=100, le=500)
):
    """List documents."""
    service = get_service()
    
    type_enum = None
    if document_type:
        try:
            type_enum = DocumentType(document_type)
        except ValueError:
            pass
    
    status_enum = None
    if status:
        try:
            status_enum = DocumentStatus(status)
        except ValueError:
            pass
    
    tag_list = tags.split(",") if tags else None
    
    documents = await service.list_documents(
        folder_id=folder_id,
        document_type=type_enum,
        status=status_enum,
        search=search,
        tags=tag_list,
        limit=limit
    )
    
    return {
        "documents": [
            {
                "id": d.id,
                "name": d.name,
                "document_type": d.document_type.value,
                "status": d.status.value,
                "current_version": d.current_version,
                "folder_id": d.folder_id,
                "view_count": d.view_count,
                "file_name": d.current_version_info.file_name if d.current_version_info else None,
                "file_size": d.current_version_info.file_size if d.current_version_info else None,
                "updated_at": d.updated_at.isoformat(),
            }
            for d in documents
        ],
        "total": len(documents)
    }


@router.get("/search")
async def search_documents(
    query: str,
    document_types: Optional[str] = None,
    limit: int = Query(default=50, le=200)
):
    """Search documents."""
    service = get_service()
    
    types = None
    if document_types:
        types = []
        for t in document_types.split(","):
            try:
                types.append(DocumentType(t))
            except ValueError:
                pass
    
    documents = await service.search_documents(
        query=query,
        document_types=types,
        limit=limit
    )
    
    return {
        "documents": [
            {
                "id": d.id,
                "name": d.name,
                "document_type": d.document_type.value,
                "description": d.description,
                "tags": d.tags,
            }
            for d in documents
        ],
        "total": len(documents)
    }


@router.get("/{document_id}")
async def get_document(document_id: str):
    """Get a document."""
    service = get_service()
    document = await service.get_document(document_id)
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    current = document.current_version_info
    
    return {
        "id": document.id,
        "name": document.name,
        "document_type": document.document_type.value,
        "status": document.status.value,
        "description": document.description,
        "tags": document.tags,
        "folder_id": document.folder_id,
        "current_version": document.current_version,
        "current_file": {
            "file_name": current.file_name,
            "file_size": current.file_size,
            "mime_type": current.mime_type,
            "storage_path": current.storage_path,
        } if current else None,
        "version_count": len(document.versions),
        "view_count": document.view_count,
        "unique_viewers": document.unique_viewers,
        "shares_count": len(document.shares),
        "deal_id": document.deal_id,
        "contact_id": document.contact_id,
        "account_id": document.account_id,
        "created_at": document.created_at.isoformat(),
        "updated_at": document.updated_at.isoformat(),
    }


@router.patch("/{document_id}")
async def update_document(document_id: str, request: UpdateDocumentRequest):
    """Update a document."""
    service = get_service()
    
    updates = request.model_dump(exclude_unset=True)
    document = await service.update_document(document_id, updates)
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {"success": True, "document_id": document_id}


@router.delete("/{document_id}")
async def delete_document(document_id: str):
    """Delete (archive) a document."""
    service = get_service()
    
    if not await service.delete_document(document_id):
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {"success": True}


# Versions
@router.post("/{document_id}/versions")
async def add_version(document_id: str, request: AddVersionRequest):
    """Add a new version."""
    service = get_service()
    
    version = await service.add_version(
        document_id=document_id,
        file_name=request.file_name,
        file_size=request.file_size,
        mime_type=request.mime_type,
        storage_path=request.storage_path,
        notes=request.notes,
    )
    
    if not version:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {
        "id": version.id,
        "version_number": version.version_number,
        "file_name": version.file_name,
        "created_at": version.created_at.isoformat(),
    }


@router.get("/{document_id}/versions")
async def list_versions(document_id: str):
    """List document versions."""
    service = get_service()
    versions = await service.list_versions(document_id)
    
    return {
        "versions": [
            {
                "id": v.id,
                "version_number": v.version_number,
                "file_name": v.file_name,
                "file_size": v.file_size,
                "notes": v.notes,
                "uploaded_by": v.uploaded_by,
                "created_at": v.created_at.isoformat(),
            }
            for v in versions
        ]
    }


@router.get("/{document_id}/versions/{version_number}")
async def get_version(document_id: str, version_number: int):
    """Get a specific version."""
    service = get_service()
    version = await service.get_version(document_id, version_number)
    
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    
    return {
        "id": version.id,
        "version_number": version.version_number,
        "file_name": version.file_name,
        "file_size": version.file_size,
        "mime_type": version.mime_type,
        "storage_path": version.storage_path,
        "notes": version.notes,
        "uploaded_by": version.uploaded_by,
        "created_at": version.created_at.isoformat(),
    }


# Sharing
@router.post("/{document_id}/shares")
async def create_share(document_id: str, request: CreateShareRequest):
    """Create a share link."""
    service = get_service()
    
    try:
        permission = SharePermission(request.permission) if request.permission else SharePermission.VIEW
    except ValueError:
        permission = SharePermission.VIEW
    
    share = await service.create_share(
        document_id=document_id,
        share_type=request.share_type,
        recipient_email=request.recipient_email,
        permission=permission,
        expires_in_days=request.expires_in_days,
        password=request.password,
    )
    
    if not share:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {
        "id": share.id,
        "share_token": share.share_token,
        "share_type": share.share_type,
        "permission": share.permission.value,
        "expires_at": share.expires_at.isoformat() if share.expires_at else None,
        "has_password": share.password_hash is not None,
    }


@router.get("/{document_id}/shares")
async def list_shares(document_id: str):
    """List shares for a document."""
    service = get_service()
    shares = await service.list_shares(document_id)
    
    return {
        "shares": [
            {
                "id": s.id,
                "share_token": s.share_token,
                "share_type": s.share_type,
                "recipient_email": s.recipient_email,
                "permission": s.permission.value,
                "access_count": s.access_count,
                "last_accessed": s.last_accessed.isoformat() if s.last_accessed else None,
                "expires_at": s.expires_at.isoformat() if s.expires_at else None,
                "is_expired": s.is_expired,
                "created_at": s.created_at.isoformat(),
            }
            for s in shares
        ]
    }


@router.delete("/{document_id}/shares/{share_id}")
async def revoke_share(document_id: str, share_id: str):
    """Revoke a share."""
    service = get_service()
    
    if not await service.revoke_share(document_id, share_id):
        raise HTTPException(status_code=404, detail="Share not found")
    
    return {"success": True}


# Public share access
@router.get("/share/{share_token}")
async def get_shared_document(share_token: str):
    """Get a shared document (public endpoint)."""
    service = get_service()
    result = await service.get_share(share_token)
    
    if not result:
        raise HTTPException(status_code=404, detail="Share not found")
    
    document, share = result
    
    if share.is_expired:
        raise HTTPException(status_code=410, detail="Share has expired")
    
    requires_password = share.password_hash is not None
    
    return {
        "document_name": document.name,
        "requires_password": requires_password,
        "permission": share.permission.value,
    }


@router.post("/share/{share_token}/validate")
async def validate_share(share_token: str, request: ValidateShareRequest):
    """Validate a share and get document details."""
    service = get_service()
    
    document = await service.validate_share(
        share_token=share_token,
        password=request.password
    )
    
    if not document:
        raise HTTPException(status_code=403, detail="Invalid share or password")
    
    current = document.current_version_info
    
    return {
        "id": document.id,
        "name": document.name,
        "document_type": document.document_type.value,
        "file": {
            "file_name": current.file_name,
            "file_size": current.file_size,
            "mime_type": current.mime_type,
        } if current else None,
    }


# View tracking
@router.post("/{document_id}/views")
async def record_view(document_id: str, request: RecordViewRequest):
    """Record a document view."""
    service = get_service()
    
    view = await service.record_view(
        document_id=document_id,
        viewer_email=request.viewer_email,
        duration_seconds=request.duration_seconds,
        pages_viewed=request.pages_viewed,
        total_pages=request.total_pages,
    )
    
    if not view:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {"success": True, "view_id": view.id}


@router.get("/{document_id}/analytics")
async def get_analytics(document_id: str):
    """Get view analytics for a document."""
    service = get_service()
    return await service.get_view_analytics(document_id)
