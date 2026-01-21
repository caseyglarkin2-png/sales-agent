"""
Forecast Service - Sales Forecasting
=====================================
Handles sales forecasting and predictions.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional
import uuid
import random


class ForecastPeriod(str, Enum):
    """Forecast period types."""
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


class ForecastCategory(str, Enum):
    """Forecast categories."""
    COMMIT = "commit"  # Highly confident
    BEST_CASE = "best_case"  # Optimistic
    PIPELINE = "pipeline"  # All opportunities
    OMITTED = "omitted"  # Excluded from forecast


class ForecastStatus(str, Enum):
    """Forecast status."""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    LOCKED = "locked"


class DealStageCategory(str, Enum):
    """Deal stage categories for forecasting."""
    EARLY = "early"
    MID = "mid"
    LATE = "late"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


@dataclass
class ForecastAdjustment:
    """An adjustment to a forecast."""
    id: str
    deal_id: Optional[str]
    original_amount: float
    adjusted_amount: float
    reason: str
    adjusted_by: str
    adjusted_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DealForecast:
    """Forecast data for a single deal."""
    deal_id: str
    deal_name: str
    amount: float
    probability: float
    expected_close_date: datetime
    category: ForecastCategory
    stage: str
    stage_category: DealStageCategory
    weighted_amount: float = 0.0
    owner_id: Optional[str] = None
    company_id: Optional[str] = None
    product_line: Optional[str] = None
    is_pushed: bool = False  # Pushed to next period
    push_count: int = 0
    
    def calculate_weighted(self) -> None:
        """Calculate weighted amount."""
        self.weighted_amount = self.amount * (self.probability / 100)


@dataclass
class ForecastEntry:
    """A forecast entry for a period."""
    id: str
    period: ForecastPeriod
    period_start: datetime
    period_end: datetime
    owner_id: str
    
    # Pipeline amounts
    pipeline_total: float = 0.0
    commit_amount: float = 0.0
    best_case_amount: float = 0.0
    weighted_amount: float = 0.0
    
    # Closed amounts
    closed_won: float = 0.0
    closed_lost: float = 0.0
    
    # Targets
    quota: float = 0.0
    target: float = 0.0
    
    # Deals
    deals: list[DealForecast] = field(default_factory=list)
    adjustments: list[ForecastAdjustment] = field(default_factory=list)
    
    # Status
    status: ForecastStatus = ForecastStatus.DRAFT
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    
    # Notes
    notes: str = ""
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def attainment_percentage(self) -> float:
        """Calculate quota attainment."""
        if self.quota <= 0:
            return 0.0
        return (self.closed_won / self.quota) * 100
    
    @property
    def gap_to_quota(self) -> float:
        """Calculate gap to quota."""
        return self.quota - self.closed_won
    
    @property
    def coverage_ratio(self) -> float:
        """Calculate pipeline coverage ratio."""
        gap = self.gap_to_quota
        if gap <= 0:
            return float('inf')
        return self.pipeline_total / gap if gap > 0 else 0


@dataclass
class Forecast:
    """A complete forecast."""
    id: str
    name: str
    period: ForecastPeriod
    year: int
    quarter: Optional[int] = None
    month: Optional[int] = None
    week: Optional[int] = None
    
    entries: list[ForecastEntry] = field(default_factory=list)
    
    # Aggregated amounts
    total_quota: float = 0.0
    total_closed_won: float = 0.0
    total_pipeline: float = 0.0
    total_commit: float = 0.0
    total_best_case: float = 0.0
    
    # Status
    status: ForecastStatus = ForecastStatus.DRAFT
    locked_at: Optional[datetime] = None
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def aggregate_totals(self) -> None:
        """Aggregate totals from entries."""
        self.total_quota = sum(e.quota for e in self.entries)
        self.total_closed_won = sum(e.closed_won for e in self.entries)
        self.total_pipeline = sum(e.pipeline_total for e in self.entries)
        self.total_commit = sum(e.commit_amount for e in self.entries)
        self.total_best_case = sum(e.best_case_amount for e in self.entries)


class ForecastService:
    """Service for sales forecasting."""
    
    def __init__(self):
        self.forecasts: dict[str, Forecast] = {}
        self.entries: dict[str, ForecastEntry] = {}
        self.quotas: dict[str, dict[str, float]] = {}  # owner_id -> {period_key: quota}
        self.stage_probabilities: dict[str, float] = {
            "Lead": 10,
            "Qualified": 20,
            "Discovery": 35,
            "Proposal": 50,
            "Negotiation": 70,
            "Commit": 90,
            "Closed Won": 100,
            "Closed Lost": 0,
        }
    
    def _get_period_key(
        self,
        period: ForecastPeriod,
        year: int,
        quarter: Optional[int] = None,
        month: Optional[int] = None,
        week: Optional[int] = None
    ) -> str:
        """Generate period key."""
        if period == ForecastPeriod.ANNUAL:
            return f"{year}"
        elif period == ForecastPeriod.QUARTERLY:
            return f"{year}-Q{quarter}"
        elif period == ForecastPeriod.MONTHLY:
            return f"{year}-{month:02d}"
        else:  # Weekly
            return f"{year}-W{week:02d}"
    
    def _get_period_dates(
        self,
        period: ForecastPeriod,
        year: int,
        quarter: Optional[int] = None,
        month: Optional[int] = None,
        week: Optional[int] = None
    ) -> tuple[datetime, datetime]:
        """Get start and end dates for a period."""
        if period == ForecastPeriod.ANNUAL:
            start = datetime(year, 1, 1)
            end = datetime(year, 12, 31, 23, 59, 59)
        elif period == ForecastPeriod.QUARTERLY:
            start_month = (quarter - 1) * 3 + 1
            start = datetime(year, start_month, 1)
            end_month = start_month + 2
            if end_month == 12:
                end = datetime(year, 12, 31, 23, 59, 59)
            else:
                end = datetime(year, end_month + 1, 1) - timedelta(seconds=1)
        elif period == ForecastPeriod.MONTHLY:
            start = datetime(year, month, 1)
            if month == 12:
                end = datetime(year, 12, 31, 23, 59, 59)
            else:
                end = datetime(year, month + 1, 1) - timedelta(seconds=1)
        else:  # Weekly
            start = datetime.strptime(f"{year}-W{week:02d}-1", "%Y-W%W-%w")
            end = start + timedelta(days=6, hours=23, minutes=59, seconds=59)
        
        return start, end
    
    # Forecast CRUD
    async def create_forecast(
        self,
        name: str,
        period: ForecastPeriod,
        year: int,
        quarter: Optional[int] = None,
        month: Optional[int] = None,
        week: Optional[int] = None
    ) -> Forecast:
        """Create a new forecast."""
        forecast_id = str(uuid.uuid4())
        
        forecast = Forecast(
            id=forecast_id,
            name=name,
            period=period,
            year=year,
            quarter=quarter,
            month=month,
            week=week,
        )
        
        self.forecasts[forecast_id] = forecast
        return forecast
    
    async def get_forecast(self, forecast_id: str) -> Optional[Forecast]:
        """Get a forecast by ID."""
        return self.forecasts.get(forecast_id)
    
    async def list_forecasts(
        self,
        period: Optional[ForecastPeriod] = None,
        year: Optional[int] = None,
        status: Optional[ForecastStatus] = None
    ) -> list[Forecast]:
        """List forecasts with filters."""
        forecasts = list(self.forecasts.values())
        
        if period:
            forecasts = [f for f in forecasts if f.period == period]
        if year:
            forecasts = [f for f in forecasts if f.year == year]
        if status:
            forecasts = [f for f in forecasts if f.status == status]
        
        forecasts.sort(key=lambda f: f.created_at, reverse=True)
        return forecasts
    
    # Forecast entries
    async def create_entry(
        self,
        forecast_id: str,
        owner_id: str,
        quota: float = 0.0,
        target: float = 0.0
    ) -> Optional[ForecastEntry]:
        """Create a forecast entry."""
        forecast = self.forecasts.get(forecast_id)
        if not forecast:
            return None
        
        start, end = self._get_period_dates(
            forecast.period,
            forecast.year,
            forecast.quarter,
            forecast.month,
            forecast.week
        )
        
        entry = ForecastEntry(
            id=str(uuid.uuid4()),
            period=forecast.period,
            period_start=start,
            period_end=end,
            owner_id=owner_id,
            quota=quota,
            target=target,
        )
        
        forecast.entries.append(entry)
        self.entries[entry.id] = entry
        forecast.aggregate_totals()
        
        return entry
    
    async def get_entry(self, entry_id: str) -> Optional[ForecastEntry]:
        """Get a forecast entry by ID."""
        return self.entries.get(entry_id)
    
    async def update_entry(
        self,
        entry_id: str,
        updates: dict[str, Any]
    ) -> Optional[ForecastEntry]:
        """Update a forecast entry."""
        entry = self.entries.get(entry_id)
        if not entry:
            return None
        
        for key, value in updates.items():
            if hasattr(entry, key):
                setattr(entry, key, value)
        
        entry.updated_at = datetime.utcnow()
        return entry
    
    # Deal forecasting
    async def add_deal_to_forecast(
        self,
        entry_id: str,
        deal_id: str,
        deal_name: str,
        amount: float,
        probability: float,
        expected_close_date: datetime,
        stage: str,
        category: ForecastCategory = ForecastCategory.PIPELINE,
        **kwargs
    ) -> Optional[DealForecast]:
        """Add a deal to a forecast entry."""
        entry = self.entries.get(entry_id)
        if not entry:
            return None
        
        # Determine stage category
        stage_category = DealStageCategory.EARLY
        if probability >= 70:
            stage_category = DealStageCategory.LATE
        elif probability >= 35:
            stage_category = DealStageCategory.MID
        
        deal_forecast = DealForecast(
            deal_id=deal_id,
            deal_name=deal_name,
            amount=amount,
            probability=probability,
            expected_close_date=expected_close_date,
            category=category,
            stage=stage,
            stage_category=stage_category,
            **kwargs
        )
        deal_forecast.calculate_weighted()
        
        entry.deals.append(deal_forecast)
        self._recalculate_entry(entry)
        
        return deal_forecast
    
    async def update_deal_category(
        self,
        entry_id: str,
        deal_id: str,
        category: ForecastCategory
    ) -> bool:
        """Update a deal's forecast category."""
        entry = self.entries.get(entry_id)
        if not entry:
            return False
        
        for deal in entry.deals:
            if deal.deal_id == deal_id:
                deal.category = category
                self._recalculate_entry(entry)
                return True
        
        return False
    
    async def push_deal(
        self,
        entry_id: str,
        deal_id: str,
        new_close_date: datetime
    ) -> bool:
        """Mark a deal as pushed to a later date."""
        entry = self.entries.get(entry_id)
        if not entry:
            return False
        
        for deal in entry.deals:
            if deal.deal_id == deal_id:
                deal.expected_close_date = new_close_date
                deal.is_pushed = True
                deal.push_count += 1
                self._recalculate_entry(entry)
                return True
        
        return False
    
    def _recalculate_entry(self, entry: ForecastEntry) -> None:
        """Recalculate entry totals from deals."""
        entry.pipeline_total = 0.0
        entry.commit_amount = 0.0
        entry.best_case_amount = 0.0
        entry.weighted_amount = 0.0
        entry.closed_won = 0.0
        entry.closed_lost = 0.0
        
        for deal in entry.deals:
            if deal.stage_category == DealStageCategory.CLOSED_WON:
                entry.closed_won += deal.amount
            elif deal.stage_category == DealStageCategory.CLOSED_LOST:
                entry.closed_lost += deal.amount
            elif deal.category != ForecastCategory.OMITTED:
                entry.pipeline_total += deal.amount
                entry.weighted_amount += deal.weighted_amount
                
                if deal.category == ForecastCategory.COMMIT:
                    entry.commit_amount += deal.amount
                elif deal.category == ForecastCategory.BEST_CASE:
                    entry.best_case_amount += deal.amount
        
        entry.updated_at = datetime.utcnow()
    
    # Adjustments
    async def add_adjustment(
        self,
        entry_id: str,
        deal_id: Optional[str],
        original_amount: float,
        adjusted_amount: float,
        reason: str,
        adjusted_by: str
    ) -> Optional[ForecastAdjustment]:
        """Add a forecast adjustment."""
        entry = self.entries.get(entry_id)
        if not entry:
            return None
        
        adjustment = ForecastAdjustment(
            id=str(uuid.uuid4()),
            deal_id=deal_id,
            original_amount=original_amount,
            adjusted_amount=adjusted_amount,
            reason=reason,
            adjusted_by=adjusted_by,
        )
        
        entry.adjustments.append(adjustment)
        entry.updated_at = datetime.utcnow()
        
        return adjustment
    
    # Status workflow
    async def submit_forecast(self, entry_id: str) -> bool:
        """Submit a forecast entry for approval."""
        entry = self.entries.get(entry_id)
        if not entry or entry.status != ForecastStatus.DRAFT:
            return False
        
        entry.status = ForecastStatus.SUBMITTED
        entry.submitted_at = datetime.utcnow()
        entry.updated_at = datetime.utcnow()
        
        return True
    
    async def approve_forecast(
        self,
        entry_id: str,
        approver_id: str
    ) -> bool:
        """Approve a forecast entry."""
        entry = self.entries.get(entry_id)
        if not entry or entry.status != ForecastStatus.SUBMITTED:
            return False
        
        entry.status = ForecastStatus.APPROVED
        entry.approved_at = datetime.utcnow()
        entry.approved_by = approver_id
        entry.updated_at = datetime.utcnow()
        
        return True
    
    async def lock_forecast(self, forecast_id: str) -> bool:
        """Lock a forecast (end of period)."""
        forecast = self.forecasts.get(forecast_id)
        if not forecast:
            return False
        
        forecast.status = ForecastStatus.LOCKED
        forecast.locked_at = datetime.utcnow()
        forecast.updated_at = datetime.utcnow()
        
        for entry in forecast.entries:
            entry.status = ForecastStatus.LOCKED
        
        return True
    
    # Quota management
    async def set_quota(
        self,
        owner_id: str,
        period_key: str,
        quota: float
    ) -> None:
        """Set quota for an owner."""
        if owner_id not in self.quotas:
            self.quotas[owner_id] = {}
        self.quotas[owner_id][period_key] = quota
    
    async def get_quota(
        self,
        owner_id: str,
        period_key: str
    ) -> float:
        """Get quota for an owner."""
        return self.quotas.get(owner_id, {}).get(period_key, 0.0)
    
    # Analytics
    async def get_forecast_summary(
        self,
        forecast_id: str
    ) -> Optional[dict[str, Any]]:
        """Get forecast summary."""
        forecast = self.forecasts.get(forecast_id)
        if not forecast:
            return None
        
        forecast.aggregate_totals()
        
        total_attainment = 0
        if forecast.total_quota > 0:
            total_attainment = (forecast.total_closed_won / forecast.total_quota) * 100
        
        gap = forecast.total_quota - forecast.total_closed_won
        coverage = forecast.total_pipeline / gap if gap > 0 else float('inf')
        
        return {
            "forecast_id": forecast.id,
            "name": forecast.name,
            "period": forecast.period.value,
            "year": forecast.year,
            "status": forecast.status.value,
            "total_quota": forecast.total_quota,
            "total_closed_won": forecast.total_closed_won,
            "total_pipeline": forecast.total_pipeline,
            "total_commit": forecast.total_commit,
            "total_best_case": forecast.total_best_case,
            "attainment_percentage": total_attainment,
            "gap_to_quota": gap,
            "pipeline_coverage": coverage,
            "entry_count": len(forecast.entries),
        }
    
    async def get_team_forecast(
        self,
        forecast_id: str
    ) -> list[dict[str, Any]]:
        """Get team forecast breakdown."""
        forecast = self.forecasts.get(forecast_id)
        if not forecast:
            return []
        
        return [
            {
                "owner_id": entry.owner_id,
                "quota": entry.quota,
                "closed_won": entry.closed_won,
                "pipeline": entry.pipeline_total,
                "commit": entry.commit_amount,
                "best_case": entry.best_case_amount,
                "weighted": entry.weighted_amount,
                "attainment": entry.attainment_percentage,
                "gap": entry.gap_to_quota,
                "coverage": entry.coverage_ratio,
                "deal_count": len(entry.deals),
                "status": entry.status.value,
            }
            for entry in forecast.entries
        ]
    
    async def get_category_breakdown(
        self,
        entry_id: str
    ) -> dict[str, Any]:
        """Get deal category breakdown for an entry."""
        entry = self.entries.get(entry_id)
        if not entry:
            return {}
        
        breakdown = {
            ForecastCategory.COMMIT.value: {"count": 0, "amount": 0},
            ForecastCategory.BEST_CASE.value: {"count": 0, "amount": 0},
            ForecastCategory.PIPELINE.value: {"count": 0, "amount": 0},
            ForecastCategory.OMITTED.value: {"count": 0, "amount": 0},
        }
        
        for deal in entry.deals:
            cat = deal.category.value
            breakdown[cat]["count"] += 1
            breakdown[cat]["amount"] += deal.amount
        
        return breakdown
    
    async def get_stage_breakdown(
        self,
        entry_id: str
    ) -> list[dict[str, Any]]:
        """Get deal stage breakdown."""
        entry = self.entries.get(entry_id)
        if not entry:
            return []
        
        stages = {}
        for deal in entry.deals:
            if deal.stage not in stages:
                stages[deal.stage] = {"count": 0, "amount": 0, "weighted": 0}
            stages[deal.stage]["count"] += 1
            stages[deal.stage]["amount"] += deal.amount
            stages[deal.stage]["weighted"] += deal.weighted_amount
        
        return [
            {"stage": stage, **data}
            for stage, data in stages.items()
        ]
    
    async def get_pushed_deals(self, entry_id: str) -> list[DealForecast]:
        """Get deals that have been pushed."""
        entry = self.entries.get(entry_id)
        if not entry:
            return []
        
        return [deal for deal in entry.deals if deal.is_pushed]
    
    # Trend analysis
    async def get_forecast_trend(
        self,
        owner_id: Optional[str] = None,
        periods: int = 4
    ) -> list[dict[str, Any]]:
        """Get forecast trend over periods."""
        # Get historical forecasts
        forecasts = list(self.forecasts.values())
        forecasts.sort(key=lambda f: f.created_at, reverse=True)
        
        trend = []
        for forecast in forecasts[:periods]:
            entries = forecast.entries
            if owner_id:
                entries = [e for e in entries if e.owner_id == owner_id]
            
            total_quota = sum(e.quota for e in entries)
            total_closed = sum(e.closed_won for e in entries)
            total_pipeline = sum(e.pipeline_total for e in entries)
            
            trend.append({
                "period": forecast.name,
                "year": forecast.year,
                "quota": total_quota,
                "closed_won": total_closed,
                "pipeline": total_pipeline,
                "attainment": (total_closed / total_quota * 100) if total_quota > 0 else 0,
            })
        
        return list(reversed(trend))
    
    # AI predictions (placeholder)
    async def generate_ai_forecast(
        self,
        entry_id: str
    ) -> dict[str, Any]:
        """Generate AI-powered forecast prediction."""
        entry = self.entries.get(entry_id)
        if not entry:
            return {}
        
        # Placeholder AI prediction
        # In real implementation, use ML model
        base_prediction = entry.weighted_amount
        
        return {
            "entry_id": entry_id,
            "predicted_close": base_prediction * (0.9 + random.random() * 0.2),
            "confidence": 0.7 + random.random() * 0.2,
            "factors": [
                {"name": "Historical close rate", "impact": "positive"},
                {"name": "Deal velocity", "impact": "neutral"},
                {"name": "Engagement signals", "impact": "positive"},
            ],
            "recommendations": [
                "Focus on deals in negotiation stage",
                "Review pushed deals for viability",
            ],
        }


# Singleton instance
_forecast_service: Optional[ForecastService] = None


def get_forecast_service() -> ForecastService:
    """Get forecast service singleton."""
    global _forecast_service
    if _forecast_service is None:
        _forecast_service = ForecastService()
    return _forecast_service
