"""HubSpot Deep Sync Celery Task - Sprint 65.1.

Syncs enhanced contact properties from HubSpot:
- lifecycle_stage
- lead_status
- recent_deal_amount
- num_contacted_times
- analytics_source
"""
import asyncio
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, update

from src.celery_app import celery_app
from src.connectors.hubspot import create_hubspot_connector
from src.db import get_session
from src.logger import get_logger
from src.models.hubspot import HubSpotContact, HubSpotCompany, HubSpotDeal

logger = get_logger(__name__)


# Enhanced properties to sync
ENHANCED_CONTACT_PROPERTIES = [
    "lifecyclestage",
    "hs_lead_status",
    "num_contacted_times",
    "hs_analytics_source",
    "hs_analytics_source_data_1",
    "hs_analytics_source_data_2",
    "recent_deal_amount",
    "num_associated_deals",
    "total_revenue",
    "jobtitle",
    "phone",
    "mobilephone",
    "hs_email_last_open_date",
    "hs_email_last_reply_date",
    "notes_last_updated",
    "hs_sequences_actively_enrolled_count",
]

ENHANCED_COMPANY_PROPERTIES = [
    "industry",
    "annualrevenue",
    "numberofemployees",
    "city",
    "state",
    "country",
    "hs_lead_status",
    "lifecyclestage",
    "hs_analytics_source",
    "num_associated_deals",
    "total_revenue",
    "hs_last_sales_activity_date",
    "notes_last_updated",
]


