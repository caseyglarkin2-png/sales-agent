"""Signal Detection Rules for HubSpot Data.

Sprint 3 Task 3.2 - Detects actionable sales signals from CRM data.

Signals are patterns that require salesperson attention:
- Stalled deals (no activity in 7+ days)
- Proposals without response (sent but no reply)
- Upcoming meetings (need prep)
- Cold leads (not contacted recently)
- Big deal movement (high-value pipeline changes)
"""
import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from .client import HubSpotClient, HubSpotDeal, HubSpotContact, get_hubspot_client

logger = logging.getLogger(__name__)


class SignalType(str, Enum):
    """Types of sales signals."""
    DEAL_STALLED = "deal_stalled"
    DEAL_CLOSE_SOON = "deal_close_soon"
    DEAL_AT_RISK = "deal_at_risk"
    PROPOSAL_NO_RESPONSE = "proposal_no_response"
    MEETING_TODAY = "meeting_today"
    MEETING_PREP_NEEDED = "meeting_prep_needed"
    LEAD_COLD = "lead_cold"
    BIG_DEAL_MOVED = "big_deal_moved"
    NEW_HIGH_VALUE = "new_high_value"
    FOLLOW_UP_DUE = "follow_up_due"


class SignalPriority(str, Enum):
    """Signal priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Signal:
    """A detected sales signal that may require action."""
    type: SignalType
    priority: SignalPriority
    title: str
    description: str
    reasoning: str
    
    # HubSpot references
    contact_id: Optional[str] = None
    deal_id: Optional[str] = None
    company_id: Optional[str] = None
    
    # Metadata
    detected_at: datetime = None
    data: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.detected_at is None:
            self.detected_at = datetime.utcnow()
        if self.data is None:
            self.data = {}
    
    @property
    def idempotency_hash(self) -> str:
        """Generate unique hash for deduplication.
        
        Same signal for same entity shouldn't be created twice.
        """
        key_parts = [
            self.type.value,
            self.contact_id or "",
            self.deal_id or "",
            # Include date to allow new signals next day
            self.detected_at.strftime("%Y-%m-%d"),
        ]
        key = "|".join(key_parts)
        return hashlib.sha256(key.encode()).hexdigest()[:16]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": self.type.value,
            "priority": self.priority.value,
            "title": self.title,
            "description": self.description,
            "reasoning": self.reasoning,
            "contact_id": self.contact_id,
            "deal_id": self.deal_id,
            "company_id": self.company_id,
            "detected_at": self.detected_at.isoformat(),
            "idempotency_hash": self.idempotency_hash,
            "data": self.data,
        }


class SignalDetector:
    """Detects actionable signals from HubSpot data.
    
    Usage:
        detector = SignalDetector(hubspot_client)
        signals = await detector.detect_all()
    """
    
    # Thresholds (can be made configurable later)
    STALLED_DAYS = 7
    CLOSE_SOON_DAYS = 7
    COLD_LEAD_DAYS = 14
    HIGH_VALUE_THRESHOLD = 10000  # $10k+
    BIG_DEAL_THRESHOLD = 50000    # $50k+
    
    def __init__(self, client: HubSpotClient):
        self.client = client
    
    async def detect_all(self) -> List[Signal]:
        """Run all detection rules and return signals."""
        signals = []
        
        # Get data from HubSpot (uses cache)
        deals = await self.client.get_deals(limit=100)
        contacts = await self.client.get_contacts(limit=100)
        
        # Run detection rules
        signals.extend(await self._detect_stalled_deals(deals))
        signals.extend(await self._detect_deals_close_soon(deals))
        signals.extend(await self._detect_big_deal_movement(deals))
        signals.extend(await self._detect_cold_leads(contacts))
        
        logger.info(f"Detected {len(signals)} signals from HubSpot data")
        return signals
    
    # =========================================================================
    # Detection Rules
    # =========================================================================
    
    async def _detect_stalled_deals(self, deals: List[HubSpotDeal]) -> List[Signal]:
        """Detect deals with no activity in 7+ days."""
        signals = []
        now = datetime.utcnow()
        
        for deal in deals:
            if not deal.updated_at:
                continue
            
            days_stalled = (now - deal.updated_at).days
            
            if days_stalled >= self.STALLED_DAYS:
                # Determine priority based on deal value and stall duration
                priority = SignalPriority.MEDIUM
                if deal.amount and deal.amount >= self.BIG_DEAL_THRESHOLD:
                    priority = SignalPriority.CRITICAL
                elif deal.amount and deal.amount >= self.HIGH_VALUE_THRESHOLD:
                    priority = SignalPriority.HIGH
                elif days_stalled >= 14:
                    priority = SignalPriority.HIGH
                
                amount_str = f"${deal.amount:,.0f}" if deal.amount else "Unknown value"
                
                signal = Signal(
                    type=SignalType.DEAL_STALLED,
                    priority=priority,
                    title=f"Follow up on {deal.dealname}",
                    description=f"{deal.dealname} ({amount_str}) has had no activity for {days_stalled} days.",
                    reasoning=f"Deals that stall often die. This deal hasn't been touched in {days_stalled} days. A quick check-in could restart momentum.",
                    deal_id=deal.id,
                    data={
                        "days_stalled": days_stalled,
                        "amount": deal.amount,
                        "stage": deal.dealstage,
                        "last_updated": deal.updated_at.isoformat() if deal.updated_at else None,
                    },
                )
                signals.append(signal)
        
        return signals
    
    async def _detect_deals_close_soon(self, deals: List[HubSpotDeal]) -> List[Signal]:
        """Detect deals with close date in next 7 days."""
        signals = []
        now = datetime.utcnow()
        
        for deal in deals:
            if not deal.closedate:
                continue
            
            days_until_close = (deal.closedate - now).days
            
            if 0 <= days_until_close <= self.CLOSE_SOON_DAYS:
                priority = SignalPriority.HIGH
                if deal.amount and deal.amount >= self.BIG_DEAL_THRESHOLD:
                    priority = SignalPriority.CRITICAL
                
                if days_until_close == 0:
                    time_desc = "TODAY"
                elif days_until_close == 1:
                    time_desc = "tomorrow"
                else:
                    time_desc = f"in {days_until_close} days"
                
                amount_str = f"${deal.amount:,.0f}" if deal.amount else "Unknown value"
                
                signal = Signal(
                    type=SignalType.DEAL_CLOSE_SOON,
                    priority=priority,
                    title=f"Close date {time_desc}: {deal.dealname}",
                    description=f"{deal.dealname} ({amount_str}) is set to close {time_desc}. Make sure it's on track.",
                    reasoning=f"Close dates approaching need attention. Either push to close or update the date to keep your forecast accurate.",
                    deal_id=deal.id,
                    data={
                        "days_until_close": days_until_close,
                        "amount": deal.amount,
                        "close_date": deal.closedate.isoformat(),
                        "stage": deal.dealstage,
                    },
                )
                signals.append(signal)
        
        return signals
    
    async def _detect_big_deal_movement(self, deals: List[HubSpotDeal]) -> List[Signal]:
        """Detect high-value deals that were recently updated."""
        signals = []
        now = datetime.utcnow()
        
        for deal in deals:
            if not deal.amount or deal.amount < self.BIG_DEAL_THRESHOLD:
                continue
            
            if not deal.updated_at:
                continue
            
            days_since_update = (now - deal.updated_at).days
            
            # Recently updated high-value deal
            if days_since_update <= 1:
                signal = Signal(
                    type=SignalType.BIG_DEAL_MOVED,
                    priority=SignalPriority.HIGH,
                    title=f"Big deal activity: {deal.dealname}",
                    description=f"${deal.amount:,.0f} deal was updated recently. Check what changed.",
                    reasoning=f"Large deals require attention. Recent activity could mean the deal is progressing or there's new info to act on.",
                    deal_id=deal.id,
                    data={
                        "amount": deal.amount,
                        "stage": deal.dealstage,
                        "last_updated": deal.updated_at.isoformat(),
                    },
                )
                signals.append(signal)
        
        return signals
    
    async def _detect_cold_leads(self, contacts: List[HubSpotContact]) -> List[Signal]:
        """Detect leads not contacted in 14+ days."""
        signals = []
        now = datetime.utcnow()
        
        for contact in contacts:
            # Skip if we don't have last contact date
            if not contact.last_contacted:
                continue
            
            days_cold = (now - contact.last_contacted).days
            
            if days_cold >= self.COLD_LEAD_DAYS:
                # Don't flag very old contacts (probably dead leads)
                if days_cold > 90:
                    continue
                
                priority = SignalPriority.LOW
                if days_cold >= 30:
                    priority = SignalPriority.MEDIUM
                
                signal = Signal(
                    type=SignalType.LEAD_COLD,
                    priority=priority,
                    title=f"Re-engage {contact.full_name}",
                    description=f"Haven't contacted {contact.full_name} in {days_cold} days. Time for a touchpoint?",
                    reasoning=f"Leads go cold without regular contact. A quick check-in keeps the relationship warm.",
                    contact_id=contact.id,
                    data={
                        "days_cold": days_cold,
                        "email": contact.email,
                        "company": contact.company,
                        "last_contacted": contact.last_contacted.isoformat(),
                    },
                )
                signals.append(signal)
        
        return signals
    
    # =========================================================================
    # Individual detectors (can be called separately)
    # =========================================================================
    
    async def detect_for_deal(self, deal_id: str) -> List[Signal]:
        """Detect signals for a specific deal."""
        deals = await self.client.get_deals(limit=100)
        deal = next((d for d in deals if d.id == deal_id), None)
        
        if not deal:
            return []
        
        signals = []
        signals.extend(await self._detect_stalled_deals([deal]))
        signals.extend(await self._detect_deals_close_soon([deal]))
        signals.extend(await self._detect_big_deal_movement([deal]))
        
        return signals
    
    async def detect_for_contact(self, contact_id: str) -> List[Signal]:
        """Detect signals for a specific contact."""
        contacts = await self.client.get_contacts(limit=100)
        contact = next((c for c in contacts if c.id == contact_id), None)
        
        if not contact:
            return []
        
        return await self._detect_cold_leads([contact])


def get_signal_detector() -> SignalDetector:
    """Get signal detector with configured client."""
    client = get_hubspot_client()
    return SignalDetector(client)
