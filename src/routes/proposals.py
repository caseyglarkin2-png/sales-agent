"""API routes for proposal generation."""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from src.proposals.proposal_generator import get_proposal_generator
from src.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/proposals", tags=["proposals"])


class GenerateProposalRequest(BaseModel):
    """Request to generate a proposal."""
    contact_email: str
    contact_name: str
    company_name: str
    job_title: str = ""
    custom_context: Optional[Dict[str, Any]] = None


class BatchProposalRequest(BaseModel):
    """Request to generate multiple proposals."""
    contacts: List[Dict[str, Any]]


# In-memory storage for generated proposals (would use DB in production)
_proposals_store: Dict[str, Dict[str, Any]] = {}


@router.post("/generate")
async def generate_proposal(request: GenerateProposalRequest) -> Dict[str, Any]:
    """Generate a personalized proposal for a contact."""
    try:
        generator = get_proposal_generator()
        
        proposal = await generator.generate_proposal(
            contact_email=request.contact_email,
            contact_name=request.contact_name,
            company_name=request.company_name,
            job_title=request.job_title,
            custom_context=request.custom_context,
        )
        
        # Store proposal
        _proposals_store[proposal.id] = proposal.model_dump()
        
        # Render markdown preview
        markdown = generator.render_as_markdown(proposal)
        
        return {
            "status": "success",
            "proposal": proposal.model_dump(),
            "markdown_preview": markdown,
        }
    except Exception as e:
        logger.error(f"Error generating proposal: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{proposal_id}")
async def get_proposal(proposal_id: str) -> Dict[str, Any]:
    """Get a previously generated proposal."""
    if proposal_id not in _proposals_store:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    return {
        "status": "success",
        "proposal": _proposals_store[proposal_id],
    }


@router.get("/{proposal_id}/markdown", response_class=PlainTextResponse)
async def get_proposal_markdown(proposal_id: str) -> str:
    """Get proposal as markdown."""
    if proposal_id not in _proposals_store:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    from src.proposals.proposal_generator import Proposal
    
    proposal = Proposal(**_proposals_store[proposal_id])
    generator = get_proposal_generator()
    
    return generator.render_as_markdown(proposal)


@router.get("/")
async def list_proposals() -> Dict[str, Any]:
    """List all generated proposals."""
    return {
        "status": "success",
        "count": len(_proposals_store),
        "proposals": [
            {
                "id": p["id"],
                "contact_email": p["contact_email"],
                "company_name": p["company_name"],
                "persona": p["persona"],
                "created_at": p["created_at"],
            }
            for p in _proposals_store.values()
        ],
    }


@router.delete("/{proposal_id}")
async def delete_proposal(proposal_id: str) -> Dict[str, Any]:
    """Delete a proposal."""
    if proposal_id not in _proposals_store:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    del _proposals_store[proposal_id]
    
    return {
        "status": "deleted",
        "proposal_id": proposal_id,
    }


@router.get("/templates/list")
async def list_templates() -> Dict[str, Any]:
    """List available proposal templates."""
    from src.proposals.proposal_generator import PROPOSAL_TEMPLATES, DEFAULT_TEMPLATE
    
    templates = []
    for persona, template in PROPOSAL_TEMPLATES.items():
        templates.append({
            "id": template.id,
            "name": template.name,
            "persona": persona.value,
            "section_count": len(template.sections),
            "pricing_tiers": [t["name"] for t in template.pricing_tiers],
        })
    
    templates.append({
        "id": DEFAULT_TEMPLATE.id,
        "name": DEFAULT_TEMPLATE.name,
        "persona": "general",
        "section_count": len(DEFAULT_TEMPLATE.sections),
        "pricing_tiers": [t["name"] for t in DEFAULT_TEMPLATE.pricing_tiers],
    })
    
    return {
        "status": "success",
        "templates": templates,
    }
