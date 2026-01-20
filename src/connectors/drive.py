"""Google Drive connector for asset search.

Searches configured Drive folders for relevant assets (proposals,
case studies, reports) to include in outbound emails.
"""
import json
import os
from typing import Any, Dict, List, Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build

from src.logger import get_logger

logger = get_logger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


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
    creds_file = os.environ.get("GOOGLE_CREDENTIALS_FILE")
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    
    credentials = None
    
    if creds_file and os.path.exists(creds_file):
        credentials = service_account.Credentials.from_service_account_file(
            creds_file, scopes=SCOPES
        )
    elif creds_json:
        creds_data = json.loads(creds_json)
        credentials = service_account.Credentials.from_service_account_info(
            creds_data, scopes=SCOPES
        )
    
    return DriveConnector(credentials=credentials)
