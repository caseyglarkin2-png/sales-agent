"""Google Drive connector for asset search.

Searches configured Drive folders for relevant assets (proposals,
case studies, reports) to include in outbound emails.
Sprint 67: Added retry for Google API calls
"""
import asyncio
import json
import os
import io
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError

from src.logger import get_logger

logger = get_logger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

T = TypeVar("T")


def with_drive_retry(
    max_retries: int = 3,
    backoff_base: float = 1.0,
    retryable_statuses: frozenset = frozenset({429, 500, 502, 503, 504}),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Retry decorator for Drive API calls.
    
    Handles rate limiting (429) and transient server errors.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_error = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except HttpError as e:
                    last_error = e
                    if e.resp.status in retryable_statuses and attempt < max_retries:
                        delay = backoff_base * (2 ** attempt)
                        logger.warning(
                            f"Drive API error {e.resp.status}, retry {attempt + 1}/{max_retries} "
                            f"in {delay:.1f}s"
                        )
                        await asyncio.sleep(delay)
                        continue
                    raise
                except Exception as e:
                    # Non-Google API errors (network, etc.)
                    last_error = e
                    if attempt < max_retries:
                        delay = backoff_base * (2 ** attempt)
                        logger.warning(
                            f"Drive API call error: {e}, retry {attempt + 1}/{max_retries} in {delay:.1f}s"
                        )
                        await asyncio.sleep(delay)
                        continue
                    raise
            raise last_error
        return wrapper
    return decorator


class DriveConnector:
    """Connector for Google Drive API with allowlist enforcement."""
    
    # Folder allowlist configuration
    FOLDER_CONFIG = {
        "pesti_sales": {
            "id": "0ACIUuJIAAt4IUk9PVA",
            "include_prefixes": [
                "CHAINge Proposals",
                "CP Client Reports", 
                "CP Proposals",
                "Manifest 2026",
            ],
            "exclude_prefixes": ["CP Closed"],
        },
        "charlie_pesti": {
            "id": "0AB_H1WFgMn8uUk9PVA",
            "include_all": True,
        },
    }
    
    def __init__(self, credentials=None):
        """Initialize Drive connector."""
        self.credentials = credentials
        self.service = None
    
    def _build_service(self) -> None:
        """Build Drive service from credentials."""
        if self.credentials and not self.service:
            self.service = build("drive", "v3", credentials=self.credentials)

    async def health_check(self) -> Dict[str, Any]:
        """Check Drive API connectivity and return health status.
        
        Uses about endpoint for a lightweight check.
        
        Returns:
            Dict with status, latency_ms, and optional error
        """
        import time
        
        start_time = time.time()
        
        if not self.credentials:
            return {
                "status": "unhealthy",
                "latency_ms": 0,
                "error": "No credentials configured",
            }
        
        try:
            if not self.service:
                self._build_service()
            
            # Lightweight call: get user info
            about = self.service.about().get(fields="user,storageQuota").execute()
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            user = about.get("user", {})
            return {
                "status": "healthy",
                "latency_ms": latency_ms,
                "user_email": user.get("emailAddress"),
                "error": None,
            }
        
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Drive health check failed: {e}")
            return {
                "status": "unhealthy",
                "latency_ms": latency_ms,
                "error": str(e),
            }
    
    @with_drive_retry(max_retries=3, backoff_base=1.0)
    async def search_assets(
        self,
        query: str,
        company_name: Optional[str] = None,
        max_results: int = 5,
    ) -> List[Dict[str, Any]]:
        """Search for relevant assets in allowlisted folders.
        
        Args:
            query: Search query (company name, topic, etc.)
            company_name: Company name for relevance scoring
            max_results: Maximum number of results
        
        Returns:
            List of matching assets with metadata
        """
        if not self.service:
            self._build_service()
        
        if not self.service:
            logger.warning("Drive service not available, returning empty results")
            return []
        
        all_results = []
        
        # Search each allowlisted folder
        for folder_key, config in self.FOLDER_CONFIG.items():
            folder_id = config.get("id") or os.environ.get(
                f"{folder_key.upper()}_FOLDER_ID"
            )
            
            if not folder_id:
                logger.warning(f"No folder ID for {folder_key}")
                continue
            
            try:
                results = await self._search_folder(
                    folder_id, query, config, max_results
                )
                all_results.extend(results)
            except Exception as e:
                logger.error(f"Error searching folder {folder_key}: {e}")
        
        # Sort by relevance and limit
        all_results.sort(key=lambda x: x.get("relevance", 0), reverse=True)
        return all_results[:max_results]
    
    async def _search_folder(
        self,
        folder_id: str,
        query: str,
        config: Dict[str, Any],
        max_results: int,
    ) -> List[Dict[str, Any]]:
        """Search within a specific folder."""
        # Build Drive query
        drive_query = f"'{folder_id}' in parents and trashed = false"
        if query:
            drive_query += f" and fullText contains '{query}'"
        
        try:
            response = self.service.files().list(
                q=drive_query,
                spaces="drive",
                fields="files(id, name, mimeType, webViewLink, modifiedTime, parents)",
                pageSize=max_results * 2,  # Get extra for filtering
            ).execute()
            
            files = response.get("files", [])
            results = []
            
            for file in files:
                # Apply allowlist filters
                if not self._is_allowed(file, config):
                    continue
                
                results.append({
                    "id": file["id"],
                    "name": file["name"],
                    "type": self._get_asset_type(file["mimeType"]),
                    "link": file.get("webViewLink", ""),
                    "modified": file.get("modifiedTime", ""),
                    "relevance": self._calculate_relevance(file, query),
                })
            
            return results
        
        except Exception as e:
            logger.error(f"Drive API error: {e}")
            return []
    
    def _is_allowed(self, file: Dict[str, Any], config: Dict[str, Any]) -> bool:
        """Check if file passes allowlist filters."""
        if config.get("include_all"):
            return True
        
        name = file.get("name", "")
        
        # Check exclude prefixes first
        for prefix in config.get("exclude_prefixes", []):
            if name.startswith(prefix):
                return False
        
        # Check include prefixes
        include_prefixes = config.get("include_prefixes", [])
        if include_prefixes:
            return any(name.startswith(p) for p in include_prefixes)
        
        return True
    
    def _get_asset_type(self, mime_type: str) -> str:
        """Determine asset type from MIME type."""
        if "pdf" in mime_type:
            return "pdf"
        elif "presentation" in mime_type or "powerpoint" in mime_type:
            return "presentation"
        elif "spreadsheet" in mime_type or "excel" in mime_type:
            return "spreadsheet"
        elif "document" in mime_type or "word" in mime_type:
            return "document"
        else:
            return "other"
    
    def _calculate_relevance(self, file: Dict[str, Any], query: str) -> float:
        """Calculate relevance score for a file."""
        name = file.get("name", "").lower()
        query_lower = query.lower() if query else ""
        
        score = 0.5  # Base score
        
        # Boost for query match in name
        if query_lower and query_lower in name:
            score += 0.3
        
        # Boost for recent files
        # (would need date parsing, simplified here)
        
        # Boost for certain file types
        if file.get("mimeType", "").endswith("pdf"):
            score += 0.1
        
        return min(score, 1.0)
    
    async def get_file_link(self, file_id: str) -> Optional[str]:
        """Get shareable link for a file."""
        if not self.service:
            self._build_service()
        
        if not self.service:
            return None
            
        return None

    async def get_file_content(self, file_id: str, mime_type: Optional[str] = None) -> str:
        """Download file content (text only)."""
        if not self.service:
            self._build_service()
            
        if not self.service:
            return ""

        try:
            # If mime_type not provided, fetch it
            if not mime_type:
                file = self.service.files().get(fileId=file_id, fields="mimeType").execute()
                mime_type = file.get("mimeType")

            content = ""
            
            # Case 1: Google Doc -> Export to plain text
            if mime_type == "application/vnd.google-apps.document":
                request = self.service.files().export_media(
                    fileId=file_id, mimeType="text/plain"
                )
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
                content = fh.getvalue().decode("utf-8")
                
            # Case 2: Plain Text / Unknown -> Try direct download
            else:
                # Basic text download attempt
                request = self.service.files().get_media(fileId=file_id)
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
                
                # Try decoding as text, skip if binary
                try:
                    content = fh.getvalue().decode("utf-8")
                except UnicodeDecodeError:
                    return "[Binary Content - Skipped]"

            return content

        except Exception as e:
            logger.error(f"Error downloading file {file_id}: {e}")
            return f"[Error downloading: {str(e)}]"

        
        try:
            file = self.service.files().get(
                fileId=file_id,
                fields="webViewLink"
            ).execute()
            return file.get("webViewLink")
        except Exception as e:
            logger.error(f"Error getting file link: {e}")
            return None


def create_drive_connector() -> DriveConnector:
    """Create a DriveConnector with credentials from environment."""
    import base64
    creds_file = os.environ.get("GOOGLE_CREDENTIALS_FILE")
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    delegated_user = os.environ.get("GMAIL_DELEGATED_USER")
    
    credentials = None
    
    if creds_file and os.path.exists(creds_file):
        credentials = service_account.Credentials.from_service_account_file(
            creds_file, scopes=SCOPES
        )
        if delegated_user:
            credentials = credentials.with_subject(delegated_user)
    elif creds_json:
        # Try to decode base64 first, fall back to raw JSON
        try:
            decoded = base64.b64decode(creds_json).decode('utf-8')
            creds_data = json.loads(decoded)
        except Exception:
            # Not base64, try raw JSON
            creds_data = json.loads(creds_json)
        credentials = service_account.Credentials.from_service_account_info(
            creds_data, scopes=SCOPES
        )
        if delegated_user:
            credentials = credentials.with_subject(delegated_user)
    
    return DriveConnector(credentials=credentials)
