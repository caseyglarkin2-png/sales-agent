"""ABM Campaign API routes.

Account-Based Marketing campaign management endpoints.
Sprint 62: ABM Campaigns
"""
import logging
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db import get_db
from src.auth.decorators import get_current_user
from src.models.user import User
from src.models.abm_campaign import (
    ABMCampaign,
    ABMCampaignAccount,
    ABMCampaignContact,
    ABMCampaignEmail,
    ABMCampaignStatus,
)
from src.models.command_queue import CommandQueueItem, QueueItemStatus
from src.campaigns.abm_email_generator import (
    generate_abm_email,
    ABMEmailContext,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/abm-campaigns", tags=["ABM Campaigns"])


# --- Request/Response Models ---

class AccountContext(BaseModel):
    """Account-level context for personalization."""
    pain_points: Optional[List[str]] = None
    trigger_event: Optional[str] = None
    competitor_using: Optional[str] = None
    recent_news: Optional[str] = None


class ContactCreate(BaseModel):
    """Contact to add to campaign."""
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    title: Optional[str] = None
    persona: Optional[str] = None


class AccountCreate(BaseModel):
    """Account to add to campaign."""
    company_name: str
    company_domain: Optional[str] = None
    company_industry: Optional[str] = None
    account_context: Optional[AccountContext] = None
    contacts: List[ContactCreate] = Field(default_factory=list)


class CampaignCreate(BaseModel):
    """Create ABM campaign request."""
    name: str
    description: Optional[str] = None
    target_personas: List[str] = Field(default_factory=list)
    target_industries: Optional[List[str]] = None
    email_template_type: str = "cold_outreach"


class CampaignUpdate(BaseModel):
    """Update ABM campaign request."""
    name: Optional[str] = None
    description: Optional[str] = None
    target_personas: Optional[List[str]] = None
    email_template_type: Optional[str] = None


class AddAccountsRequest(BaseModel):
    """Add accounts to campaign."""
    accounts: List[AccountCreate]


class GenerateEmailsRequest(BaseModel):
    """Generate emails for campaign."""
    email_type: str = "cold_outreach"
    account_ids: Optional[List[str]] = None  # None = all accounts


class LaunchCampaignRequest(BaseModel):
    """Launch campaign request."""
    email_ids: Optional[List[str]] = None  # None = all generated emails


# --- Routes ---

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_campaign(
    payload: CampaignCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Create a new ABM campaign."""
    campaign = ABMCampaign(
        name=payload.name,
        description=payload.description,
        target_personas=payload.target_personas,
        target_industries=payload.target_industries,
        email_template_type=payload.email_template_type,
        owner_id=user.id,
        status=ABMCampaignStatus.DRAFT.value,
    )
    
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    
    logger.info(f"Created ABM campaign: {campaign.name} ({campaign.id})")
    
    return campaign.to_dict()


@router.get("")
async def list_campaigns(
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """List ABM campaigns."""
    query = select(ABMCampaign).where(ABMCampaign.owner_id == user.id)
    
    if status:
        query = query.where(ABMCampaign.status == status)
    
    query = query.order_by(ABMCampaign.created_at.desc()).offset(offset).limit(limit)
    
    result = await db.execute(query)
    campaigns = result.scalars().all()
    
    # Get total count
    count_query = select(func.count(ABMCampaign.id)).where(ABMCampaign.owner_id == user.id)
    if status:
        count_query = count_query.where(ABMCampaign.status == status)
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0
    
    return {
        "campaigns": [c.to_dict() for c in campaigns],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{campaign_id}")
async def get_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Get ABM campaign details with accounts."""
    query = (
        select(ABMCampaign)
        .options(
            selectinload(ABMCampaign.accounts).selectinload(ABMCampaignAccount.contacts)
        )
        .where(ABMCampaign.id == uuid.UUID(campaign_id))
        .where(ABMCampaign.owner_id == user.id)
    )
    
    result = await db.execute(query)
    campaign = result.scalar_one_or_none()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    campaign_dict = campaign.to_dict()
    campaign_dict["accounts"] = [
        {
            **acc.to_dict(),
            "contacts": [c.to_dict() for c in acc.contacts],
        }
        for acc in campaign.accounts
    ]
    
    return campaign_dict


@router.patch("/{campaign_id}")
async def update_campaign(
    campaign_id: str,
    payload: CampaignUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Update an ABM campaign."""
    query = (
        select(ABMCampaign)
        .where(ABMCampaign.id == uuid.UUID(campaign_id))
        .where(ABMCampaign.owner_id == user.id)
    )
    result = await db.execute(query)
    campaign = result.scalar_one_or_none()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if payload.name is not None:
        campaign.name = payload.name
    if payload.description is not None:
        campaign.description = payload.description
    if payload.target_personas is not None:
        campaign.target_personas = payload.target_personas
    if payload.email_template_type is not None:
        campaign.email_template_type = payload.email_template_type
    
    await db.commit()
    await db.refresh(campaign)
    
    return campaign.to_dict()


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """Delete an ABM campaign."""
    query = (
        select(ABMCampaign)
        .where(ABMCampaign.id == uuid.UUID(campaign_id))
        .where(ABMCampaign.owner_id == user.id)
    )
    result = await db.execute(query)
    campaign = result.scalar_one_or_none()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    await db.delete(campaign)
    await db.commit()


@router.post("/{campaign_id}/accounts")
async def add_accounts(
    campaign_id: str,
    payload: AddAccountsRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Add accounts to an ABM campaign."""
    query = (
        select(ABMCampaign)
        .where(ABMCampaign.id == uuid.UUID(campaign_id))
        .where(ABMCampaign.owner_id == user.id)
    )
    result = await db.execute(query)
    campaign = result.scalar_one_or_none()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    accounts_added = 0
    contacts_added = 0
    
    for acc_data in payload.accounts:
        account = ABMCampaignAccount(
            campaign_id=campaign.id,
            company_name=acc_data.company_name,
            company_domain=acc_data.company_domain,
            company_industry=acc_data.company_industry,
            account_context=acc_data.account_context.dict() if acc_data.account_context else None,
        )
        db.add(account)
        await db.flush()  # Get account ID
        accounts_added += 1
        
        for contact_data in acc_data.contacts:
            contact = ABMCampaignContact(
                account_id=account.id,
                email=contact_data.email,
                first_name=contact_data.first_name,
                last_name=contact_data.last_name,
                title=contact_data.title,
                persona=contact_data.persona,
            )
            db.add(contact)
            contacts_added += 1
    
    # Update campaign metrics
    campaign.total_accounts += accounts_added
    campaign.total_contacts += contacts_added
    
    await db.commit()
    
    logger.info(
        f"Added {accounts_added} accounts, {contacts_added} contacts "
        f"to campaign {campaign_id}"
    )
    
    return {
        "accounts_added": accounts_added,
        "contacts_added": contacts_added,
        "total_accounts": campaign.total_accounts,
        "total_contacts": campaign.total_contacts,
    }


@router.post("/{campaign_id}/generate")
async def generate_emails(
    campaign_id: str,
    payload: GenerateEmailsRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Generate personalized emails for campaign contacts."""
    # Fetch campaign with accounts and contacts
    query = (
        select(ABMCampaign)
        .options(
            selectinload(ABMCampaign.accounts).selectinload(ABMCampaignAccount.contacts)
        )
        .where(ABMCampaign.id == uuid.UUID(campaign_id))
        .where(ABMCampaign.owner_id == user.id)
    )
    result = await db.execute(query)
    campaign = result.scalar_one_or_none()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Update status to generating
    campaign.status = ABMCampaignStatus.GENERATING.value
    await db.commit()
    
    emails_generated = 0
    
    try:
        # Filter accounts if specified
        accounts = campaign.accounts
        if payload.account_ids:
            account_uuids = [uuid.UUID(aid) for aid in payload.account_ids]
            accounts = [a for a in accounts if a.id in account_uuids]
        
        for account in accounts:
            for contact in account.contacts:
                # Build context
                context = ABMEmailContext(
                    first_name=contact.first_name or "there",
                    last_name=contact.last_name,
                    email=contact.email,
                    title=contact.title,
                    persona=contact.persona,
                    company_name=account.company_name,
                    company_domain=account.company_domain,
                    company_industry=account.company_industry,
                    pain_points=account.account_context.get("pain_points") if account.account_context else None,
                    trigger_event=account.account_context.get("trigger_event") if account.account_context else None,
                    recent_news=account.account_context.get("recent_news") if account.account_context else None,
                )
                
                # Generate email
                email_result = generate_abm_email(context, payload.email_type)
                
                # Save to database
                email = ABMCampaignEmail(
                    campaign_id=campaign.id,
                    account_id=account.id,
                    contact_id=contact.id,
                    subject=email_result.subject,
                    body=email_result.body,
                    personalization_score=email_result.personalization_score,
                    status="draft",
                )
                db.add(email)
                emails_generated += 1
            
            # Update account stats
            account.emails_generated = len(account.contacts)
        
        # Update campaign stats
        campaign.emails_generated += emails_generated
        campaign.status = ABMCampaignStatus.READY.value
        await db.commit()
        
        logger.info(f"Generated {emails_generated} emails for campaign {campaign_id}")
        
        return {
            "emails_generated": emails_generated,
            "status": campaign.status,
        }
    
    except Exception as e:
        campaign.status = ABMCampaignStatus.DRAFT.value
        await db.commit()
        logger.error(f"Failed to generate emails: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{campaign_id}/emails")
async def list_campaign_emails(
    campaign_id: str,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """List generated emails for a campaign."""
    # Verify campaign ownership
    campaign_query = (
        select(ABMCampaign)
        .where(ABMCampaign.id == uuid.UUID(campaign_id))
        .where(ABMCampaign.owner_id == user.id)
    )
    campaign_result = await db.execute(campaign_query)
    if not campaign_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Fetch emails
    query = (
        select(ABMCampaignEmail)
        .where(ABMCampaignEmail.campaign_id == uuid.UUID(campaign_id))
    )
    
    if status:
        query = query.where(ABMCampaignEmail.status == status)
    
    query = query.order_by(ABMCampaignEmail.created_at.desc()).offset(offset).limit(limit)
    
    result = await db.execute(query)
    emails = result.scalars().all()
    
    # Get total count
    count_query = (
        select(func.count(ABMCampaignEmail.id))
        .where(ABMCampaignEmail.campaign_id == uuid.UUID(campaign_id))
    )
    if status:
        count_query = count_query.where(ABMCampaignEmail.status == status)
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0
    
    return {
        "emails": [e.to_dict() for e in emails],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/{campaign_id}/launch")
async def launch_campaign(
    campaign_id: str,
    payload: LaunchCampaignRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Launch campaign - queue emails for operator approval."""
    query = (
        select(ABMCampaign)
        .where(ABMCampaign.id == uuid.UUID(campaign_id))
        .where(ABMCampaign.owner_id == user.id)
    )
    result = await db.execute(query)
    campaign = result.scalar_one_or_none()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign.status not in [ABMCampaignStatus.READY.value, ABMCampaignStatus.PAUSED.value]:
        raise HTTPException(
            status_code=400,
            detail=f"Campaign must be in 'ready' or 'paused' status. Current: {campaign.status}"
        )
    
    # Fetch emails to queue
    email_query = (
        select(ABMCampaignEmail)
        .where(ABMCampaignEmail.campaign_id == uuid.UUID(campaign_id))
        .where(ABMCampaignEmail.status == "draft")
    )
    
    if payload.email_ids:
        email_uuids = [uuid.UUID(eid) for eid in payload.email_ids]
        email_query = email_query.where(ABMCampaignEmail.id.in_(email_uuids))
    
    email_result = await db.execute(email_query)
    emails = email_result.scalars().all()
    
    if not emails:
        raise HTTPException(status_code=400, detail="No draft emails to queue")
    
    # Create queue items for each email
    queued_count = 0
    for email in emails:
        queue_item = CommandQueueItem(
            action_type="send_email",
            priority=50,  # Medium priority for ABM
            recipient=email.body[:100] + "...",  # Use contact email from email record
            subject=email.subject,
            body=email.body,
            status=QueueItemStatus.PENDING.value,
            metadata={
                "abm_campaign_id": str(campaign.id),
                "abm_email_id": str(email.id),
                "personalization_score": email.personalization_score,
            },
        )
        db.add(queue_item)
        await db.flush()
        
        # Update email with queue reference
        email.queue_item_id = queue_item.id
        email.status = "queued"
        queued_count += 1
    
    # Update campaign status
    campaign.status = ABMCampaignStatus.ACTIVE.value
    campaign.launched_at = datetime.utcnow()
    
    await db.commit()
    
    logger.info(f"Launched campaign {campaign_id}, queued {queued_count} emails")
    
    return {
        "status": "launched",
        "emails_queued": queued_count,
        "campaign_status": campaign.status,
    }


@router.post("/{campaign_id}/pause")
async def pause_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Pause an active campaign."""
    query = (
        select(ABMCampaign)
        .where(ABMCampaign.id == uuid.UUID(campaign_id))
        .where(ABMCampaign.owner_id == user.id)
    )
    result = await db.execute(query)
    campaign = result.scalar_one_or_none()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    campaign.status = ABMCampaignStatus.PAUSED.value
    await db.commit()
    
    return {"status": campaign.status}


@router.post("/{campaign_id}/complete")
async def complete_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Mark campaign as completed."""
    query = (
        select(ABMCampaign)
        .where(ABMCampaign.id == uuid.UUID(campaign_id))
        .where(ABMCampaign.owner_id == user.id)
    )
    result = await db.execute(query)
    campaign = result.scalar_one_or_none()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    campaign.status = ABMCampaignStatus.COMPLETED.value
    campaign.completed_at = datetime.utcnow()
    await db.commit()
    
    return {"status": campaign.status}
