"""
Deal/Pipeline Service
=====================
Manages sales deals and pipeline stages.
Tracks deal progress, probability, and revenue forecasting.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
import structlog
import uuid

logger = structlog.get_logger(__name__)


class DealStage(str, Enum):
    """Standard deal stages."""
    LEAD = "lead"
    QUALIFIED = "qualified"
    DEMO_SCHEDULED = "demo_scheduled"
    DEMO_COMPLETED = "demo_completed"
    PROPOSAL_SENT = "proposal_sent"
    NEGOTIATION = "negotiation"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


# Default stage probabilities
STAGE_PROBABILITIES = {
    DealStage.LEAD: 10,
    DealStage.QUALIFIED: 20,
    DealStage.DEMO_SCHEDULED: 40,
    DealStage.DEMO_COMPLETED: 60,
    DealStage.PROPOSAL_SENT: 75,
    DealStage.NEGOTIATION: 90,
    DealStage.CLOSED_WON: 100,
    DealStage.CLOSED_LOST: 0,
}


@dataclass
class DealActivity:
    """Activity on a deal."""
    id: str
    deal_id: str
    activity_type: str  # stage_change, note, call, email, meeting
    description: str
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "deal_id": self.deal_id,
            "activity_type": self.activity_type,
            "description": self.description,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class Deal:
    """A sales deal."""
    id: str
    name: str
    amount: float
    stage: DealStage = DealStage.LEAD
    probability: int = 10
    contact_id: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    company_id: Optional[str] = None
    company_name: Optional[str] = None
    owner_id: Optional[str] = None
    owner_name: Optional[str] = None
    pipeline_id: Optional[str] = None
    close_date: Optional[datetime] = None
    description: str = ""
    source: str = ""
    products: list[str] = field(default_factory=list)
    competitors: list[str] = field(default_factory=list)
    loss_reason: Optional[str] = None
    won_reason: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    custom_fields: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    closed_at: Optional[datetime] = None
    
    @property
    def weighted_amount(self) -> float:
        """Calculate weighted deal amount."""
        return self.amount * (self.probability / 100)
    
    @property
    def is_open(self) -> bool:
        """Check if deal is still open."""
        return self.stage not in [DealStage.CLOSED_WON, DealStage.CLOSED_LOST]
    
    @property
    def days_in_stage(self) -> int:
        """Days since last stage change."""
        return (datetime.utcnow() - self.updated_at).days
    
    @property
    def days_open(self) -> int:
        """Total days deal has been open."""
        end = self.closed_at or datetime.utcnow()
        return (end - self.created_at).days
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "amount": self.amount,
            "weighted_amount": self.weighted_amount,
            "stage": self.stage.value,
            "probability": self.probability,
            "contact_id": self.contact_id,
            "contact_name": self.contact_name,
            "contact_email": self.contact_email,
            "company_id": self.company_id,
            "company_name": self.company_name,
            "owner_id": self.owner_id,
            "owner_name": self.owner_name,
            "pipeline_id": self.pipeline_id,
            "close_date": self.close_date.isoformat() if self.close_date else None,
            "description": self.description,
            "source": self.source,
            "products": self.products,
            "competitors": self.competitors,
            "loss_reason": self.loss_reason,
            "won_reason": self.won_reason,
            "tags": self.tags,
            "is_open": self.is_open,
            "days_in_stage": self.days_in_stage,
            "days_open": self.days_open,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
        }


@dataclass
class Pipeline:
    """A sales pipeline configuration."""
    id: str
    name: str
    stages: list[dict] = field(default_factory=list)
    is_default: bool = False
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "stages": self.stages,
            "is_default": self.is_default,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
        }


class DealService:
    """
    Manages sales deals and pipeline.
    """
    
    def __init__(self):
        self.deals: dict[str, Deal] = {}
        self.activities: dict[str, list[DealActivity]] = {}  # deal_id -> activities
        self.pipelines: dict[str, Pipeline] = {}
        self._setup_default_pipeline()
    
    def _setup_default_pipeline(self) -> None:
        """Set up the default pipeline."""
        pipeline = Pipeline(
            id=str(uuid.uuid4()),
            name="Sales Pipeline",
            is_default=True,
            stages=[
                {"name": "Lead", "value": "lead", "probability": 10, "order": 1},
                {"name": "Qualified", "value": "qualified", "probability": 20, "order": 2},
                {"name": "Demo Scheduled", "value": "demo_scheduled", "probability": 40, "order": 3},
                {"name": "Demo Completed", "value": "demo_completed", "probability": 60, "order": 4},
                {"name": "Proposal Sent", "value": "proposal_sent", "probability": 75, "order": 5},
                {"name": "Negotiation", "value": "negotiation", "probability": 90, "order": 6},
                {"name": "Closed Won", "value": "closed_won", "probability": 100, "order": 7},
                {"name": "Closed Lost", "value": "closed_lost", "probability": 0, "order": 8},
            ],
        )
        self.pipelines[pipeline.id] = pipeline
        logger.info("default_pipeline_created", pipeline_id=pipeline.id)
    
    def create_deal(
        self,
        name: str,
        amount: float,
        contact_id: str = None,
        contact_name: str = None,
        contact_email: str = None,
        company_id: str = None,
        company_name: str = None,
        owner_id: str = None,
        owner_name: str = None,
        pipeline_id: str = None,
        close_date: datetime = None,
        description: str = "",
        source: str = "",
        products: list[str] = None,
        tags: list[str] = None,
    ) -> Deal:
        """Create a new deal."""
        deal = Deal(
            id=str(uuid.uuid4()),
            name=name,
            amount=amount,
            stage=DealStage.LEAD,
            probability=STAGE_PROBABILITIES[DealStage.LEAD],
            contact_id=contact_id,
            contact_name=contact_name,
            contact_email=contact_email,
            company_id=company_id,
            company_name=company_name,
            owner_id=owner_id,
            owner_name=owner_name,
            pipeline_id=pipeline_id,
            close_date=close_date,
            description=description,
            source=source,
            products=products or [],
            tags=tags or [],
        )
        
        self.deals[deal.id] = deal
        self.activities[deal.id] = []
        
        # Log creation activity
        self._add_activity(
            deal_id=deal.id,
            activity_type="created",
            description=f"Deal created: {name}",
        )
        
        logger.info(
            "deal_created",
            deal_id=deal.id,
            name=name,
            amount=amount,
        )
        
        return deal
    
    def get_deal(self, deal_id: str) -> Optional[Deal]:
        """Get a deal by ID."""
        return self.deals.get(deal_id)
    
    def list_deals(
        self,
        stage: DealStage = None,
        owner_id: str = None,
        contact_id: str = None,
        company_id: str = None,
        pipeline_id: str = None,
        open_only: bool = False,
        min_amount: float = None,
        max_amount: float = None,
        tags: list[str] = None,
    ) -> list[Deal]:
        """List deals with filters."""
        deals = list(self.deals.values())
        
        if stage:
            deals = [d for d in deals if d.stage == stage]
        
        if owner_id:
            deals = [d for d in deals if d.owner_id == owner_id]
        
        if contact_id:
            deals = [d for d in deals if d.contact_id == contact_id]
        
        if company_id:
            deals = [d for d in deals if d.company_id == company_id]
        
        if pipeline_id:
            deals = [d for d in deals if d.pipeline_id == pipeline_id]
        
        if open_only:
            deals = [d for d in deals if d.is_open]
        
        if min_amount is not None:
            deals = [d for d in deals if d.amount >= min_amount]
        
        if max_amount is not None:
            deals = [d for d in deals if d.amount <= max_amount]
        
        if tags:
            deals = [d for d in deals if any(tag in d.tags for tag in tags)]
        
        return sorted(deals, key=lambda d: d.created_at, reverse=True)
    
    def update_deal(
        self,
        deal_id: str,
        updates: dict,
    ) -> Optional[Deal]:
        """Update a deal."""
        deal = self.deals.get(deal_id)
        if not deal:
            return None
        
        for key, value in updates.items():
            if hasattr(deal, key) and key not in ["id", "created_at", "activities"]:
                setattr(deal, key, value)
        
        deal.updated_at = datetime.utcnow()
        return deal
    
    def move_stage(
        self,
        deal_id: str,
        new_stage: DealStage,
        notes: str = "",
    ) -> Optional[Deal]:
        """Move a deal to a new stage."""
        deal = self.deals.get(deal_id)
        if not deal:
            return None
        
        old_stage = deal.stage
        deal.stage = new_stage
        deal.probability = STAGE_PROBABILITIES.get(new_stage, 50)
        deal.updated_at = datetime.utcnow()
        
        # Handle closed stages
        if new_stage in [DealStage.CLOSED_WON, DealStage.CLOSED_LOST]:
            deal.closed_at = datetime.utcnow()
        
        self._add_activity(
            deal_id=deal_id,
            activity_type="stage_change",
            description=f"Stage changed from {old_stage.value} to {new_stage.value}",
            old_value=old_stage.value,
            new_value=new_stage.value,
        )
        
        if notes:
            self._add_activity(
                deal_id=deal_id,
                activity_type="note",
                description=notes,
            )
        
        logger.info(
            "deal_stage_changed",
            deal_id=deal_id,
            old_stage=old_stage.value,
            new_stage=new_stage.value,
        )
        
        return deal
    
    def close_won(
        self,
        deal_id: str,
        won_reason: str = "",
        notes: str = "",
    ) -> Optional[Deal]:
        """Mark a deal as won."""
        deal = self.deals.get(deal_id)
        if not deal:
            return None
        
        deal.won_reason = won_reason
        return self.move_stage(deal_id, DealStage.CLOSED_WON, notes)
    
    def close_lost(
        self,
        deal_id: str,
        loss_reason: str = "",
        notes: str = "",
    ) -> Optional[Deal]:
        """Mark a deal as lost."""
        deal = self.deals.get(deal_id)
        if not deal:
            return None
        
        deal.loss_reason = loss_reason
        return self.move_stage(deal_id, DealStage.CLOSED_LOST, notes)
    
    def delete_deal(self, deal_id: str) -> bool:
        """Delete a deal."""
        if deal_id in self.deals:
            del self.deals[deal_id]
            if deal_id in self.activities:
                del self.activities[deal_id]
            return True
        return False
    
    def _add_activity(
        self,
        deal_id: str,
        activity_type: str,
        description: str,
        user_id: str = None,
        user_name: str = None,
        old_value: str = None,
        new_value: str = None,
    ) -> DealActivity:
        """Add an activity to a deal."""
        activity = DealActivity(
            id=str(uuid.uuid4()),
            deal_id=deal_id,
            activity_type=activity_type,
            description=description,
            user_id=user_id,
            user_name=user_name,
            old_value=old_value,
            new_value=new_value,
        )
        
        if deal_id not in self.activities:
            self.activities[deal_id] = []
        
        self.activities[deal_id].append(activity)
        return activity
    
    def add_note(
        self,
        deal_id: str,
        note: str,
        user_id: str = None,
        user_name: str = None,
    ) -> Optional[DealActivity]:
        """Add a note to a deal."""
        if deal_id not in self.deals:
            return None
        
        return self._add_activity(
            deal_id=deal_id,
            activity_type="note",
            description=note,
            user_id=user_id,
            user_name=user_name,
        )
    
    def get_activities(
        self,
        deal_id: str,
        limit: int = 50,
    ) -> list[DealActivity]:
        """Get activities for a deal."""
        activities = self.activities.get(deal_id, [])
        return sorted(activities, key=lambda a: a.created_at, reverse=True)[:limit]
    
    def get_pipeline_summary(
        self,
        pipeline_id: str = None,
        owner_id: str = None,
    ) -> dict:
        """Get pipeline summary by stage."""
        deals = self.list_deals(
            pipeline_id=pipeline_id,
            owner_id=owner_id,
            open_only=True,
        )
        
        stages = {}
        for stage in DealStage:
            stage_deals = [d for d in deals if d.stage == stage]
            stages[stage.value] = {
                "count": len(stage_deals),
                "total_amount": sum(d.amount for d in stage_deals),
                "weighted_amount": sum(d.weighted_amount for d in stage_deals),
            }
        
        return {
            "total_deals": len(deals),
            "total_amount": sum(d.amount for d in deals),
            "weighted_amount": sum(d.weighted_amount for d in deals),
            "by_stage": stages,
        }
    
    def get_forecast(
        self,
        months: int = 3,
        owner_id: str = None,
    ) -> dict:
        """Get revenue forecast based on weighted pipeline."""
        deals = self.list_deals(owner_id=owner_id, open_only=True)
        
        now = datetime.utcnow()
        forecast = {}
        
        for i in range(months):
            month_start = datetime(now.year, now.month + i, 1)
            if month_start.month > 12:
                month_start = datetime(now.year + 1, month_start.month - 12, 1)
            
            month_key = month_start.strftime("%Y-%m")
            
            month_deals = [
                d for d in deals
                if d.close_date and d.close_date.strftime("%Y-%m") == month_key
            ]
            
            forecast[month_key] = {
                "deals_count": len(month_deals),
                "total_amount": sum(d.amount for d in month_deals),
                "weighted_amount": sum(d.weighted_amount for d in month_deals),
            }
        
        return {
            "months": months,
            "forecast": forecast,
            "total_weighted": sum(f["weighted_amount"] for f in forecast.values()),
        }
    
    def get_deal_stats(
        self,
        owner_id: str = None,
        days: int = 30,
    ) -> dict:
        """Get deal statistics."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        all_deals = self.list_deals(owner_id=owner_id)
        recent_deals = [d for d in all_deals if d.created_at >= cutoff]
        
        won = [d for d in all_deals if d.stage == DealStage.CLOSED_WON and d.closed_at and d.closed_at >= cutoff]
        lost = [d for d in all_deals if d.stage == DealStage.CLOSED_LOST and d.closed_at and d.closed_at >= cutoff]
        
        return {
            "period_days": days,
            "deals_created": len(recent_deals),
            "deals_won": len(won),
            "deals_lost": len(lost),
            "win_rate": (len(won) / (len(won) + len(lost)) * 100) if (won or lost) else 0,
            "revenue_won": sum(d.amount for d in won),
            "revenue_lost": sum(d.amount for d in lost),
            "average_deal_size": (sum(d.amount for d in won) / len(won)) if won else 0,
            "open_deals": len([d for d in all_deals if d.is_open]),
            "pipeline_value": sum(d.amount for d in all_deals if d.is_open),
        }
    
    # Pipeline management
    def create_pipeline(
        self,
        name: str,
        stages: list[dict],
    ) -> Pipeline:
        """Create a new pipeline."""
        pipeline = Pipeline(
            id=str(uuid.uuid4()),
            name=name,
            stages=stages,
        )
        self.pipelines[pipeline.id] = pipeline
        return pipeline
    
    def list_pipelines(self, active_only: bool = True) -> list[Pipeline]:
        """List all pipelines."""
        pipelines = list(self.pipelines.values())
        if active_only:
            pipelines = [p for p in pipelines if p.is_active]
        return pipelines
    
    def get_pipeline(self, pipeline_id: str) -> Optional[Pipeline]:
        """Get a pipeline by ID."""
        return self.pipelines.get(pipeline_id)


# Singleton instance
_service: Optional[DealService] = None


def get_deal_service() -> DealService:
    """Get the deal service singleton."""
    global _service
    if _service is None:
        _service = DealService()
    return _service
