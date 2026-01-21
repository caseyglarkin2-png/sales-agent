"""
Quota Management Service
========================
Sales quota definition, assignment, and tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Any, Optional
import uuid
from calendar import monthrange


class QuotaType(str, Enum):
    """Quota types."""
    REVENUE = "revenue"
    DEALS = "deals"
    UNITS = "units"
    CALLS = "calls"
    MEETINGS = "meetings"
    NEW_CUSTOMERS = "new_customers"
    PIPELINE = "pipeline"
    ACTIVITIES = "activities"


class QuotaPeriod(str, Enum):
    """Quota periods."""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    CUSTOM = "custom"


class QuotaStatus(str, Enum):
    """Quota status."""
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class AttainmentStatus(str, Enum):
    """Attainment status."""
    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    BEHIND = "behind"
    EXCEEDED = "exceeded"


@dataclass
class Quota:
    """Quota definition."""
    id: str
    name: str
    quota_type: QuotaType
    period: QuotaPeriod
    target: float
    org_id: str
    currency: str = "USD"
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: QuotaStatus = QuotaStatus.ACTIVE
    description: Optional[str] = None
    parent_quota_id: Optional[str] = None  # For hierarchical quotas
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None


@dataclass
class QuotaAssignment:
    """Quota assignment to user or team."""
    id: str
    quota_id: str
    assignee_type: str  # "user" or "team"
    assignee_id: str
    target: float
    weight: float = 1.0  # Weight for weighted quota distribution
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: QuotaStatus = QuotaStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class QuotaAttainment:
    """Quota attainment record."""
    id: str
    assignment_id: str
    period_start: date
    period_end: date
    target: float
    actual: float
    attainment_percent: float
    gap: float
    status: AttainmentStatus
    deals_count: int = 0
    pipeline_value: float = 0.0
    forecast_value: float = 0.0
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class QuotaHistory:
    """Quota change history."""
    id: str
    quota_id: str
    changed_by: str
    change_type: str  # "created", "updated", "target_changed", "status_changed"
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    changed_at: datetime = field(default_factory=datetime.utcnow)


class QuotaService:
    """
    Quota Management service.
    
    Handles quota creation, assignment, tracking, and attainment calculation.
    """
    
    def __init__(self):
        """Initialize quota service."""
        self.quotas: dict[str, Quota] = {}
        self.assignments: dict[str, QuotaAssignment] = {}
        self.attainments: dict[str, QuotaAttainment] = {}
        self.history: list[QuotaHistory] = []
    
    async def create_quota(
        self,
        name: str,
        quota_type: QuotaType,
        period: QuotaPeriod,
        target: float,
        org_id: str,
        currency: str = "USD",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        description: Optional[str] = None,
        parent_quota_id: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> Quota:
        """Create a new quota."""
        quota = Quota(
            id=str(uuid.uuid4()),
            name=name,
            quota_type=quota_type,
            period=period,
            target=target,
            org_id=org_id,
            currency=currency,
            start_date=start_date,
            end_date=end_date,
            description=description,
            parent_quota_id=parent_quota_id,
            created_by=created_by,
        )
        
        self.quotas[quota.id] = quota
        
        # Log history
        self.history.append(QuotaHistory(
            id=str(uuid.uuid4()),
            quota_id=quota.id,
            changed_by=created_by or "system",
            change_type="created",
            new_value={"name": name, "target": target},
        ))
        
        return quota
    
    async def get_quota(self, quota_id: str) -> Optional[Quota]:
        """Get a quota by ID."""
        return self.quotas.get(quota_id)
    
    async def list_quotas(
        self,
        org_id: str,
        quota_type: Optional[QuotaType] = None,
        period: Optional[QuotaPeriod] = None,
        status: Optional[QuotaStatus] = None,
    ) -> list[Quota]:
        """List quotas for an organization."""
        quotas = [q for q in self.quotas.values() if q.org_id == org_id]
        
        if quota_type:
            quotas = [q for q in quotas if q.quota_type == quota_type]
        
        if period:
            quotas = [q for q in quotas if q.period == period]
        
        if status:
            quotas = [q for q in quotas if q.status == status]
        
        return quotas
    
    async def update_quota(
        self,
        quota_id: str,
        name: Optional[str] = None,
        target: Optional[float] = None,
        status: Optional[QuotaStatus] = None,
        description: Optional[str] = None,
        updated_by: Optional[str] = None,
    ) -> Optional[Quota]:
        """Update a quota."""
        quota = self.quotas.get(quota_id)
        if not quota:
            return None
        
        if name:
            quota.name = name
        
        if target is not None:
            old_target = quota.target
            quota.target = target
            self.history.append(QuotaHistory(
                id=str(uuid.uuid4()),
                quota_id=quota_id,
                changed_by=updated_by or "system",
                change_type="target_changed",
                old_value=old_target,
                new_value=target,
            ))
        
        if status:
            old_status = quota.status
            quota.status = status
            self.history.append(QuotaHistory(
                id=str(uuid.uuid4()),
                quota_id=quota_id,
                changed_by=updated_by or "system",
                change_type="status_changed",
                old_value=old_status.value,
                new_value=status.value,
            ))
        
        if description is not None:
            quota.description = description
        
        quota.updated_at = datetime.utcnow()
        return quota
    
    async def delete_quota(self, quota_id: str) -> bool:
        """Delete a quota."""
        if quota_id in self.quotas:
            del self.quotas[quota_id]
            # Also delete assignments
            for a_id in list(self.assignments.keys()):
                if self.assignments[a_id].quota_id == quota_id:
                    del self.assignments[a_id]
            return True
        return False
    
    async def assign_quota(
        self,
        quota_id: str,
        assignee_type: str,
        assignee_id: str,
        target: Optional[float] = None,
        weight: float = 1.0,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Optional[QuotaAssignment]:
        """Assign a quota to a user or team."""
        quota = self.quotas.get(quota_id)
        if not quota:
            return None
        
        # Use quota target if not specified
        if target is None:
            target = quota.target
        
        assignment = QuotaAssignment(
            id=str(uuid.uuid4()),
            quota_id=quota_id,
            assignee_type=assignee_type,
            assignee_id=assignee_id,
            target=target,
            weight=weight,
            start_date=start_date or quota.start_date,
            end_date=end_date or quota.end_date,
        )
        
        self.assignments[assignment.id] = assignment
        return assignment
    
    async def get_assignment(self, assignment_id: str) -> Optional[QuotaAssignment]:
        """Get an assignment by ID."""
        return self.assignments.get(assignment_id)
    
    async def list_assignments(
        self,
        quota_id: Optional[str] = None,
        assignee_type: Optional[str] = None,
        assignee_id: Optional[str] = None,
    ) -> list[QuotaAssignment]:
        """List quota assignments."""
        assignments = list(self.assignments.values())
        
        if quota_id:
            assignments = [a for a in assignments if a.quota_id == quota_id]
        
        if assignee_type:
            assignments = [a for a in assignments if a.assignee_type == assignee_type]
        
        if assignee_id:
            assignments = [a for a in assignments if a.assignee_id == assignee_id]
        
        return assignments
    
    async def update_assignment(
        self,
        assignment_id: str,
        target: Optional[float] = None,
        status: Optional[QuotaStatus] = None,
    ) -> Optional[QuotaAssignment]:
        """Update an assignment."""
        assignment = self.assignments.get(assignment_id)
        if not assignment:
            return None
        
        if target is not None:
            assignment.target = target
        
        if status:
            assignment.status = status
        
        assignment.updated_at = datetime.utcnow()
        return assignment
    
    async def delete_assignment(self, assignment_id: str) -> bool:
        """Delete an assignment."""
        if assignment_id in self.assignments:
            del self.assignments[assignment_id]
            return True
        return False
    
    async def record_attainment(
        self,
        assignment_id: str,
        period_start: date,
        period_end: date,
        actual: float,
        deals_count: int = 0,
        pipeline_value: float = 0.0,
        forecast_value: float = 0.0,
    ) -> Optional[QuotaAttainment]:
        """Record quota attainment."""
        assignment = self.assignments.get(assignment_id)
        if not assignment:
            return None
        
        target = assignment.target
        attainment_percent = (actual / target * 100) if target > 0 else 0
        gap = target - actual
        
        # Determine status
        if attainment_percent >= 100:
            status = AttainmentStatus.EXCEEDED
        elif attainment_percent >= 75:
            status = AttainmentStatus.ON_TRACK
        elif attainment_percent >= 50:
            status = AttainmentStatus.AT_RISK
        else:
            status = AttainmentStatus.BEHIND
        
        attainment = QuotaAttainment(
            id=str(uuid.uuid4()),
            assignment_id=assignment_id,
            period_start=period_start,
            period_end=period_end,
            target=target,
            actual=actual,
            attainment_percent=attainment_percent,
            gap=gap,
            status=status,
            deals_count=deals_count,
            pipeline_value=pipeline_value,
            forecast_value=forecast_value,
        )
        
        self.attainments[attainment.id] = attainment
        return attainment
    
    async def get_attainment(
        self,
        assignment_id: str,
        period_start: Optional[date] = None,
    ) -> Optional[QuotaAttainment]:
        """Get attainment for an assignment."""
        for att in self.attainments.values():
            if att.assignment_id == assignment_id:
                if period_start is None or att.period_start == period_start:
                    return att
        return None
    
    async def list_attainments(
        self,
        assignment_id: Optional[str] = None,
        status: Optional[AttainmentStatus] = None,
    ) -> list[QuotaAttainment]:
        """List quota attainments."""
        attainments = list(self.attainments.values())
        
        if assignment_id:
            attainments = [a for a in attainments if a.assignment_id == assignment_id]
        
        if status:
            attainments = [a for a in attainments if a.status == status]
        
        return attainments
    
    async def get_user_quota_summary(
        self,
        user_id: str,
        org_id: str,
    ) -> dict[str, Any]:
        """Get quota summary for a user."""
        # Find user assignments
        assignments = [
            a for a in self.assignments.values()
            if a.assignee_type == "user" and a.assignee_id == user_id
        ]
        
        summaries = []
        total_target = 0.0
        total_actual = 0.0
        
        for assignment in assignments:
            quota = self.quotas.get(assignment.quota_id)
            if not quota or quota.org_id != org_id:
                continue
            
            # Get latest attainment
            attainment = await self.get_attainment(assignment.id)
            
            summary = {
                "quota_id": quota.id,
                "quota_name": quota.name,
                "quota_type": quota.quota_type.value,
                "period": quota.period.value,
                "target": assignment.target,
                "actual": attainment.actual if attainment else 0,
                "attainment_percent": attainment.attainment_percent if attainment else 0,
                "status": attainment.status.value if attainment else "no_data",
                "gap": attainment.gap if attainment else assignment.target,
            }
            summaries.append(summary)
            
            total_target += assignment.target
            if attainment:
                total_actual += attainment.actual
        
        overall_percent = (total_actual / total_target * 100) if total_target > 0 else 0
        
        return {
            "user_id": user_id,
            "quotas": summaries,
            "total_target": total_target,
            "total_actual": total_actual,
            "overall_attainment": overall_percent,
            "total_gap": total_target - total_actual,
        }
    
    async def get_team_quota_summary(
        self,
        team_id: str,
        org_id: str,
    ) -> dict[str, Any]:
        """Get quota summary for a team."""
        # Find team assignments
        assignments = [
            a for a in self.assignments.values()
            if a.assignee_type == "team" and a.assignee_id == team_id
        ]
        
        summaries = []
        total_target = 0.0
        total_actual = 0.0
        
        for assignment in assignments:
            quota = self.quotas.get(assignment.quota_id)
            if not quota or quota.org_id != org_id:
                continue
            
            attainment = await self.get_attainment(assignment.id)
            
            summary = {
                "quota_id": quota.id,
                "quota_name": quota.name,
                "target": assignment.target,
                "actual": attainment.actual if attainment else 0,
                "attainment_percent": attainment.attainment_percent if attainment else 0,
                "status": attainment.status.value if attainment else "no_data",
            }
            summaries.append(summary)
            
            total_target += assignment.target
            if attainment:
                total_actual += attainment.actual
        
        return {
            "team_id": team_id,
            "quotas": summaries,
            "total_target": total_target,
            "total_actual": total_actual,
            "overall_attainment": (total_actual / total_target * 100) if total_target > 0 else 0,
        }
    
    async def distribute_quota(
        self,
        quota_id: str,
        assignee_ids: list[str],
        assignee_type: str = "user",
        distribution: str = "equal",  # "equal", "weighted", "custom"
        custom_targets: Optional[dict[str, float]] = None,
    ) -> list[QuotaAssignment]:
        """Distribute quota among multiple assignees."""
        quota = self.quotas.get(quota_id)
        if not quota:
            return []
        
        assignments = []
        
        if distribution == "equal":
            per_assignee = quota.target / len(assignee_ids)
            for assignee_id in assignee_ids:
                assignment = await self.assign_quota(
                    quota_id=quota_id,
                    assignee_type=assignee_type,
                    assignee_id=assignee_id,
                    target=per_assignee,
                )
                if assignment:
                    assignments.append(assignment)
        
        elif distribution == "custom" and custom_targets:
            for assignee_id, target in custom_targets.items():
                assignment = await self.assign_quota(
                    quota_id=quota_id,
                    assignee_type=assignee_type,
                    assignee_id=assignee_id,
                    target=target,
                )
                if assignment:
                    assignments.append(assignment)
        
        return assignments
    
    async def get_quota_history(
        self,
        quota_id: str,
    ) -> list[QuotaHistory]:
        """Get quota change history."""
        return [h for h in self.history if h.quota_id == quota_id]
    
    async def get_leaderboard(
        self,
        org_id: str,
        quota_type: Optional[QuotaType] = None,
    ) -> list[dict[str, Any]]:
        """Get quota attainment leaderboard."""
        leaderboard = []
        
        for assignment in self.assignments.values():
            if assignment.assignee_type != "user":
                continue
            
            quota = self.quotas.get(assignment.quota_id)
            if not quota or quota.org_id != org_id:
                continue
            
            if quota_type and quota.quota_type != quota_type:
                continue
            
            attainment = await self.get_attainment(assignment.id)
            
            leaderboard.append({
                "user_id": assignment.assignee_id,
                "quota_name": quota.name,
                "target": assignment.target,
                "actual": attainment.actual if attainment else 0,
                "attainment_percent": attainment.attainment_percent if attainment else 0,
            })
        
        # Sort by attainment descending
        leaderboard.sort(key=lambda x: x["attainment_percent"], reverse=True)
        
        # Add rank
        for i, entry in enumerate(leaderboard):
            entry["rank"] = i + 1
        
        return leaderboard


# Singleton instance
_quota_service: Optional[QuotaService] = None


def get_quota_service() -> QuotaService:
    """Get or create quota service singleton."""
    global _quota_service
    if _quota_service is None:
        _quota_service = QuotaService()
    return _quota_service
