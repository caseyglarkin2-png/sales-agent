"""
Subscription Service - Recurring Revenue Management
====================================================
Handles subscriptions, billing cycles, and revenue tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
import uuid


class BillingPeriod(str, Enum):
    """Billing period."""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMI_ANNUAL = "semi_annual"
    ANNUAL = "annual"
    CUSTOM = "custom"


class SubscriptionStatus(str, Enum):
    """Subscription status."""
    TRIAL = "trial"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class ChangeType(str, Enum):
    """Subscription change type."""
    UPGRADE = "upgrade"
    DOWNGRADE = "downgrade"
    QUANTITY_CHANGE = "quantity_change"
    RENEWAL = "renewal"
    CANCELLATION = "cancellation"


@dataclass
class PlanFeature:
    """A feature included in a plan."""
    id: str
    name: str
    description: str
    included: bool = True
    limit: Optional[int] = None  # None = unlimited


@dataclass
class SubscriptionPlan:
    """A subscription plan."""
    id: str
    name: str
    description: str
    
    # Pricing
    price: float
    currency: str = "USD"
    billing_period: BillingPeriod = BillingPeriod.MONTHLY
    
    # Setup
    setup_fee: float = 0.0
    trial_days: int = 0
    
    # Features
    features: list[PlanFeature] = field(default_factory=list)
    
    # Limits
    min_quantity: int = 1
    max_quantity: Optional[int] = None
    
    # Metadata
    is_active: bool = True
    is_featured: bool = False
    sort_order: int = 0
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SubscriptionItem:
    """A line item in a subscription."""
    id: str
    product_id: str
    product_name: str
    quantity: int
    unit_price: float
    total: float


@dataclass
class Subscription:
    """A subscription."""
    id: str
    account_id: str
    plan_id: str
    
    # Items
    items: list[SubscriptionItem] = field(default_factory=list)
    
    # Pricing
    mrr: float = 0.0  # Monthly Recurring Revenue
    arr: float = 0.0  # Annual Recurring Revenue
    quantity: int = 1
    
    # Billing
    billing_period: BillingPeriod = BillingPeriod.MONTHLY
    currency: str = "USD"
    
    # Status
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    
    # Dates
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    trial_start: Optional[datetime] = None
    trial_end: Optional[datetime] = None
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancel_at_period_end: bool = False
    
    # Auto-renewal
    auto_renew: bool = True
    renewal_reminder_days: int = 30
    
    # Payment
    payment_method_id: Optional[str] = None
    last_payment_date: Optional[datetime] = None
    next_billing_date: Optional[datetime] = None
    
    # Discounts
    discount_percent: float = 0.0
    discount_expires: Optional[datetime] = None
    
    # Related
    contract_id: Optional[str] = None
    deal_id: Optional[str] = None
    owner_id: Optional[str] = None
    
    # Notes
    notes: str = ""
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SubscriptionChange:
    """A change to a subscription."""
    id: str
    subscription_id: str
    change_type: ChangeType
    
    # Before/After
    old_plan_id: Optional[str] = None
    new_plan_id: Optional[str] = None
    old_quantity: Optional[int] = None
    new_quantity: Optional[int] = None
    old_mrr: float = 0.0
    new_mrr: float = 0.0
    
    # Impact
    mrr_change: float = 0.0
    proration_amount: float = 0.0
    
    # Metadata
    reason: str = ""
    changed_by: Optional[str] = None
    effective_date: datetime = field(default_factory=datetime.utcnow)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Invoice:
    """An invoice for a subscription."""
    id: str
    subscription_id: str
    account_id: str
    
    # Amounts
    subtotal: float = 0.0
    discount: float = 0.0
    tax: float = 0.0
    total: float = 0.0
    
    # Status
    status: str = "draft"  # draft, sent, paid, void
    
    # Dates
    invoice_date: datetime = field(default_factory=datetime.utcnow)
    due_date: Optional[datetime] = None
    paid_date: Optional[datetime] = None
    
    # Period
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    
    # Items
    line_items: list[dict[str, Any]] = field(default_factory=list)
    
    created_at: datetime = field(default_factory=datetime.utcnow)


class SubscriptionService:
    """Service for subscription management."""
    
    def __init__(self):
        self.plans: dict[str, SubscriptionPlan] = {}
        self.subscriptions: dict[str, Subscription] = {}
        self.changes: dict[str, list[SubscriptionChange]] = {}
        self.invoices: dict[str, list[Invoice]] = {}
        self._init_sample_plans()
    
    def _init_sample_plans(self) -> None:
        """Initialize sample plans."""
        starter = SubscriptionPlan(
            id="plan-starter",
            name="Starter",
            description="For small teams getting started",
            price=49.0,
            billing_period=BillingPeriod.MONTHLY,
            trial_days=14,
            features=[
                PlanFeature(id="f1", name="Users", description="Team members", limit=5),
                PlanFeature(id="f2", name="Contacts", description="Contact records", limit=1000),
                PlanFeature(id="f3", name="Email Support", description="Email support"),
            ],
            sort_order=1,
        )
        
        professional = SubscriptionPlan(
            id="plan-professional",
            name="Professional",
            description="For growing teams",
            price=149.0,
            billing_period=BillingPeriod.MONTHLY,
            trial_days=14,
            is_featured=True,
            features=[
                PlanFeature(id="f1", name="Users", description="Team members", limit=25),
                PlanFeature(id="f2", name="Contacts", description="Contact records", limit=10000),
                PlanFeature(id="f3", name="Priority Support", description="Priority support"),
                PlanFeature(id="f4", name="API Access", description="API access"),
            ],
            sort_order=2,
        )
        
        enterprise = SubscriptionPlan(
            id="plan-enterprise",
            name="Enterprise",
            description="For large organizations",
            price=499.0,
            billing_period=BillingPeriod.MONTHLY,
            features=[
                PlanFeature(id="f1", name="Users", description="Team members"),
                PlanFeature(id="f2", name="Contacts", description="Contact records"),
                PlanFeature(id="f3", name="Dedicated Support", description="24/7 support"),
                PlanFeature(id="f4", name="Custom Integrations", description="Custom integrations"),
                PlanFeature(id="f5", name="SSO", description="Single Sign-On"),
            ],
            sort_order=3,
        )
        
        self.plans[starter.id] = starter
        self.plans[professional.id] = professional
        self.plans[enterprise.id] = enterprise
    
    # Plan CRUD
    async def create_plan(
        self,
        name: str,
        description: str,
        price: float,
        billing_period: BillingPeriod = BillingPeriod.MONTHLY,
        **kwargs
    ) -> SubscriptionPlan:
        """Create a subscription plan."""
        plan = SubscriptionPlan(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            price=price,
            billing_period=billing_period,
            **kwargs
        )
        self.plans[plan.id] = plan
        return plan
    
    async def get_plan(self, plan_id: str) -> Optional[SubscriptionPlan]:
        """Get a plan by ID."""
        return self.plans.get(plan_id)
    
    async def update_plan(
        self,
        plan_id: str,
        updates: dict[str, Any]
    ) -> Optional[SubscriptionPlan]:
        """Update a plan."""
        plan = self.plans.get(plan_id)
        if not plan:
            return None
        
        for key, value in updates.items():
            if hasattr(plan, key):
                setattr(plan, key, value)
        
        plan.updated_at = datetime.utcnow()
        return plan
    
    async def list_plans(
        self,
        active_only: bool = True,
        billing_period: Optional[BillingPeriod] = None
    ) -> list[SubscriptionPlan]:
        """List plans."""
        plans = list(self.plans.values())
        
        if active_only:
            plans = [p for p in plans if p.is_active]
        if billing_period:
            plans = [p for p in plans if p.billing_period == billing_period]
        
        plans.sort(key=lambda p: p.sort_order)
        return plans
    
    # Subscription CRUD
    async def create_subscription(
        self,
        account_id: str,
        plan_id: str,
        quantity: int = 1,
        start_date: Optional[datetime] = None,
        trial: bool = False,
        **kwargs
    ) -> Optional[Subscription]:
        """Create a subscription."""
        plan = self.plans.get(plan_id)
        if not plan:
            return None
        
        from datetime import timedelta
        
        start = start_date or datetime.utcnow()
        
        # Calculate MRR/ARR
        monthly_multiplier = {
            BillingPeriod.MONTHLY: 1,
            BillingPeriod.QUARTERLY: 3,
            BillingPeriod.SEMI_ANNUAL: 6,
            BillingPeriod.ANNUAL: 12,
        }
        
        months = monthly_multiplier.get(plan.billing_period, 1)
        mrr = (plan.price * quantity) / months
        arr = mrr * 12
        
        # Trial dates
        trial_start = None
        trial_end = None
        if trial and plan.trial_days > 0:
            trial_start = start
            trial_end = start + timedelta(days=plan.trial_days)
            start = trial_end
        
        # Calculate period end
        if plan.billing_period == BillingPeriod.MONTHLY:
            period_end = start + timedelta(days=30)
        elif plan.billing_period == BillingPeriod.QUARTERLY:
            period_end = start + timedelta(days=90)
        elif plan.billing_period == BillingPeriod.SEMI_ANNUAL:
            period_end = start + timedelta(days=180)
        else:
            period_end = start + timedelta(days=365)
        
        subscription = Subscription(
            id=str(uuid.uuid4()),
            account_id=account_id,
            plan_id=plan_id,
            quantity=quantity,
            mrr=mrr,
            arr=arr,
            billing_period=plan.billing_period,
            status=SubscriptionStatus.TRIAL if trial else SubscriptionStatus.ACTIVE,
            start_date=start if not trial else trial_end,
            trial_start=trial_start,
            trial_end=trial_end,
            current_period_start=start,
            current_period_end=period_end,
            next_billing_date=period_end,
            **kwargs
        )
        
        self.subscriptions[subscription.id] = subscription
        self.changes[subscription.id] = []
        self.invoices[subscription.id] = []
        
        return subscription
    
    async def get_subscription(self, subscription_id: str) -> Optional[Subscription]:
        """Get a subscription by ID."""
        return self.subscriptions.get(subscription_id)
    
    async def update_subscription(
        self,
        subscription_id: str,
        updates: dict[str, Any]
    ) -> Optional[Subscription]:
        """Update a subscription."""
        subscription = self.subscriptions.get(subscription_id)
        if not subscription:
            return None
        
        for key, value in updates.items():
            if hasattr(subscription, key):
                setattr(subscription, key, value)
        
        subscription.updated_at = datetime.utcnow()
        return subscription
    
    async def list_subscriptions(
        self,
        account_id: Optional[str] = None,
        status: Optional[SubscriptionStatus] = None,
        plan_id: Optional[str] = None,
        owner_id: Optional[str] = None,
        limit: int = 100
    ) -> list[Subscription]:
        """List subscriptions."""
        subscriptions = list(self.subscriptions.values())
        
        if account_id:
            subscriptions = [s for s in subscriptions if s.account_id == account_id]
        if status:
            subscriptions = [s for s in subscriptions if s.status == status]
        if plan_id:
            subscriptions = [s for s in subscriptions if s.plan_id == plan_id]
        if owner_id:
            subscriptions = [s for s in subscriptions if s.owner_id == owner_id]
        
        subscriptions.sort(key=lambda s: s.created_at, reverse=True)
        return subscriptions[:limit]
    
    # Subscription actions
    async def upgrade(
        self,
        subscription_id: str,
        new_plan_id: str,
        prorate: bool = True
    ) -> Optional[Subscription]:
        """Upgrade a subscription."""
        subscription = self.subscriptions.get(subscription_id)
        new_plan = self.plans.get(new_plan_id)
        
        if not subscription or not new_plan:
            return None
        
        old_plan = self.plans.get(subscription.plan_id)
        old_mrr = subscription.mrr
        
        # Record change
        change = SubscriptionChange(
            id=str(uuid.uuid4()),
            subscription_id=subscription_id,
            change_type=ChangeType.UPGRADE,
            old_plan_id=subscription.plan_id,
            new_plan_id=new_plan_id,
            old_mrr=old_mrr,
        )
        
        # Update subscription
        subscription.plan_id = new_plan_id
        subscription.billing_period = new_plan.billing_period
        
        # Recalculate MRR
        monthly_multiplier = {
            BillingPeriod.MONTHLY: 1,
            BillingPeriod.QUARTERLY: 3,
            BillingPeriod.SEMI_ANNUAL: 6,
            BillingPeriod.ANNUAL: 12,
        }
        months = monthly_multiplier.get(new_plan.billing_period, 1)
        subscription.mrr = (new_plan.price * subscription.quantity) / months
        subscription.arr = subscription.mrr * 12
        
        change.new_mrr = subscription.mrr
        change.mrr_change = subscription.mrr - old_mrr
        
        # Proration calculation (simplified)
        if prorate and subscription.current_period_end:
            days_remaining = (subscription.current_period_end - datetime.utcnow()).days
            total_days = 30 if subscription.billing_period == BillingPeriod.MONTHLY else 365
            change.proration_amount = change.mrr_change * (days_remaining / total_days)
        
        self.changes[subscription_id].append(change)
        subscription.updated_at = datetime.utcnow()
        
        return subscription
    
    async def downgrade(
        self,
        subscription_id: str,
        new_plan_id: str,
        at_period_end: bool = True
    ) -> Optional[Subscription]:
        """Downgrade a subscription."""
        subscription = self.subscriptions.get(subscription_id)
        new_plan = self.plans.get(new_plan_id)
        
        if not subscription or not new_plan:
            return None
        
        change = SubscriptionChange(
            id=str(uuid.uuid4()),
            subscription_id=subscription_id,
            change_type=ChangeType.DOWNGRADE,
            old_plan_id=subscription.plan_id,
            new_plan_id=new_plan_id,
            old_mrr=subscription.mrr,
            effective_date=subscription.current_period_end if at_period_end else datetime.utcnow(),
        )
        
        if not at_period_end:
            subscription.plan_id = new_plan_id
            monthly_multiplier = {
                BillingPeriod.MONTHLY: 1,
                BillingPeriod.QUARTERLY: 3,
                BillingPeriod.SEMI_ANNUAL: 6,
                BillingPeriod.ANNUAL: 12,
            }
            months = monthly_multiplier.get(new_plan.billing_period, 1)
            subscription.mrr = (new_plan.price * subscription.quantity) / months
            subscription.arr = subscription.mrr * 12
        
        change.new_mrr = subscription.mrr
        change.mrr_change = subscription.mrr - change.old_mrr
        
        self.changes[subscription_id].append(change)
        subscription.updated_at = datetime.utcnow()
        
        return subscription
    
    async def change_quantity(
        self,
        subscription_id: str,
        new_quantity: int,
        prorate: bool = True
    ) -> Optional[Subscription]:
        """Change subscription quantity."""
        subscription = self.subscriptions.get(subscription_id)
        plan = self.plans.get(subscription.plan_id) if subscription else None
        
        if not subscription or not plan:
            return None
        
        old_quantity = subscription.quantity
        old_mrr = subscription.mrr
        
        subscription.quantity = new_quantity
        
        monthly_multiplier = {
            BillingPeriod.MONTHLY: 1,
            BillingPeriod.QUARTERLY: 3,
            BillingPeriod.SEMI_ANNUAL: 6,
            BillingPeriod.ANNUAL: 12,
        }
        months = monthly_multiplier.get(plan.billing_period, 1)
        subscription.mrr = (plan.price * new_quantity) / months
        subscription.arr = subscription.mrr * 12
        
        change = SubscriptionChange(
            id=str(uuid.uuid4()),
            subscription_id=subscription_id,
            change_type=ChangeType.QUANTITY_CHANGE,
            old_quantity=old_quantity,
            new_quantity=new_quantity,
            old_mrr=old_mrr,
            new_mrr=subscription.mrr,
            mrr_change=subscription.mrr - old_mrr,
        )
        
        self.changes[subscription_id].append(change)
        subscription.updated_at = datetime.utcnow()
        
        return subscription
    
    async def cancel(
        self,
        subscription_id: str,
        reason: str = "",
        at_period_end: bool = True
    ) -> bool:
        """Cancel a subscription."""
        subscription = self.subscriptions.get(subscription_id)
        if not subscription:
            return False
        
        if at_period_end:
            subscription.cancel_at_period_end = True
        else:
            subscription.status = SubscriptionStatus.CANCELLED
            subscription.cancelled_at = datetime.utcnow()
        
        change = SubscriptionChange(
            id=str(uuid.uuid4()),
            subscription_id=subscription_id,
            change_type=ChangeType.CANCELLATION,
            old_mrr=subscription.mrr,
            new_mrr=0.0,
            mrr_change=-subscription.mrr,
            reason=reason,
            effective_date=subscription.current_period_end if at_period_end else datetime.utcnow(),
        )
        
        self.changes[subscription_id].append(change)
        subscription.updated_at = datetime.utcnow()
        
        return True
    
    async def pause(
        self,
        subscription_id: str,
        resume_date: Optional[datetime] = None
    ) -> bool:
        """Pause a subscription."""
        subscription = self.subscriptions.get(subscription_id)
        if not subscription or subscription.status != SubscriptionStatus.ACTIVE:
            return False
        
        subscription.status = SubscriptionStatus.PAUSED
        subscription.updated_at = datetime.utcnow()
        
        return True
    
    async def resume(self, subscription_id: str) -> bool:
        """Resume a paused subscription."""
        subscription = self.subscriptions.get(subscription_id)
        if not subscription or subscription.status != SubscriptionStatus.PAUSED:
            return False
        
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.updated_at = datetime.utcnow()
        
        return True
    
    async def renew(self, subscription_id: str) -> Optional[Subscription]:
        """Renew a subscription."""
        subscription = self.subscriptions.get(subscription_id)
        if not subscription:
            return None
        
        from datetime import timedelta
        
        # Move period forward
        old_end = subscription.current_period_end or datetime.utcnow()
        
        if subscription.billing_period == BillingPeriod.MONTHLY:
            new_end = old_end + timedelta(days=30)
        elif subscription.billing_period == BillingPeriod.QUARTERLY:
            new_end = old_end + timedelta(days=90)
        elif subscription.billing_period == BillingPeriod.SEMI_ANNUAL:
            new_end = old_end + timedelta(days=180)
        else:
            new_end = old_end + timedelta(days=365)
        
        subscription.current_period_start = old_end
        subscription.current_period_end = new_end
        subscription.next_billing_date = new_end
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.cancel_at_period_end = False
        
        change = SubscriptionChange(
            id=str(uuid.uuid4()),
            subscription_id=subscription_id,
            change_type=ChangeType.RENEWAL,
            old_mrr=subscription.mrr,
            new_mrr=subscription.mrr,
        )
        
        self.changes[subscription_id].append(change)
        subscription.updated_at = datetime.utcnow()
        
        return subscription
    
    # Changes
    async def get_changes(self, subscription_id: str) -> list[SubscriptionChange]:
        """Get changes for a subscription."""
        return self.changes.get(subscription_id, [])
    
    # Revenue Analytics
    async def get_mrr_summary(self) -> dict[str, Any]:
        """Get MRR summary."""
        active_subs = [
            s for s in self.subscriptions.values()
            if s.status == SubscriptionStatus.ACTIVE
        ]
        
        total_mrr = sum(s.mrr for s in active_subs)
        total_arr = sum(s.arr for s in active_subs)
        
        by_plan = {}
        for s in active_subs:
            by_plan[s.plan_id] = by_plan.get(s.plan_id, 0) + s.mrr
        
        return {
            "total_mrr": total_mrr,
            "total_arr": total_arr,
            "active_subscriptions": len(active_subs),
            "avg_mrr": total_mrr / len(active_subs) if active_subs else 0,
            "by_plan": by_plan,
        }
    
    async def get_churn_metrics(
        self,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None
    ) -> dict[str, Any]:
        """Get churn metrics."""
        cancelled = [
            s for s in self.subscriptions.values()
            if s.status == SubscriptionStatus.CANCELLED
        ]
        
        if period_start:
            cancelled = [c for c in cancelled if c.cancelled_at and c.cancelled_at >= period_start]
        if period_end:
            cancelled = [c for c in cancelled if c.cancelled_at and c.cancelled_at <= period_end]
        
        total_active = len([
            s for s in self.subscriptions.values()
            if s.status == SubscriptionStatus.ACTIVE
        ])
        
        churned_mrr = sum(s.mrr for s in cancelled)
        
        return {
            "churned_subscriptions": len(cancelled),
            "churned_mrr": churned_mrr,
            "churn_rate": len(cancelled) / (total_active + len(cancelled)) if total_active else 0,
        }


# Singleton instance
_subscription_service: Optional[SubscriptionService] = None


def get_subscription_service() -> SubscriptionService:
    """Get subscription service singleton."""
    global _subscription_service
    if _subscription_service is None:
        _subscription_service = SubscriptionService()
    return _subscription_service
