"""
Agenda API Routes.

Endpoints for daily agenda generation.
"""

import logging
from typing import Dict, Any
from datetime import datetime
from fastapi import APIRouter

from src.agents.agenda_generator import get_agenda_generator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/agenda", tags=["agenda"])


@router.get("/today")
async def get_today_agenda() -> Dict[str, Any]:
    """Get today's agenda."""
    generator = get_agenda_generator()
    agenda = await generator.generate_agenda()
    
    return agenda.to_dict()


@router.get("/date/{date_str}")
async def get_agenda_for_date(date_str: str) -> Dict[str, Any]:
    """Get agenda for a specific date.
    
    Args:
        date_str: Date in YYYY-MM-DD format
    """
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return {"error": "Invalid date format. Use YYYY-MM-DD"}
    
    generator = get_agenda_generator()
    agenda = await generator.generate_agenda(date=date)
    
    return agenda.to_dict()


@router.get("/summary")
async def get_agenda_summary() -> Dict[str, Any]:
    """Get a quick summary of today's priorities."""
    generator = get_agenda_generator()
    agenda = await generator.generate_agenda()
    
    urgent_tasks = [t for t in agenda.tasks if t.priority.value == "urgent"]
    high_tasks = [t for t in agenda.tasks if t.priority.value == "high"]
    
    return {
        "date": agenda.date,
        "total_tasks": len(agenda.tasks),
        "urgent_count": len(urgent_tasks),
        "high_priority_count": len(high_tasks),
        "summary": agenda.summary,
        "top_3_tasks": [t.to_dict() for t in agenda.tasks[:3]],
    }
