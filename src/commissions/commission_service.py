"""
Commission Service - Commission Management
==========================================
Handles commission plans, calculations, and payouts.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
import uuid


class PlanType(str, Enum):
    """Commission plan type."""
    FLAT_RATE = "flat_rate"
    PERCENTAGE = "percentage"
    TIERED = "tiered"
    ACCELERATOR = "accelerator"
    CUSTOM = "custom"


class CommissionStatus(str, Enum):
    """Commission status."""
    PENDING = "pending"
    APPROVED = "approved"
    PAID = "paid"
    HELD = "held"
    CLAWED_BACK = "clawed_back"


class PayoutFrequency(str, Enum):
    """Payout frequency."""
    WEEKLY = "weekly"
    BI_WEEKLY = "bi_weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


class TriggerEvent(str, Enum):
    """When commission is triggered."""
    DEAL_WON = "deal_won"
    INVOICE_SENT = "invoice_sent"
    PAYMENT_RECEIVED = "payment_received"
    CONTRACT_SIGNED = "contract_signed"


@dataclass
class CommissionTier:
    """A tier in a tiered commission plan."""
    id: str
    min_amount: float  # Or min quota percentage
    max_amount: Optional[float]  # None for unlimited
    rate: float  # Percentage rate
    is_percentage_based: bool = True  # True = % of quota, False = $ amount


@dataclass
class CommissionRule:
    """A rule that modifies commission calculation."""
    id: str
    name: str
    description: str
    condition: dict[str, Any]  # Conditions to match
    modifier_type: str  # "multiplier", "bonus", "penalty"
    modifier_value: float
    is_active: bool = True


@dataclass
class CommissionPlan:
    """A commission plan."""
    id: str
    name: str
    description: str
    
    # Plan configuration
    plan_type: PlanType = PlanType.PERCENTAGE
    base_rate: float = 0.0  # Base percentage/rate
    
    # Tiered structure
    tiers: list[CommissionTier] = field(default_factory=list)
    
    # Accelerators
    accelerator_threshold: float = 100.0  # % of quota
    accelerator_rate: float = 0.0  # Additional rate after threshold
    
    # Rules
    rules: list[CommissionRule] = field(default_factory=list)
    
    # Split configuration
    split_percentage: float = 100.0  # For split deals
    
    # Clawback
    clawback_enabled: bool = False
    clawback_period_days: int = 90
    
    # Payout
    payout_frequency: PayoutFrequency = PayoutFrequency.MONTHLY
    trigger_event: TriggerEvent = TriggerEvent.DEAL_WON
    
    # Assignment
    user_ids: list[str] = field(default_factory=list)
    role_ids: list[str] = field(default_factory=list)
    
    # Validity
    effective_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: bool = True
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Commission:
    """A commission record."""
    id: str
    user_id: str
    plan_id: str
    deal_id: str
    
    # Amounts
    deal_amount: float
    commission_amount: float
    adjusted_amount: float = 0.0  # After adjustments/splits
    
    # Calculation details
    base_rate_applied: float = 0.0
    tier_applied: Optional[str] = None
    accelerator_applied: bool = False
    rules_applied: list[str] = field(default_factory=list)
    
    # Split info
    is_split: bool = False
    split_percentage: float = 100.0
    split_with: list[str] = field(default_factory=list)
    
    # Status
    status: CommissionStatus = CommissionStatus.PENDING
    
    # Period
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    
    # Approval
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    
    # Payment
    paid_at: Optional[datetime] = None
    payout_id: Optional[str] = None
    
    # Clawback
    clawback_at: Optional[datetime] = None
    clawback_reason: Optional[str] = None
    clawback_amount: float = 0.0
    
    # Notes
    notes: str = ""
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CommissionPayout:
    """A commission payout."""
    id: str
    user_id: str
    period_start: datetime
    period_end: datetime
    
    # Amounts
    total_amount: float = 0.0
    commission_ids: list[str] = field(default_factory=list)
    
    # Status
    status: str = "pending"  # pending, processing, paid
    paid_at: Optional[datetime] = None
    payment_method: Optional[str] = None
    payment_reference: Optional[str] = None
    
    created_at: datetime = field(default_factory=datetime.utcnow)


class CommissionService:
    """Service for commission management."""
    
    def __init__(self):
        self.plans: dict[str, CommissionPlan] = {}
        self.commissions: dict[str, Commission] = {}
        self.payouts: dict[str, CommissionPayout] = {}
        self._init_sample_plans()
    
    def _init_sample_plans(self) -> None:
        """Initialize sample commission plans."""
        # Standard percentage plan
        standard = CommissionPlan(
            id="plan-standard",
            name="Standard Commission",
            description="10% commission on all deals",
            plan_type=PlanType.PERCENTAGE,
            base_rate=10.0,
        )
        
        # Tiered plan
        tiered = CommissionPlan(
            id="plan-tiered",
            name="Tiered Commission",
            description="Tiered rates based on quota attainment",
            plan_type=PlanType.TIERED,
            tiers=[
                CommissionTier(
                    id="tier-1",
                    min_amount=0,
                    max_amount=50,
                    rate=8.0,
                    is_percentage_based=True,
                ),
                CommissionTier(
                    id="tier-2",
                    min_amount=50,
                    max_amount=100,
                    rate=10.0,
                    is_percentage_based=True,
                ),
                CommissionTier(
                    id="tier-3",
                    min_amount=100,
                    max_amount=None,
                    rate=15.0,
                    is_percentage_based=True,
                ),
            ],
        )
        
        self.plans[standard.id] = standard
        self.plans[tiered.id] = tiered
    
    # Plan CRUD
    async def create_plan(
        self,
        name: str,
        description: str,
        plan_type: PlanType = PlanType.PERCENTAGE,
        base_rate: float = 0.0,
        **kwargs
    ) -> CommissionPlan:
        """Create a commission plan."""
        plan_id = str(uuid.uuid4())
        
        plan = CommissionPlan(
            id=plan_id,
            name=name,
            description=description,
            plan_type=plan_type,
            base_rate=base_rate,
            **kwargs
        )
        
        self.plans[plan_id] = plan
        return plan
    
    async def get_plan(self, plan_id: str) -> Optional[CommissionPlan]:
        """Get a plan by ID."""
        return self.plans.get(plan_id)
    
    async def update_plan(
        self,
        plan_id: str,
        updates: dict[str, Any]
    ) -> Optional[CommissionPlan]:
        """Update a plan."""
        plan = self.plans.get(plan_id)
        if not plan:
            return None
        
        for key, value in updates.items():
            if hasattr(plan, key):
                setattr(plan, key, value)
        
        plan.updated_at = datetime.utcnow()
        return plan
    
    async def delete_plan(self, plan_id: str) -> bool:
        """Delete a plan."""
        if plan_id in self.plans:
            del self.plans[plan_id]
            return True
        return False
    
    async def list_plans(
        self,
        active_only: bool = True,
        user_id: Optional[str] = None
    ) -> list[CommissionPlan]:
        """List commission plans."""
        plans = list(self.plans.values())
        
        if active_only:
            plans = [p for p in plans if p.is_active]
        if user_id:
            plans = [p for p in plans if user_id in p.user_ids or not p.user_ids]
        
        plans.sort(key=lambda p: p.name)
        return plans
    
    # Tiers
    async def add_tier(
        self,
        plan_id: str,
        min_amount: float,
        max_amount: Optional[float],
        rate: float,
        is_percentage_based: bool = True
    ) -> Optional[CommissionTier]:
        """Add a tier to a plan."""
        plan = self.plans.get(plan_id)
        if not plan:
            return None
        
        tier = CommissionTier(
            id=str(uuid.uuid4()),
            min_amount=min_amount,
            max_amount=max_amount,
            rate=rate,
            is_percentage_based=is_percentage_based,
        )
        
        plan.tiers.append(tier)
        plan.tiers.sort(key=lambda t: t.min_amount)
        plan.updated_at = datetime.utcnow()
        
        return tier
    
    async def remove_tier(self, plan_id: str, tier_id: str) -> bool:
        """Remove a tier from a plan."""
        plan = self.plans.get(plan_id)
        if not plan:
            return False
        
        original_count = len(plan.tiers)
        plan.tiers = [t for t in plan.tiers if t.id != tier_id]
        
        if len(plan.tiers) < original_count:
            plan.updated_at = datetime.utcnow()
            return True
        
        return False
    
    # Rules
    async def add_rule(
        self,
        plan_id: str,
        name: str,
        description: str,
        condition: dict[str, Any],
        modifier_type: str,
        modifier_value: float
    ) -> Optional[CommissionRule]:
        """Add a rule to a plan."""
        plan = self.plans.get(plan_id)
        if not plan:
            return None
        
        rule = CommissionRule(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            condition=condition,
            modifier_type=modifier_type,
            modifier_value=modifier_value,
        )
        
        plan.rules.append(rule)
        plan.updated_at = datetime.utcnow()
        
        return rule
    
    # Commission calculation
    async def calculate_commission(
        self,
        user_id: str,
        deal_id: str,
        deal_amount: float,
        plan_id: Optional[str] = None,
        quota_attainment: float = 0.0,
        deal_metadata: Optional[dict[str, Any]] = None
    ) -> Optional[Commission]:
        """Calculate commission for a deal."""
        # Get applicable plan
        if plan_id:
            plan = self.plans.get(plan_id)
        else:
            plans = await self.list_plans(user_id=user_id)
            plan = plans[0] if plans else None
        
        if not plan:
            return None
        
        # Calculate base commission
        commission_amount = 0.0
        tier_applied = None
        
        if plan.plan_type == PlanType.FLAT_RATE:
            commission_amount = plan.base_rate
        elif plan.plan_type == PlanType.PERCENTAGE:
            commission_amount = deal_amount * (plan.base_rate / 100)
        elif plan.plan_type == PlanType.TIERED:
            # Find applicable tier
            for tier in plan.tiers:
                if tier.is_percentage_based:
                    # Quota-based tiers
                    if quota_attainment >= tier.min_amount:
                        if tier.max_amount is None or quota_attainment < tier.max_amount:
                            commission_amount = deal_amount * (tier.rate / 100)
                            tier_applied = tier.id
                else:
                    # Amount-based tiers
                    if deal_amount >= tier.min_amount:
                        if tier.max_amount is None or deal_amount < tier.max_amount:
                            commission_amount = deal_amount * (tier.rate / 100)
                            tier_applied = tier.id
        elif plan.plan_type == PlanType.ACCELERATOR:
            base_commission = deal_amount * (plan.base_rate / 100)
            if quota_attainment >= plan.accelerator_threshold:
                # Apply accelerator
                commission_amount = base_commission * (1 + plan.accelerator_rate / 100)
            else:
                commission_amount = base_commission
        
        # Apply rules
        rules_applied = []
        if plan.rules and deal_metadata:
            for rule in plan.rules:
                if not rule.is_active:
                    continue
                
                if self._evaluate_rule_condition(rule.condition, deal_metadata):
                    if rule.modifier_type == "multiplier":
                        commission_amount *= rule.modifier_value
                    elif rule.modifier_type == "bonus":
                        commission_amount += rule.modifier_value
                    elif rule.modifier_type == "penalty":
                        commission_amount -= rule.modifier_value
                    
                    rules_applied.append(rule.id)
        
        # Check if accelerator applies
        accelerator_applied = (
            plan.plan_type == PlanType.ACCELERATOR and
            quota_attainment >= plan.accelerator_threshold
        )
        
        # Create commission record
        commission = Commission(
            id=str(uuid.uuid4()),
            user_id=user_id,
            plan_id=plan.id,
            deal_id=deal_id,
            deal_amount=deal_amount,
            commission_amount=commission_amount,
            adjusted_amount=commission_amount,
            base_rate_applied=plan.base_rate,
            tier_applied=tier_applied,
            accelerator_applied=accelerator_applied,
            rules_applied=rules_applied,
        )
        
        self.commissions[commission.id] = commission
        return commission
    
    def _evaluate_rule_condition(
        self,
        condition: dict[str, Any],
        metadata: dict[str, Any]
    ) -> bool:
        """Evaluate a rule condition against metadata."""
        for field, expected in condition.items():
            actual = metadata.get(field)
            if isinstance(expected, dict):
                # Complex condition (e.g., {"gt": 1000})
                if "gt" in expected and not (actual and actual > expected["gt"]):
                    return False
                if "lt" in expected and not (actual and actual < expected["lt"]):
                    return False
                if "in" in expected and actual not in expected["in"]:
                    return False
            else:
                # Simple equality
                if actual != expected:
                    return False
        return True
    
    # Commission CRUD
    async def get_commission(self, commission_id: str) -> Optional[Commission]:
        """Get a commission by ID."""
        return self.commissions.get(commission_id)
    
    async def list_commissions(
        self,
        user_id: Optional[str] = None,
        status: Optional[CommissionStatus] = None,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
        limit: int = 100
    ) -> list[Commission]:
        """List commissions with filters."""
        commissions = list(self.commissions.values())
        
        if user_id:
            commissions = [c for c in commissions if c.user_id == user_id]
        if status:
            commissions = [c for c in commissions if c.status == status]
        if period_start:
            commissions = [c for c in commissions if c.created_at >= period_start]
        if period_end:
            commissions = [c for c in commissions if c.created_at <= period_end]
        
        commissions.sort(key=lambda c: c.created_at, reverse=True)
        return commissions[:limit]
    
    async def update_commission(
        self,
        commission_id: str,
        updates: dict[str, Any]
    ) -> Optional[Commission]:
        """Update a commission."""
        commission = self.commissions.get(commission_id)
        if not commission:
            return None
        
        for key, value in updates.items():
            if hasattr(commission, key):
                setattr(commission, key, value)
        
        commission.updated_at = datetime.utcnow()
        return commission
    
    # Split handling
    async def split_commission(
        self,
        commission_id: str,
        splits: list[dict[str, Any]]  # [{user_id, percentage}]
    ) -> list[Commission]:
        """Split a commission between users."""
        original = self.commissions.get(commission_id)
        if not original:
            return []
        
        split_commissions = []
        
        for split in splits:
            user_id = split["user_id"]
            percentage = split["percentage"]
            
            split_commission = Commission(
                id=str(uuid.uuid4()),
                user_id=user_id,
                plan_id=original.plan_id,
                deal_id=original.deal_id,
                deal_amount=original.deal_amount,
                commission_amount=original.commission_amount * (percentage / 100),
                adjusted_amount=original.commission_amount * (percentage / 100),
                base_rate_applied=original.base_rate_applied,
                is_split=True,
                split_percentage=percentage,
                split_with=[s["user_id"] for s in splits if s["user_id"] != user_id],
            )
            
            self.commissions[split_commission.id] = split_commission
            split_commissions.append(split_commission)
        
        # Mark original as superseded
        original.status = CommissionStatus.HELD
        original.notes = f"Split into {len(splits)} commissions"
        
        return split_commissions
    
    # Status workflow
    async def approve_commission(
        self,
        commission_id: str,
        approver_id: str
    ) -> bool:
        """Approve a commission."""
        commission = self.commissions.get(commission_id)
        if not commission or commission.status != CommissionStatus.PENDING:
            return False
        
        commission.status = CommissionStatus.APPROVED
        commission.approved_by = approver_id
        commission.approved_at = datetime.utcnow()
        commission.updated_at = datetime.utcnow()
        
        return True
    
    async def hold_commission(
        self,
        commission_id: str,
        reason: str
    ) -> bool:
        """Put a commission on hold."""
        commission = self.commissions.get(commission_id)
        if not commission:
            return False
        
        commission.status = CommissionStatus.HELD
        commission.notes = reason
        commission.updated_at = datetime.utcnow()
        
        return True
    
    async def clawback_commission(
        self,
        commission_id: str,
        reason: str,
        amount: Optional[float] = None
    ) -> bool:
        """Clawback a commission."""
        commission = self.commissions.get(commission_id)
        if not commission or commission.status not in [CommissionStatus.APPROVED, CommissionStatus.PAID]:
            return False
        
        commission.status = CommissionStatus.CLAWED_BACK
        commission.clawback_at = datetime.utcnow()
        commission.clawback_reason = reason
        commission.clawback_amount = amount or commission.adjusted_amount
        commission.updated_at = datetime.utcnow()
        
        return True
    
    # Payouts
    async def create_payout(
        self,
        user_id: str,
        period_start: datetime,
        period_end: datetime
    ) -> CommissionPayout:
        """Create a payout for approved commissions."""
        # Get approved commissions for period
        commissions = await self.list_commissions(
            user_id=user_id,
            status=CommissionStatus.APPROVED,
            period_start=period_start,
            period_end=period_end
        )
        
        total_amount = sum(c.adjusted_amount for c in commissions)
        commission_ids = [c.id for c in commissions]
        
        payout = CommissionPayout(
            id=str(uuid.uuid4()),
            user_id=user_id,
            period_start=period_start,
            period_end=period_end,
            total_amount=total_amount,
            commission_ids=commission_ids,
        )
        
        self.payouts[payout.id] = payout
        return payout
    
    async def process_payout(
        self,
        payout_id: str,
        payment_method: str,
        payment_reference: str
    ) -> bool:
        """Process a payout."""
        payout = self.payouts.get(payout_id)
        if not payout or payout.status != "pending":
            return False
        
        payout.status = "paid"
        payout.paid_at = datetime.utcnow()
        payout.payment_method = payment_method
        payout.payment_reference = payment_reference
        
        # Update commission statuses
        for commission_id in payout.commission_ids:
            commission = self.commissions.get(commission_id)
            if commission:
                commission.status = CommissionStatus.PAID
                commission.paid_at = datetime.utcnow()
                commission.payout_id = payout.id
        
        return True
    
    async def get_payout(self, payout_id: str) -> Optional[CommissionPayout]:
        """Get a payout by ID."""
        return self.payouts.get(payout_id)
    
    async def list_payouts(
        self,
        user_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> list[CommissionPayout]:
        """List payouts."""
        payouts = list(self.payouts.values())
        
        if user_id:
            payouts = [p for p in payouts if p.user_id == user_id]
        if status:
            payouts = [p for p in payouts if p.status == status]
        
        payouts.sort(key=lambda p: p.created_at, reverse=True)
        return payouts
    
    # Analytics
    async def get_commission_summary(
        self,
        user_id: str,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None
    ) -> dict[str, Any]:
        """Get commission summary for a user."""
        commissions = await self.list_commissions(
            user_id=user_id,
            period_start=period_start,
            period_end=period_end,
            limit=1000
        )
        
        by_status = {}
        for c in commissions:
            status = c.status.value
            by_status[status] = by_status.get(status, 0) + c.adjusted_amount
        
        total_earned = sum(c.adjusted_amount for c in commissions if c.status in [CommissionStatus.APPROVED, CommissionStatus.PAID])
        total_pending = sum(c.adjusted_amount for c in commissions if c.status == CommissionStatus.PENDING)
        total_paid = sum(c.adjusted_amount for c in commissions if c.status == CommissionStatus.PAID)
        total_clawback = sum(c.clawback_amount for c in commissions if c.status == CommissionStatus.CLAWED_BACK)
        
        return {
            "user_id": user_id,
            "total_commissions": len(commissions),
            "total_earned": total_earned,
            "total_pending": total_pending,
            "total_paid": total_paid,
            "total_clawback": total_clawback,
            "by_status": by_status,
            "avg_commission": total_earned / len(commissions) if commissions else 0,
        }
    
    async def get_team_leaderboard(
        self,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
        limit: int = 10
    ) -> list[dict[str, Any]]:
        """Get team commission leaderboard."""
        # Group by user
        user_totals = {}
        
        for commission in self.commissions.values():
            if period_start and commission.created_at < period_start:
                continue
            if period_end and commission.created_at > period_end:
                continue
            
            user_id = commission.user_id
            if user_id not in user_totals:
                user_totals[user_id] = {"earned": 0, "deals": 0}
            
            if commission.status in [CommissionStatus.APPROVED, CommissionStatus.PAID]:
                user_totals[user_id]["earned"] += commission.adjusted_amount
                user_totals[user_id]["deals"] += 1
        
        # Sort and format
        leaderboard = [
            {
                "user_id": user_id,
                "total_earned": data["earned"],
                "deal_count": data["deals"],
                "avg_per_deal": data["earned"] / data["deals"] if data["deals"] > 0 else 0,
            }
            for user_id, data in user_totals.items()
        ]
        
        leaderboard.sort(key=lambda x: x["total_earned"], reverse=True)
        
        return leaderboard[:limit]


# Singleton instance
_commission_service: Optional[CommissionService] = None


def get_commission_service() -> CommissionService:
    """Get commission service singleton."""
    global _commission_service
    if _commission_service is None:
        _commission_service = CommissionService()
    return _commission_service