def _run_async(coro: Any) -> Any:
    """Run async coroutine in sync context for Celery."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(
    name="src.tasks.hubspot_sync.sync_contact_deep",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def sync_contact_deep(self, hubspot_contact_id: str) -> dict:
    """Sync enhanced properties for a single contact.
    
    Args:
        hubspot_contact_id: HubSpot contact ID (e.g., "12345")
        
    Returns:
        Dict with sync status and synced properties
    """
    return _run_async(_sync_contact_deep_async(hubspot_contact_id))


async def _sync_contact_deep_async(hubspot_contact_id: str) -> dict:
    """Async implementation of deep contact sync."""
    connector = create_hubspot_connector()
    
    try:
        # Fetch contact with enhanced properties
        contact_data = await connector.get_contact_with_properties(
            hubspot_contact_id, 
            properties=ENHANCED_CONTACT_PROPERTIES
        )
        
        if not contact_data:
            return {"status": "not_found", "hubspot_contact_id": hubspot_contact_id}
        
        props = contact_data.get("properties", {})
        
        # Build enhanced properties dict
        enhanced = {
            "lifecycle_stage": props.get("lifecyclestage"),
            "lead_status": props.get("hs_lead_status"),
            "num_contacted_times": _parse_int(props.get("num_contacted_times")),
            "analytics_source": props.get("hs_analytics_source"),
            "analytics_source_data_1": props.get("hs_analytics_source_data_1"),
            "analytics_source_data_2": props.get("hs_analytics_source_data_2"),
            "recent_deal_amount": _parse_float(props.get("recent_deal_amount")),
            "num_associated_deals": _parse_int(props.get("num_associated_deals")),
            "total_revenue": _parse_float(props.get("total_revenue")),
            "job_title": props.get("jobtitle"),
            "phone": props.get("phone"),
            "mobile_phone": props.get("mobilephone"),
            "email_last_open_date": props.get("hs_email_last_open_date"),
            "email_last_reply_date": props.get("hs_email_last_reply_date"),
            "notes_last_updated": props.get("notes_last_updated"),
            "sequences_enrolled_count": _parse_int(props.get("hs_sequences_actively_enrolled_count")),
            "synced_at": datetime.utcnow().isoformat(),
        }
        
        # Update in database
        async with get_session() as session:
            stmt = select(HubSpotContact).where(
                HubSpotContact.hubspot_contact_id == hubspot_contact_id
            )
            result = await session.execute(stmt)
            contact = result.scalar_one_or_none()
            
            if contact:
                # Merge with existing custom_properties
                existing = contact.custom_properties or {}
                existing.update(enhanced)
                contact.custom_properties = existing
                contact.synced_at = datetime.utcnow()
                await session.commit()
                logger.info(f"Deep synced contact {hubspot_contact_id}")
                return {"status": "synced", "hubspot_contact_id": hubspot_contact_id, "properties": enhanced}
            else:
                logger.warning(f"Contact {hubspot_contact_id} not found in local DB")
                return {"status": "not_in_db", "hubspot_contact_id": hubspot_contact_id}
                
    except Exception as e:
        logger.error(f"Error deep syncing contact {hubspot_contact_id}: {e}")
        raise


@celery_app.task(
    name="src.tasks.hubspot_sync.sync_company_deep",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def sync_company_deep(self, hubspot_company_id: str) -> dict:
    """Sync enhanced properties for a single company."""
    return _run_async(_sync_company_deep_async(hubspot_company_id))


async def _sync_company_deep_async(hubspot_company_id: str) -> dict:
    """Async implementation of deep company sync."""
    connector = create_hubspot_connector()
    
    try:
        company_data = await connector.get_company_with_properties(
            hubspot_company_id,
            properties=ENHANCED_COMPANY_PROPERTIES
        )
        
        if not company_data:
            return {"status": "not_found", "hubspot_company_id": hubspot_company_id}
        
        props = company_data.get("properties", {})
        
        enhanced = {
            "industry": props.get("industry"),
            "annual_revenue": _parse_float(props.get("annualrevenue")),
            "employee_count": _parse_int(props.get("numberofemployees")),
            "city": props.get("city"),
            "state": props.get("state"),
            "country": props.get("country"),
            "lead_status": props.get("hs_lead_status"),
            "lifecycle_stage": props.get("lifecyclestage"),
            "analytics_source": props.get("hs_analytics_source"),
            "num_associated_deals": _parse_int(props.get("num_associated_deals")),
            "total_revenue": _parse_float(props.get("total_revenue")),
            "last_sales_activity_date": props.get("hs_last_sales_activity_date"),
            "notes_last_updated": props.get("notes_last_updated"),
            "synced_at": datetime.utcnow().isoformat(),
        }
        
        async with get_session() as session:
            stmt = select(HubSpotCompany).where(
                HubSpotCompany.hubspot_company_id == hubspot_company_id
            )
            result = await session.execute(stmt)
            company = result.scalar_one_or_none()
            
            if company:
                existing = company.custom_properties or {}
                existing.update(enhanced)
                company.custom_properties = existing
                company.synced_at = datetime.utcnow()
                await session.commit()
                logger.info(f"Deep synced company {hubspot_company_id}")
                return {"status": "synced", "hubspot_company_id": hubspot_company_id, "properties": enhanced}
            else:
                return {"status": "not_in_db", "hubspot_company_id": hubspot_company_id}
                
    except Exception as e:
        logger.error(f"Error deep syncing company {hubspot_company_id}: {e}")
        raise


@celery_app.task(
    name="src.tasks.hubspot_sync.sync_all_contacts_deep",
    bind=True,
)
def sync_all_contacts_deep(self, limit: int = 100) -> dict:
    """Sync enhanced properties for all contacts in local DB.
    
    Args:
        limit: Max contacts to sync per run
        
    Returns:
        Summary of sync results
    """
    return _run_async(_sync_all_contacts_deep_async(limit))


async def _sync_all_contacts_deep_async(limit: int) -> dict:
    """Async implementation of bulk contact sync."""
    async with get_session() as session:
        stmt = select(HubSpotContact.hubspot_contact_id).limit(limit)
        result = await session.execute(stmt)
        contact_ids = [row[0] for row in result.fetchall()]
    
    synced = 0
    failed = 0
    
    for contact_id in contact_ids:
        try:
            result = await _sync_contact_deep_async(contact_id)
            if result.get("status") == "synced":
                synced += 1
            else:
                failed += 1
        except Exception as e:
            logger.error(f"Failed to sync contact {contact_id}: {e}")
            failed += 1
    
    return {
        "total": len(contact_ids),
        "synced": synced,
        "failed": failed,
    }


def _parse_int(value: Any) -> int | None:
    """Safely parse int from string."""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _parse_float(value: Any) -> float | None:
    """Safely parse float from string."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None
