"""
Sequences API Routes.

Endpoints for managing multi-channel sequences.
"""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.sequences import get_sequence_engine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sequences", tags=["sequences"])


class CreateSequenceRequest(BaseModel):
    name: str
    description: Optional[str] = None
    target_persona: Optional[str] = None
    steps: List[Dict[str, Any]]


class EnrollContactRequest(BaseModel):
    sequence_id: str
    contact_email: str
    contact_name: Optional[str] = None
    start_immediately: bool = True


class ExecuteStepRequest(BaseModel):
    enrollment_id: str
    contact_data: Dict[str, Any]


@router.get("/list")
async def list_sequences() -> Dict[str, Any]:
    """List all available sequences."""
    engine = get_sequence_engine()
    sequences = engine.list_sequences()
    
    return {
        "sequences": sequences,
        "total": len(sequences),
    }


@router.get("/templates")
async def list_templates() -> Dict[str, Any]:
    """List pre-built sequence templates."""
    engine = get_sequence_engine()
    
    templates = []
    for seq in engine.sequences.values():
        if seq.id.startswith("template_"):
            templates.append(seq.to_dict())
    
    return {
        "templates": templates,
        "total": len(templates),
    }


@router.get("/{sequence_id}")
async def get_sequence(sequence_id: str) -> Dict[str, Any]:
    """Get a specific sequence."""
    engine = get_sequence_engine()
    sequence = engine.get_sequence(sequence_id)
    
    if not sequence:
        raise HTTPException(status_code=404, detail="Sequence not found")
    
    return sequence.to_dict()


@router.post("/create")
async def create_sequence(request: CreateSequenceRequest) -> Dict[str, Any]:
    """Create a new sequence."""
    try:
        engine = get_sequence_engine()
        
        sequence = await engine.create_sequence(
            name=request.name,
            steps=request.steps,
            description=request.description,
            target_persona=request.target_persona,
        )
        
        return {
            "status": "success",
            "sequence": sequence.to_dict(),
        }
        
    except Exception as e:
        logger.error(f"Error creating sequence: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/enroll")
async def enroll_contact(request: EnrollContactRequest) -> Dict[str, Any]:
    """Enroll a contact in a sequence."""
    try:
        engine = get_sequence_engine()
        
        enrollment = await engine.enroll_contact(
            sequence_id=request.sequence_id,
            contact_email=request.contact_email,
            contact_name=request.contact_name,
            start_immediately=request.start_immediately,
        )
        
        return {
            "status": "success",
            "enrollment": enrollment.to_dict(),
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error enrolling contact: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/enrollments")
async def list_enrollments(
    contact_email: Optional[str] = None,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    """List sequence enrollments."""
    engine = get_sequence_engine()
    enrollments = engine.get_enrollment_status(contact_email=contact_email)
    
    # Filter by status if provided
    if status:
        enrollments = [e for e in enrollments if e["status"] == status]
    
    return {
        "enrollments": enrollments,
        "total": len(enrollments),
    }


@router.get("/due")
async def get_due_steps() -> Dict[str, Any]:
    """Get all steps that are due for execution."""
    engine = get_sequence_engine()
    due_steps = await engine.get_due_steps()
    
    return {
        "due_steps": due_steps,
        "total": len(due_steps),
    }


@router.post("/execute")
async def execute_step(request: ExecuteStepRequest) -> Dict[str, Any]:
    """Execute the current step for an enrollment."""
    try:
        engine = get_sequence_engine()
        
        result = await engine.execute_step(
            enrollment_id=request.enrollment_id,
            contact_data=request.contact_data,
        )
        
        return {
            "status": "success",
            "result": result,
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error executing step: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mark-replied")
async def mark_replied(contact_email: str) -> Dict[str, Any]:
    """Mark a contact as having replied, stopping their sequences."""
    engine = get_sequence_engine()
    await engine.mark_replied(contact_email)
    
    return {
        "status": "success",
        "message": f"Marked {contact_email} as replied",
    }


@router.get("/for-persona/{persona}")
async def get_sequence_for_persona(persona: str) -> Dict[str, Any]:
    """Get the recommended sequence for a persona."""
    engine = get_sequence_engine()
    sequence = engine.get_sequence_for_persona(persona)
    
    if not sequence:
        raise HTTPException(status_code=404, detail=f"No sequence for persona: {persona}")
    
    return sequence.to_dict()
