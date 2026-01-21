"""
Google Docs connector for proposal generation.

Uses the same service account credentials as Gmail/Calendar.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

# Lazy imports to avoid startup overhead
_docs_service = None
_drive_service = None


def _get_credentials():
    """Get credentials from environment."""
    from google.oauth2 import service_account
    
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if not creds_json:
        raise ValueError("GOOGLE_CREDENTIALS_JSON not configured")
    
    creds_data = json.loads(creds_json)
    
    scopes = [
        "https://www.googleapis.com/auth/documents",
        "https://www.googleapis.com/auth/drive",
    ]
    
    credentials = service_account.Credentials.from_service_account_info(
        creds_data, scopes=scopes
    )
    
    # Delegate to Casey's account
    delegated_user = os.getenv("GMAIL_DELEGATED_USER", "casey.l@pesti.io")
    return credentials.with_subject(delegated_user)


def get_docs_service():
    """Get Google Docs API service."""
    global _docs_service
    
    if _docs_service is None:
        from googleapiclient.discovery import build
        credentials = _get_credentials()
        _docs_service = build("docs", "v1", credentials=credentials)
    
    return _docs_service


def get_drive_service():
    """Get Google Drive API service."""
    global _drive_service
    
    if _drive_service is None:
        from googleapiclient.discovery import build
        credentials = _get_credentials()
        _drive_service = build("drive", "v3", credentials=credentials)
    
    return _drive_service


class GoogleDocsConnector:
    """Connector for creating and managing Google Docs proposals."""
    
    def __init__(self):
        self.template_folder_id = os.getenv("PROPOSAL_TEMPLATES_FOLDER_ID")
        self.proposals_folder_id = os.getenv("PROPOSALS_FOLDER_ID", os.getenv("PESTI_SALES_FOLDER_ID"))
    
    async def create_document(
        self,
        title: str,
        content: str,
        folder_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new Google Doc with the given content.
        
        Args:
            title: Document title
            content: Markdown or plain text content
            folder_id: Drive folder ID (optional)
            
        Returns:
            Dict with document_id, url, title
        """
        try:
            docs_service = get_docs_service()
            drive_service = get_drive_service()
            
            # Create empty document
            doc = docs_service.documents().create(
                body={"title": title}
            ).execute()
            
            document_id = doc.get("documentId")
            
            # Insert content
            if content:
                requests = self._build_insert_requests(content)
                if requests:
                    docs_service.documents().batchUpdate(
                        documentId=document_id,
                        body={"requests": requests}
                    ).execute()
            
            # Move to folder if specified
            target_folder = folder_id or self.proposals_folder_id
            if target_folder:
                try:
                    # Get current parent
                    file = drive_service.files().get(
                        fileId=document_id,
                        fields="parents"
                    ).execute()
                    
                    previous_parents = ",".join(file.get("parents", []))
                    
                    # Move to new folder
                    drive_service.files().update(
                        fileId=document_id,
                        addParents=target_folder,
                        removeParents=previous_parents,
                        fields="id, parents"
                    ).execute()
                except Exception as e:
                    logger.warning(f"Could not move to folder: {e}")
            
            doc_url = f"https://docs.google.com/document/d/{document_id}/edit"
            
            logger.info(f"Created document: {title} ({document_id})")
            
            return {
                "document_id": document_id,
                "url": doc_url,
                "title": title,
            }
            
        except Exception as e:
            logger.error(f"Error creating document: {e}")
            raise
    
    def _build_insert_requests(self, content: str) -> List[Dict[str, Any]]:
        """Build batch update requests from content.
        
        Handles basic markdown-like formatting.
        """
        requests = []
        
        # Insert text at the beginning
        requests.append({
            "insertText": {
                "location": {"index": 1},
                "text": content
            }
        })
        
        return requests
    
    async def clone_template(
        self,
        template_id: str,
        new_title: str,
        replacements: Dict[str, str],
    ) -> Dict[str, Any]:
        """Clone a template and replace placeholders.
        
        Args:
            template_id: Source template document ID
            new_title: Title for the new document
            replacements: Dict of {{placeholder}}: value
            
        Returns:
            Dict with new document info
        """
        try:
            drive_service = get_drive_service()
            docs_service = get_docs_service()
            
            # Copy the template
            copy = drive_service.files().copy(
                fileId=template_id,
                body={"name": new_title}
            ).execute()
            
            new_doc_id = copy.get("id")
            
            # Replace placeholders
            if replacements:
                requests = []
                for placeholder, value in replacements.items():
                    requests.append({
                        "replaceAllText": {
                            "containsText": {
                                "text": placeholder,
                                "matchCase": True,
                            },
                            "replaceText": value,
                        }
                    })
                
                if requests:
                    docs_service.documents().batchUpdate(
                        documentId=new_doc_id,
                        body={"requests": requests}
                    ).execute()
            
            # Move to proposals folder
            if self.proposals_folder_id:
                try:
                    file = drive_service.files().get(
                        fileId=new_doc_id,
                        fields="parents"
                    ).execute()
                    
                    previous_parents = ",".join(file.get("parents", []))
                    
                    drive_service.files().update(
                        fileId=new_doc_id,
                        addParents=self.proposals_folder_id,
                        removeParents=previous_parents,
                        fields="id, parents"
                    ).execute()
                except Exception as e:
                    logger.warning(f"Could not move to folder: {e}")
            
            doc_url = f"https://docs.google.com/document/d/{new_doc_id}/edit"
            
            return {
                "document_id": new_doc_id,
                "url": doc_url,
                "title": new_title,
            }
            
        except Exception as e:
            logger.error(f"Error cloning template: {e}")
            raise
    
    async def append_content(
        self,
        document_id: str,
        content: str,
    ) -> bool:
        """Append content to an existing document.
        
        Args:
            document_id: Target document ID
            content: Content to append
            
        Returns:
            True if successful
        """
        try:
            docs_service = get_docs_service()
            
            # Get current document to find end index
            doc = docs_service.documents().get(documentId=document_id).execute()
            
            # Find the end of the document
            content_elements = doc.get("body", {}).get("content", [])
            end_index = 1
            for element in content_elements:
                if "endIndex" in element:
                    end_index = element["endIndex"]
            
            # Insert at the end
            docs_service.documents().batchUpdate(
                documentId=document_id,
                body={
                    "requests": [{
                        "insertText": {
                            "location": {"index": end_index - 1},
                            "text": f"\n\n{content}"
                        }
                    }]
                }
            ).execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Error appending to document: {e}")
            return False
    
    async def get_document(self, document_id: str) -> Dict[str, Any]:
        """Get document metadata and content.
        
        Args:
            document_id: Document ID
            
        Returns:
            Document metadata and text content
        """
        try:
            docs_service = get_docs_service()
            
            doc = docs_service.documents().get(documentId=document_id).execute()
            
            # Extract text content
            text_content = ""
            for element in doc.get("body", {}).get("content", []):
                if "paragraph" in element:
                    for text_element in element["paragraph"].get("elements", []):
                        if "textRun" in text_element:
                            text_content += text_element["textRun"].get("content", "")
            
            return {
                "document_id": document_id,
                "title": doc.get("title"),
                "url": f"https://docs.google.com/document/d/{document_id}/edit",
                "content": text_content,
            }
            
        except Exception as e:
            logger.error(f"Error getting document: {e}")
            raise
    
    async def list_templates(self) -> List[Dict[str, Any]]:
        """List available proposal templates.
        
        Returns:
            List of template documents
        """
        templates = []
        
        if not self.template_folder_id:
            logger.warning("PROPOSAL_TEMPLATES_FOLDER_ID not configured")
            return templates
        
        try:
            drive_service = get_drive_service()
            
            results = drive_service.files().list(
                q=f"'{self.template_folder_id}' in parents and mimeType='application/vnd.google-apps.document'",
                fields="files(id, name, createdTime, modifiedTime)",
                pageSize=50,
            ).execute()
            
            for file in results.get("files", []):
                templates.append({
                    "id": file["id"],
                    "name": file["name"],
                    "created": file.get("createdTime"),
                    "modified": file.get("modifiedTime"),
                    "url": f"https://docs.google.com/document/d/{file['id']}/edit",
                })
            
            return templates
            
        except Exception as e:
            logger.error(f"Error listing templates: {e}")
            return templates


# Singleton instance
_connector: Optional[GoogleDocsConnector] = None


def get_google_docs_connector() -> GoogleDocsConnector:
    """Get singleton Google Docs connector."""
    global _connector
    if _connector is None:
        _connector = GoogleDocsConnector()
    return _connector
