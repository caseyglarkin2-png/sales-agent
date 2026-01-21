"""
Google Docs API Routes.

Endpoints for creating and managing proposals in Google Docs.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/docs", tags=["docs"])


class CreateDocumentRequest(BaseModel):
    title: str
    content: str
    folder_id: Optional[str] = None


class CloneTemplateRequest(BaseModel):
    template_id: str
    new_title: str
    replacements: Dict[str, str]


class AppendContentRequest(BaseModel):
    document_id: str
    content: str


@router.get("/status")
async def docs_status() -> Dict[str, Any]:
    """Check Google Docs connector status."""
    try:
        from src.connectors.google_docs import get_google_docs_connector
        connector = get_google_docs_connector()
        
        return {
            "status": "configured",
            "proposals_folder": connector.proposals_folder_id or "Not set",
            "templates_folder": connector.template_folder_id or "Not set",
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


@router.post("/create")
async def create_document(request: CreateDocumentRequest) -> Dict[str, Any]:
    """Create a new Google Doc."""
    try:
        from src.connectors.google_docs import get_google_docs_connector
        connector = get_google_docs_connector()
        
        result = await connector.create_document(
            title=request.title,
            content=request.content,
            folder_id=request.folder_id,
        )
        
        return {
            "status": "success",
            **result,
        }
        
    except Exception as e:
        logger.error(f"Error creating document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clone-template")
async def clone_template(request: CloneTemplateRequest) -> Dict[str, Any]:
    """Clone a template and replace placeholders."""
    try:
        from src.connectors.google_docs import get_google_docs_connector
        connector = get_google_docs_connector()
        
        result = await connector.clone_template(
            template_id=request.template_id,
            new_title=request.new_title,
            replacements=request.replacements,
        )
        
        return {
            "status": "success",
            **result,
        }
        
    except Exception as e:
        logger.error(f"Error cloning template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates")
async def list_templates() -> Dict[str, Any]:
    """List available proposal templates."""
    try:
        from src.connectors.google_docs import get_google_docs_connector
        connector = get_google_docs_connector()
        
        templates = await connector.list_templates()
        
        return {
            "templates": templates,
            "total": len(templates),
        }
        
    except Exception as e:
        logger.error(f"Error listing templates: {e}")
        return {
            "templates": [],
            "total": 0,
            "error": str(e),
        }


@router.get("/{document_id}")
async def get_document(document_id: str) -> Dict[str, Any]:
    """Get a document's content."""
    try:
        from src.connectors.google_docs import get_google_docs_connector
        connector = get_google_docs_connector()
        
        result = await connector.get_document(document_id)
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/append")
async def append_content(request: AppendContentRequest) -> Dict[str, Any]:
    """Append content to an existing document."""
    try:
        from src.connectors.google_docs import get_google_docs_connector
        connector = get_google_docs_connector()
        
        success = await connector.append_content(
            document_id=request.document_id,
            content=request.content,
        )
        
        if success:
            return {
                "status": "success",
                "message": "Content appended",
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to append content")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error appending content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/proposal")
async def create_proposal_doc(
    contact_email: str,
    contact_name: str,
    company: str,
    job_title: str,
) -> Dict[str, Any]:
    """Create a complete proposal document for a contact.
    
    This combines proposal generation with Google Docs creation.
    """
    try:
        from src.connectors.google_docs import get_google_docs_connector
        from src.proposals.proposal_generator import get_proposal_generator
        
        # Generate proposal content
        generator = get_proposal_generator()
        proposal = await generator.generate_proposal(
            contact_email=contact_email,
            contact_name=contact_name,
            company=company,
            job_title=job_title,
        )
        
        # Render to markdown
        markdown_content = generator.render_markdown(proposal)
        
        # Create Google Doc
        connector = get_google_docs_connector()
        doc_title = f"Pesti Proposal - {company} - {proposal.contact_name}"
        
        result = await connector.create_document(
            title=doc_title,
            content=markdown_content,
        )
        
        return {
            "status": "success",
            "proposal_id": proposal.id,
            "persona": proposal.persona,
            "document_id": result["document_id"],
            "document_url": result["url"],
            "title": doc_title,
        }
        
    except Exception as e:
        logger.error(f"Error creating proposal doc: {e}")
        raise HTTPException(status_code=500, detail=str(e))
