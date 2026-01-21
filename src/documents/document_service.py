"""
Document Service - Document Management
======================================
Handles document storage, versioning, and sharing.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional
import uuid
import hashlib


class DocumentType(str, Enum):
    """Document type."""
    PROPOSAL = "proposal"
    CONTRACT = "contract"
    PRESENTATION = "presentation"
    CASE_STUDY = "case_study"
    WHITEPAPER = "whitepaper"
    DATASHEET = "datasheet"
    BROCHURE = "brochure"
    QUOTE = "quote"
    INVOICE = "invoice"
    OTHER = "other"


class DocumentStatus(str, Enum):
    """Document status."""
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class SharePermission(str, Enum):
    """Share permission level."""
    VIEW = "view"
    DOWNLOAD = "download"
    EDIT = "edit"


@dataclass
class DocumentVersion:
    """A version of a document."""
    id: str
    version_number: int
    
    # File info
    file_name: str
    file_size: int  # bytes
    mime_type: str
    file_hash: str
    storage_path: str
    
    # Metadata
    notes: Optional[str] = None
    uploaded_by: Optional[str] = None
    
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DocumentShare:
    """A document share."""
    id: str
    document_id: str
    
    # Share target
    share_type: str = "link"  # link, email, user
    recipient_email: Optional[str] = None
    recipient_user_id: Optional[str] = None
    
    # Settings
    permission: SharePermission = SharePermission.VIEW
    expires_at: Optional[datetime] = None
    password_hash: Optional[str] = None
    
    # Tracking
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    
    # Token for link shares
    share_token: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    
    @property
    def is_expired(self) -> bool:
        """Check if share is expired."""
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False


@dataclass
class DocumentView:
    """A document view record."""
    id: str
    document_id: str
    
    # Viewer
    viewer_email: Optional[str] = None
    viewer_ip: Optional[str] = None
    share_id: Optional[str] = None
    
    # Engagement
    duration_seconds: int = 0
    pages_viewed: int = 0
    total_pages: int = 0
    
    viewed_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Document:
    """A document."""
    id: str
    name: str
    
    # Type and status
    document_type: DocumentType = DocumentType.OTHER
    status: DocumentStatus = DocumentStatus.ACTIVE
    
    # Folder
    folder_id: Optional[str] = None
    
    # Current version
    current_version: int = 1
    versions: list[DocumentVersion] = field(default_factory=list)
    
    # Shares
    shares: list[DocumentShare] = field(default_factory=list)
    
    # Views
    views: list[DocumentView] = field(default_factory=list)
    view_count: int = 0
    unique_viewers: int = 0
    
    # Metadata
    description: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    
    # Links
    deal_id: Optional[str] = None
    contact_id: Optional[str] = None
    account_id: Optional[str] = None
    
    # Permissions
    is_public: bool = False
    owner_id: Optional[str] = None
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def current_version_info(self) -> Optional[DocumentVersion]:
        """Get current version info."""
        for version in self.versions:
            if version.version_number == self.current_version:
                return version
        return None


@dataclass
class DocumentFolder:
    """A document folder."""
    id: str
    name: str
    
    # Hierarchy
    parent_id: Optional[str] = None
    path: str = "/"
    
    # Permissions
    owner_id: Optional[str] = None
    is_shared: bool = False
    
    # Metadata
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    
    document_count: int = 0
    subfolder_count: int = 0
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class DocumentService:
    """Service for document management."""
    
    def __init__(self):
        self.documents: dict[str, Document] = {}
        self.folders: dict[str, DocumentFolder] = {}
    
    # Folder operations
    async def create_folder(
        self,
        name: str,
        parent_id: Optional[str] = None,
        owner_id: Optional[str] = None,
        **kwargs
    ) -> DocumentFolder:
        """Create a folder."""
        path = "/"
        if parent_id:
            parent = self.folders.get(parent_id)
            if parent:
                path = f"{parent.path}{parent.name}/"
        
        folder = DocumentFolder(
            id=str(uuid.uuid4()),
            name=name,
            parent_id=parent_id,
            path=path,
            owner_id=owner_id,
            **kwargs
        )
        
        self.folders[folder.id] = folder
        
        # Update parent subfolder count
        if parent_id and parent_id in self.folders:
            self.folders[parent_id].subfolder_count += 1
        
        return folder
    
    async def get_folder(self, folder_id: str) -> Optional[DocumentFolder]:
        """Get a folder by ID."""
        return self.folders.get(folder_id)
    
    async def list_folders(
        self,
        parent_id: Optional[str] = None
    ) -> list[DocumentFolder]:
        """List folders."""
        folders = list(self.folders.values())
        
        if parent_id is not None:
            folders = [f for f in folders if f.parent_id == parent_id]
        else:
            folders = [f for f in folders if f.parent_id is None]
        
        folders.sort(key=lambda f: f.name)
        return folders
    
    async def delete_folder(self, folder_id: str) -> bool:
        """Delete a folder."""
        folder = self.folders.get(folder_id)
        if not folder:
            return False
        
        # Check if empty
        docs = [d for d in self.documents.values() if d.folder_id == folder_id]
        subfolders = [f for f in self.folders.values() if f.parent_id == folder_id]
        
        if docs or subfolders:
            return False  # Not empty
        
        del self.folders[folder_id]
        return True
    
    # Document CRUD
    async def create_document(
        self,
        name: str,
        file_name: str,
        file_size: int,
        mime_type: str,
        storage_path: str,
        document_type: DocumentType = DocumentType.OTHER,
        folder_id: Optional[str] = None,
        owner_id: Optional[str] = None,
        **kwargs
    ) -> Document:
        """Create a document."""
        document = Document(
            id=str(uuid.uuid4()),
            name=name,
            document_type=document_type,
            folder_id=folder_id,
            owner_id=owner_id,
            **kwargs
        )
        
        # Create initial version
        version = DocumentVersion(
            id=str(uuid.uuid4()),
            version_number=1,
            file_name=file_name,
            file_size=file_size,
            mime_type=mime_type,
            file_hash=hashlib.sha256(storage_path.encode()).hexdigest()[:32],
            storage_path=storage_path,
            uploaded_by=owner_id,
        )
        
        document.versions.append(version)
        self.documents[document.id] = document
        
        # Update folder document count
        if folder_id and folder_id in self.folders:
            self.folders[folder_id].document_count += 1
        
        return document
    
    async def get_document(self, document_id: str) -> Optional[Document]:
        """Get a document by ID."""
        return self.documents.get(document_id)
    
    async def update_document(
        self,
        document_id: str,
        updates: dict[str, Any]
    ) -> Optional[Document]:
        """Update a document."""
        document = self.documents.get(document_id)
        if not document:
            return None
        
        for key, value in updates.items():
            if hasattr(document, key) and key not in ["id", "versions", "shares", "views"]:
                setattr(document, key, value)
        
        document.updated_at = datetime.utcnow()
        return document
    
    async def delete_document(self, document_id: str) -> bool:
        """Delete (archive) a document."""
        document = self.documents.get(document_id)
        if not document:
            return False
        
        document.status = DocumentStatus.DELETED
        document.updated_at = datetime.utcnow()
        return True
    
    async def list_documents(
        self,
        folder_id: Optional[str] = None,
        document_type: Optional[DocumentType] = None,
        status: Optional[DocumentStatus] = None,
        search: Optional[str] = None,
        tags: Optional[list[str]] = None,
        limit: int = 100
    ) -> list[Document]:
        """List documents."""
        documents = list(self.documents.values())
        
        # Filter out deleted by default
        if status:
            documents = [d for d in documents if d.status == status]
        else:
            documents = [d for d in documents if d.status != DocumentStatus.DELETED]
        
        if folder_id is not None:
            documents = [d for d in documents if d.folder_id == folder_id]
        if document_type:
            documents = [d for d in documents if d.document_type == document_type]
        if search:
            search_lower = search.lower()
            documents = [d for d in documents if search_lower in d.name.lower()]
        if tags:
            documents = [d for d in documents if any(t in d.tags for t in tags)]
        
        documents.sort(key=lambda d: d.updated_at, reverse=True)
        return documents[:limit]
    
    # Version management
    async def add_version(
        self,
        document_id: str,
        file_name: str,
        file_size: int,
        mime_type: str,
        storage_path: str,
        notes: Optional[str] = None,
        uploaded_by: Optional[str] = None
    ) -> Optional[DocumentVersion]:
        """Add a new version."""
        document = self.documents.get(document_id)
        if not document:
            return None
        
        new_version_number = document.current_version + 1
        
        version = DocumentVersion(
            id=str(uuid.uuid4()),
            version_number=new_version_number,
            file_name=file_name,
            file_size=file_size,
            mime_type=mime_type,
            file_hash=hashlib.sha256(storage_path.encode()).hexdigest()[:32],
            storage_path=storage_path,
            notes=notes,
            uploaded_by=uploaded_by,
        )
        
        document.versions.append(version)
        document.current_version = new_version_number
        document.updated_at = datetime.utcnow()
        
        return version
    
    async def get_version(
        self,
        document_id: str,
        version_number: int
    ) -> Optional[DocumentVersion]:
        """Get a specific version."""
        document = self.documents.get(document_id)
        if not document:
            return None
        
        for version in document.versions:
            if version.version_number == version_number:
                return version
        
        return None
    
    async def list_versions(self, document_id: str) -> list[DocumentVersion]:
        """List all versions of a document."""
        document = self.documents.get(document_id)
        if not document:
            return []
        
        versions = sorted(document.versions, key=lambda v: v.version_number, reverse=True)
        return versions
    
    # Sharing
    async def create_share(
        self,
        document_id: str,
        share_type: str = "link",
        recipient_email: Optional[str] = None,
        permission: SharePermission = SharePermission.VIEW,
        expires_in_days: Optional[int] = None,
        password: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> Optional[DocumentShare]:
        """Create a share link."""
        document = self.documents.get(document_id)
        if not document:
            return None
        
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        password_hash = None
        if password:
            password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        share = DocumentShare(
            id=str(uuid.uuid4()),
            document_id=document_id,
            share_type=share_type,
            recipient_email=recipient_email,
            permission=permission,
            expires_at=expires_at,
            password_hash=password_hash,
            created_by=created_by,
        )
        
        document.shares.append(share)
        document.updated_at = datetime.utcnow()
        
        return share
    
    async def get_share(self, share_token: str) -> Optional[tuple[Document, DocumentShare]]:
        """Get a document by share token."""
        for document in self.documents.values():
            for share in document.shares:
                if share.share_token == share_token:
                    return (document, share)
        return None
    
    async def validate_share(
        self,
        share_token: str,
        password: Optional[str] = None
    ) -> Optional[Document]:
        """Validate a share and return document."""
        result = await self.get_share(share_token)
        if not result:
            return None
        
        document, share = result
        
        if share.is_expired:
            return None
        
        if share.password_hash:
            if not password:
                return None
            if hashlib.sha256(password.encode()).hexdigest() != share.password_hash:
                return None
        
        # Update access tracking
        share.access_count += 1
        share.last_accessed = datetime.utcnow()
        
        return document
    
    async def revoke_share(self, document_id: str, share_id: str) -> bool:
        """Revoke a share."""
        document = self.documents.get(document_id)
        if not document:
            return False
        
        original = len(document.shares)
        document.shares = [s for s in document.shares if s.id != share_id]
        
        return len(document.shares) < original
    
    async def list_shares(self, document_id: str) -> list[DocumentShare]:
        """List shares for a document."""
        document = self.documents.get(document_id)
        if not document:
            return []
        
        return document.shares
    
    # View tracking
    async def record_view(
        self,
        document_id: str,
        viewer_email: Optional[str] = None,
        viewer_ip: Optional[str] = None,
        share_id: Optional[str] = None,
        duration_seconds: int = 0,
        pages_viewed: int = 0,
        total_pages: int = 0
    ) -> Optional[DocumentView]:
        """Record a document view."""
        document = self.documents.get(document_id)
        if not document:
            return None
        
        view = DocumentView(
            id=str(uuid.uuid4()),
            document_id=document_id,
            viewer_email=viewer_email,
            viewer_ip=viewer_ip,
            share_id=share_id,
            duration_seconds=duration_seconds,
            pages_viewed=pages_viewed,
            total_pages=total_pages,
        )
        
        document.views.append(view)
        document.view_count += 1
        
        # Track unique viewers
        if viewer_email:
            existing = set(v.viewer_email for v in document.views if v.viewer_email)
            document.unique_viewers = len(existing)
        
        return view
    
    async def get_view_analytics(
        self,
        document_id: str
    ) -> dict[str, Any]:
        """Get view analytics for a document."""
        document = self.documents.get(document_id)
        if not document:
            return {}
        
        views = document.views
        
        total_time = sum(v.duration_seconds for v in views)
        avg_time = total_time / len(views) if views else 0
        
        return {
            "total_views": document.view_count,
            "unique_viewers": document.unique_viewers,
            "total_view_time": total_time,
            "average_view_time": avg_time,
            "shares_count": len(document.shares),
            "recent_views": [
                {
                    "viewer_email": v.viewer_email,
                    "duration_seconds": v.duration_seconds,
                    "pages_viewed": v.pages_viewed,
                    "viewed_at": v.viewed_at.isoformat(),
                }
                for v in sorted(views, key=lambda x: x.viewed_at, reverse=True)[:10]
            ],
        }
    
    # Search
    async def search_documents(
        self,
        query: str,
        document_types: Optional[list[DocumentType]] = None,
        limit: int = 50
    ) -> list[Document]:
        """Search documents."""
        documents = list(self.documents.values())
        documents = [d for d in documents if d.status == DocumentStatus.ACTIVE]
        
        query_lower = query.lower()
        
        results = []
        for doc in documents:
            score = 0
            
            if query_lower in doc.name.lower():
                score += 10
            if doc.description and query_lower in doc.description.lower():
                score += 5
            if any(query_lower in tag.lower() for tag in doc.tags):
                score += 3
            
            if score > 0:
                if document_types and doc.document_type not in document_types:
                    continue
                results.append((score, doc))
        
        results.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in results[:limit]]


# Singleton instance
_document_service: Optional[DocumentService] = None


def get_document_service() -> DocumentService:
    """Get document service singleton."""
    global _document_service
    if _document_service is None:
        _document_service = DocumentService()
    return _document_service
