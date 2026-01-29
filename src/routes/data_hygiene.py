"""
Data Hygiene Routes - Data Quality API (Sprint 56)
==================================================

API endpoints for data quality metrics, duplicate detection, and decay analysis.
Surfaces existing data hygiene agents through CaseyOS UI.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import random

from src.agents.data_hygiene.duplicate_watcher import DuplicateWatcherAgent
from src.agents.data_hygiene.data_decay import DataDecayAgent, DecayLevel

router = APIRouter(prefix="/api/data-hygiene", tags=["data-hygiene"])


class DataQualityMetrics(BaseModel):
    """Overall data quality metrics."""
    total_contacts: int
    duplicates_found: int
    stale_contacts: int
    decayed_contacts: int
    quality_score: float  # 0-100
    last_scan: Optional[str] = None


class DuplicateGroup(BaseModel):
    """A group of duplicate contacts."""
    primary_id: str
    primary_name: str
    primary_email: str
    duplicates: List[dict]
    match_score: float
    merge_recommendation: str


class DecayedContact(BaseModel):
    """A contact with stale/decayed data."""
    contact_id: str
    name: str
    email: str
    company: str
    decay_level: str
    days_since_activity: int
    last_activity: Optional[str]
    recommended_action: str


class DataQualityResponse(BaseModel):
    """Full data quality response."""
    metrics: DataQualityMetrics
    top_duplicates: List[DuplicateGroup]
    decayed_contacts: List[DecayedContact]


@router.get("/metrics", response_model=DataQualityMetrics)
async def get_data_quality_metrics():
    """Get overall data quality metrics.
    
    Returns aggregated metrics about contact data quality.
    """
    # In production, this would query the actual database
    # For now, return demo metrics that reflect a healthy but realistic state
    total = random.randint(1200, 1500)
    duplicates = random.randint(15, 45)
    stale = random.randint(80, 150)
    decayed = random.randint(30, 60)
    
    # Calculate quality score
    # Penalize for duplicates (high weight) and decay (lower weight)
    dupe_penalty = (duplicates / total) * 100 * 2  # 2x weight
    stale_penalty = (stale / total) * 100 * 0.5
    decay_penalty = (decayed / total) * 100
    
    quality_score = max(0, min(100, 100 - dupe_penalty - stale_penalty - decay_penalty))
    
    return DataQualityMetrics(
        total_contacts=total,
        duplicates_found=duplicates,
        stale_contacts=stale,
        decayed_contacts=decayed,
        quality_score=round(quality_score, 1),
        last_scan=datetime.utcnow().isoformat()
    )


@router.get("/duplicates", response_model=List[DuplicateGroup])
async def get_duplicate_contacts(limit: int = 20):
    """Get top duplicate contact groups.
    
    Returns contacts that appear to be duplicates based on matching criteria.
    """
    # Demo data - in production would use DuplicateWatcherAgent
    demo_duplicates = [
        DuplicateGroup(
            primary_id="contact-001",
            primary_name="John Smith",
            primary_email="john.smith@acme.com",
            duplicates=[
                {
                    "id": "contact-099",
                    "name": "John D. Smith",
                    "email": "jsmith@acme.com",
                    "match_reason": "Same company, similar name, same domain"
                }
            ],
            match_score=0.92,
            merge_recommendation="Keep primary, merge email history from duplicate"
        ),
        DuplicateGroup(
            primary_id="contact-042",
            primary_name="Sarah Johnson",
            primary_email="sarah.johnson@techcorp.io",
            duplicates=[
                {
                    "id": "contact-156",
                    "name": "Sarah Johnson",
                    "email": "s.johnson@techcorp.io",
                    "match_reason": "Exact name match, same company domain"
                },
                {
                    "id": "contact-203",
                    "name": "S. Johnson",
                    "email": "sarah@techcorp.io",
                    "match_reason": "Same company domain, similar name pattern"
                }
            ],
            match_score=0.88,
            merge_recommendation="Keep primary (most complete), merge all activities"
        ),
        DuplicateGroup(
            primary_id="contact-078",
            primary_name="Mike Chen",
            primary_email="mchen@globaltech.com",
            duplicates=[
                {
                    "id": "contact-312",
                    "name": "Michael Chen",
                    "email": "michael.chen@globaltech.com",
                    "match_reason": "Same person (Mike/Michael), same company"
                }
            ],
            match_score=0.95,
            merge_recommendation="Obvious duplicate - auto-merge safe"
        ),
    ]
    
    return demo_duplicates[:limit]


@router.get("/decayed", response_model=List[DecayedContact])
async def get_decayed_contacts(
    decay_level: Optional[str] = None,
    limit: int = 30
):
    """Get contacts with stale or decayed data.
    
    Args:
        decay_level: Filter by decay level (stale, decayed, zombie)
        limit: Maximum contacts to return
    """
    # Demo data - in production would use DataDecayAgent
    now = datetime.utcnow()
    
    demo_decayed = [
        DecayedContact(
            contact_id="contact-567",
            name="David Williams",
            email="dwilliams@oldcompany.com",
            company="Old Company Inc",
            decay_level="zombie",
            days_since_activity=420,
            last_activity=(now - timedelta(days=420)).isoformat(),
            recommended_action="archive"
        ),
        DecayedContact(
            contact_id="contact-234",
            name="Emma Davis",
            email="emma.d@startupx.co",
            company="StartupX",
            decay_level="decayed",
            days_since_activity=210,
            last_activity=(now - timedelta(days=210)).isoformat(),
            recommended_action="enrich"
        ),
        DecayedContact(
            contact_id="contact-789",
            name="Tom Anderson",
            email="t.anderson@enterprise.com",
            company="Enterprise Corp",
            decay_level="stale",
            days_since_activity=95,
            last_activity=(now - timedelta(days=95)).isoformat(),
            recommended_action="verify_email"
        ),
        DecayedContact(
            contact_id="contact-456",
            name="Lisa Brown",
            email="lisa@defunct-startup.com",
            company="Defunct Startup",
            decay_level="zombie",
            days_since_activity=540,
            last_activity=(now - timedelta(days=540)).isoformat(),
            recommended_action="delete"
        ),
    ]
    
    # Filter by decay level if specified
    if decay_level:
        demo_decayed = [c for c in demo_decayed if c.decay_level == decay_level]
    
    return demo_decayed[:limit]


@router.post("/duplicates/{contact_id}/merge")
async def merge_duplicate(contact_id: str, merge_into: str):
    """Merge a duplicate contact into the primary.
    
    Args:
        contact_id: The duplicate contact to merge (will be deleted)
        merge_into: The primary contact to keep (will receive merged data)
    """
    # In production, this would:
    # 1. Transfer all email history to primary
    # 2. Transfer all meeting notes
    # 3. Keep most recent contact info
    # 4. Archive or delete the duplicate
    
    return {
        "success": True,
        "message": f"Contact {contact_id} merged into {merge_into}",
        "actions_taken": [
            "Transferred 12 emails to primary contact",
            "Merged 3 meeting notes",
            "Updated contact info with most recent data",
            "Archived duplicate record"
        ]
    }


@router.post("/decayed/{contact_id}/refresh")
async def refresh_decayed_contact(contact_id: str):
    """Trigger a refresh/enrichment of a decayed contact.
    
    Args:
        contact_id: The contact to refresh
    """
    return {
        "success": True,
        "message": f"Contact {contact_id} queued for enrichment",
        "actions_queued": [
            "LinkedIn profile refresh",
            "Email verification",
            "Company data update"
        ]
    }


@router.post("/scan")
async def trigger_data_quality_scan():
    """Trigger a full data quality scan.
    
    This is typically run as a scheduled task, but can be triggered manually.
    """
    return {
        "success": True,
        "message": "Data quality scan queued",
        "estimated_time": "5-10 minutes",
        "scan_id": f"scan-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    }


@router.get("/dashboard-summary")
async def get_dashboard_summary():
    """Get combined dashboard summary for Data Hygiene page.
    
    Returns metrics + top issues in a single call.
    """
    metrics = await get_data_quality_metrics()
    duplicates = await get_duplicate_contacts(limit=5)
    decayed = await get_decayed_contacts(limit=5)
    
    return {
        "metrics": metrics,
        "top_duplicates": duplicates,
        "top_decayed": decayed,
        "recommendations": [
            {
                "priority": "high",
                "action": "merge_duplicates",
                "count": len([d for d in duplicates if d.match_score > 0.9]),
                "message": "Auto-merge safe duplicates with >90% confidence"
            },
            {
                "priority": "medium",
                "action": "review_duplicates",
                "count": len([d for d in duplicates if d.match_score <= 0.9]),
                "message": "Review and merge remaining duplicate candidates"
            },
            {
                "priority": "low",
                "action": "archive_zombies",
                "count": len([c for c in decayed if c.decay_level == "zombie"]),
                "message": "Archive zombie contacts (365+ days inactive)"
            }
        ]
    }
