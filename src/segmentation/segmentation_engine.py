"""
Smart Segmentation Engine
==========================
Dynamic contact segmentation based on attributes, behaviors, and engagement.
Supports complex rule combinations with AND/OR logic.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional
import structlog
import uuid

logger = structlog.get_logger(__name__)


class RuleOperator(str, Enum):
    """Operators for segment rules."""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_OR_EQUAL = "greater_or_equal"
    LESS_OR_EQUAL = "less_or_equal"
    IS_EMPTY = "is_empty"
    IS_NOT_EMPTY = "is_not_empty"
    IN_LIST = "in_list"
    NOT_IN_LIST = "not_in_list"
    BEFORE = "before"
    AFTER = "after"
    WITHIN_DAYS = "within_days"


@dataclass
class SegmentRule:
    """A single rule in a segment."""
    id: str
    field: str
    operator: RuleOperator
    value: Any = None
    is_active: bool = True
    
    def evaluate(self, contact: dict) -> bool:
        """Evaluate this rule against a contact."""
        actual_value = self._get_nested_value(contact, self.field)
        
        if self.operator == RuleOperator.EQUALS:
            return str(actual_value).lower() == str(self.value).lower() if actual_value else False
        
        elif self.operator == RuleOperator.NOT_EQUALS:
            return str(actual_value).lower() != str(self.value).lower() if actual_value else True
        
        elif self.operator == RuleOperator.CONTAINS:
            return str(self.value).lower() in str(actual_value).lower() if actual_value else False
        
        elif self.operator == RuleOperator.NOT_CONTAINS:
            return str(self.value).lower() not in str(actual_value).lower() if actual_value else True
        
        elif self.operator == RuleOperator.STARTS_WITH:
            return str(actual_value).lower().startswith(str(self.value).lower()) if actual_value else False
        
        elif self.operator == RuleOperator.ENDS_WITH:
            return str(actual_value).lower().endswith(str(self.value).lower()) if actual_value else False
        
        elif self.operator == RuleOperator.GREATER_THAN:
            return float(actual_value) > float(self.value) if actual_value else False
        
        elif self.operator == RuleOperator.LESS_THAN:
            return float(actual_value) < float(self.value) if actual_value else False
        
        elif self.operator == RuleOperator.GREATER_OR_EQUAL:
            return float(actual_value) >= float(self.value) if actual_value else False
        
        elif self.operator == RuleOperator.LESS_OR_EQUAL:
            return float(actual_value) <= float(self.value) if actual_value else False
        
        elif self.operator == RuleOperator.IS_EMPTY:
            return not actual_value
        
        elif self.operator == RuleOperator.IS_NOT_EMPTY:
            return bool(actual_value)
        
        elif self.operator == RuleOperator.IN_LIST:
            if isinstance(self.value, list):
                return str(actual_value).lower() in [str(v).lower() for v in self.value]
            return False
        
        elif self.operator == RuleOperator.NOT_IN_LIST:
            if isinstance(self.value, list):
                return str(actual_value).lower() not in [str(v).lower() for v in self.value]
            return True
        
        elif self.operator == RuleOperator.BEFORE:
            if actual_value:
                actual_date = self._parse_date(actual_value)
                target_date = self._parse_date(self.value)
                return actual_date < target_date if actual_date and target_date else False
            return False
        
        elif self.operator == RuleOperator.AFTER:
            if actual_value:
                actual_date = self._parse_date(actual_value)
                target_date = self._parse_date(self.value)
                return actual_date > target_date if actual_date and target_date else False
            return False
        
        elif self.operator == RuleOperator.WITHIN_DAYS:
            if actual_value:
                actual_date = self._parse_date(actual_value)
                if actual_date:
                    days = int(self.value)
                    threshold = datetime.utcnow() - timedelta(days=days)
                    return actual_date >= threshold
            return False
        
        return False
    
    def _get_nested_value(self, obj: dict, path: str) -> Any:
        """Get a nested value from a dict using dot notation."""
        keys = path.split(".")
        value = obj
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value
    
    def _parse_date(self, value: Any) -> Optional[datetime]:
        """Parse a date value."""
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None
        return None
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "field": self.field,
            "operator": self.operator.value,
            "value": self.value,
            "is_active": self.is_active,
        }


@dataclass
class SegmentMembership:
    """Record of a contact's segment membership."""
    contact_id: str
    segment_id: str
    added_at: datetime = field(default_factory=datetime.utcnow)
    removed_at: Optional[datetime] = None
    is_active: bool = True
    
    def to_dict(self) -> dict:
        return {
            "contact_id": self.contact_id,
            "segment_id": self.segment_id,
            "added_at": self.added_at.isoformat(),
            "removed_at": self.removed_at.isoformat() if self.removed_at else None,
            "is_active": self.is_active,
        }


@dataclass
class Segment:
    """A contact segment with rules."""
    id: str
    name: str
    description: str = ""
    rules: list[SegmentRule] = field(default_factory=list)
    match_type: str = "all"  # all (AND) or any (OR)
    is_dynamic: bool = True  # Dynamic segments auto-update
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    member_count: int = 0
    last_evaluated_at: Optional[datetime] = None
    metadata: dict = field(default_factory=dict)
    
    def evaluate_contact(self, contact: dict) -> bool:
        """Check if a contact matches this segment."""
        if not self.is_active:
            return False
        
        active_rules = [r for r in self.rules if r.is_active]
        
        if not active_rules:
            return False
        
        results = [rule.evaluate(contact) for rule in active_rules]
        
        if self.match_type == "all":
            return all(results)
        return any(results)
    
    def add_rule(
        self,
        field: str,
        operator: RuleOperator,
        value: Any = None,
    ) -> SegmentRule:
        """Add a rule to this segment."""
        rule = SegmentRule(
            id=str(uuid.uuid4()),
            field=field,
            operator=operator,
            value=value,
        )
        self.rules.append(rule)
        self.updated_at = datetime.utcnow()
        return rule
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule from this segment."""
        for i, rule in enumerate(self.rules):
            if rule.id == rule_id:
                self.rules.pop(i)
                self.updated_at = datetime.utcnow()
                return True
        return False
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "rules": [r.to_dict() for r in self.rules],
            "match_type": self.match_type,
            "is_dynamic": self.is_dynamic,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "member_count": self.member_count,
            "last_evaluated_at": self.last_evaluated_at.isoformat() if self.last_evaluated_at else None,
        }


class SegmentationEngine:
    """
    Manages contact segmentation with dynamic rules.
    """
    
    def __init__(self):
        self.segments: dict[str, Segment] = {}
        self.memberships: dict[str, list[SegmentMembership]] = {}  # segment_id -> memberships
        self._setup_default_segments()
    
    def _setup_default_segments(self) -> None:
        """Set up default segments."""
        # Hot leads
        hot_leads = self.create_segment(
            name="Hot Leads",
            description="High-scoring leads ready for outreach",
        )
        hot_leads.add_rule("score", RuleOperator.GREATER_OR_EQUAL, 80)
        hot_leads.add_rule("last_activity_at", RuleOperator.WITHIN_DAYS, 7)
        
        # Decision makers
        dm_segment = self.create_segment(
            name="Decision Makers",
            description="C-level and VP contacts",
        )
        dm_segment.add_rule("title", RuleOperator.IN_LIST, [
            "CEO", "CTO", "CFO", "COO", "CMO", "CRO",
            "VP", "Vice President", "Director", "Head of"
        ])
        
        # Engaged contacts
        engaged = self.create_segment(
            name="Engaged Contacts",
            description="Contacts with recent engagement",
        )
        engaged.add_rule("emails_opened", RuleOperator.GREATER_THAN, 0)
        engaged.add_rule("last_email_opened_at", RuleOperator.WITHIN_DAYS, 30)
        
        # Tech industry
        tech = self.create_segment(
            name="Tech Industry",
            description="Contacts in technology companies",
        )
        tech.add_rule("company.industry", RuleOperator.CONTAINS, "technology")
        
        # Enterprise accounts
        enterprise = self.create_segment(
            name="Enterprise Accounts",
            description="Large company contacts",
        )
        enterprise.add_rule("company.employee_count", RuleOperator.GREATER_OR_EQUAL, 1000)
        
        # New leads this week
        new_leads = self.create_segment(
            name="New Leads This Week",
            description="Leads added in the last 7 days",
        )
        new_leads.add_rule("created_at", RuleOperator.WITHIN_DAYS, 7)
        
        logger.info("default_segments_created", count=6)
    
    def create_segment(
        self,
        name: str,
        description: str = "",
        match_type: str = "all",
        is_dynamic: bool = True,
    ) -> Segment:
        """Create a new segment."""
        segment = Segment(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            match_type=match_type,
            is_dynamic=is_dynamic,
        )
        
        self.segments[segment.id] = segment
        self.memberships[segment.id] = []
        
        logger.info("segment_created", segment_id=segment.id, name=name)
        
        return segment
    
    def get_segment(self, segment_id: str) -> Optional[Segment]:
        """Get a segment by ID."""
        return self.segments.get(segment_id)
    
    def get_segment_by_name(self, name: str) -> Optional[Segment]:
        """Get a segment by name."""
        for segment in self.segments.values():
            if segment.name.lower() == name.lower():
                return segment
        return None
    
    def list_segments(self, active_only: bool = True) -> list[Segment]:
        """List all segments."""
        segments = list(self.segments.values())
        if active_only:
            segments = [s for s in segments if s.is_active]
        return sorted(segments, key=lambda s: s.name)
    
    def update_segment(
        self,
        segment_id: str,
        updates: dict,
    ) -> Optional[Segment]:
        """Update a segment."""
        segment = self.segments.get(segment_id)
        if not segment:
            return None
        
        for key, value in updates.items():
            if hasattr(segment, key) and key not in ["id", "created_at", "rules"]:
                setattr(segment, key, value)
        
        segment.updated_at = datetime.utcnow()
        return segment
    
    def delete_segment(self, segment_id: str) -> bool:
        """Delete a segment."""
        if segment_id in self.segments:
            del self.segments[segment_id]
            if segment_id in self.memberships:
                del self.memberships[segment_id]
            return True
        return False
    
    def add_rule_to_segment(
        self,
        segment_id: str,
        field: str,
        operator: str,
        value: Any = None,
    ) -> Optional[SegmentRule]:
        """Add a rule to a segment."""
        segment = self.segments.get(segment_id)
        if not segment:
            return None
        
        try:
            op = RuleOperator(operator)
        except ValueError:
            return None
        
        return segment.add_rule(field, op, value)
    
    def remove_rule_from_segment(
        self,
        segment_id: str,
        rule_id: str,
    ) -> bool:
        """Remove a rule from a segment."""
        segment = self.segments.get(segment_id)
        if not segment:
            return False
        return segment.remove_rule(rule_id)
    
    def evaluate_contact(
        self,
        contact: dict,
        segment_id: str = None,
    ) -> dict[str, bool]:
        """Evaluate which segments a contact belongs to."""
        results = {}
        
        segments_to_check = (
            [self.segments[segment_id]] if segment_id and segment_id in self.segments
            else self.segments.values()
        )
        
        for segment in segments_to_check:
            if segment.is_active:
                results[segment.id] = segment.evaluate_contact(contact)
        
        return results
    
    def get_contacts_in_segment(
        self,
        segment_id: str,
        contacts: list[dict],
    ) -> list[dict]:
        """Get all contacts that match a segment."""
        segment = self.segments.get(segment_id)
        if not segment:
            return []
        
        matching = []
        for contact in contacts:
            if segment.evaluate_contact(contact):
                matching.append(contact)
        
        # Update segment member count
        segment.member_count = len(matching)
        segment.last_evaluated_at = datetime.utcnow()
        
        return matching
    
    def refresh_segment_membership(
        self,
        segment_id: str,
        contacts: list[dict],
    ) -> dict:
        """Refresh membership for a segment."""
        segment = self.segments.get(segment_id)
        if not segment:
            return {"error": "Segment not found"}
        
        # Get current members
        current_members = {m.contact_id for m in self.memberships.get(segment_id, []) if m.is_active}
        
        # Evaluate all contacts
        new_members = set()
        for contact in contacts:
            if segment.evaluate_contact(contact):
                contact_id = contact.get("id")
                if contact_id:
                    new_members.add(contact_id)
        
        # Find added and removed
        added = new_members - current_members
        removed = current_members - new_members
        
        # Update memberships
        now = datetime.utcnow()
        
        for contact_id in added:
            membership = SegmentMembership(
                contact_id=contact_id,
                segment_id=segment_id,
            )
            self.memberships[segment_id].append(membership)
        
        for membership in self.memberships.get(segment_id, []):
            if membership.contact_id in removed and membership.is_active:
                membership.is_active = False
                membership.removed_at = now
        
        segment.member_count = len(new_members)
        segment.last_evaluated_at = now
        
        return {
            "segment_id": segment_id,
            "total_members": len(new_members),
            "added": len(added),
            "removed": len(removed),
        }
    
    def get_segment_stats(self, segment_id: str) -> dict:
        """Get statistics for a segment."""
        segment = self.segments.get(segment_id)
        if not segment:
            return {"error": "Segment not found"}
        
        memberships = self.memberships.get(segment_id, [])
        active_memberships = [m for m in memberships if m.is_active]
        
        return {
            "segment_id": segment_id,
            "name": segment.name,
            "member_count": len(active_memberships),
            "total_historical_members": len(memberships),
            "rules_count": len([r for r in segment.rules if r.is_active]),
            "is_dynamic": segment.is_dynamic,
            "last_evaluated_at": segment.last_evaluated_at.isoformat() if segment.last_evaluated_at else None,
        }
    
    def preview_segment(
        self,
        rules: list[dict],
        match_type: str,
        contacts: list[dict],
        limit: int = 10,
    ) -> dict:
        """Preview segment membership without creating it."""
        # Create temporary segment
        temp_segment = Segment(
            id="preview",
            name="Preview",
            match_type=match_type,
        )
        
        for rule_data in rules:
            try:
                operator = RuleOperator(rule_data.get("operator"))
                rule = SegmentRule(
                    id=str(uuid.uuid4()),
                    field=rule_data.get("field", ""),
                    operator=operator,
                    value=rule_data.get("value"),
                )
                temp_segment.rules.append(rule)
            except ValueError:
                continue
        
        # Evaluate contacts
        matching = []
        for contact in contacts:
            if temp_segment.evaluate_contact(contact):
                matching.append(contact)
        
        return {
            "total_matching": len(matching),
            "sample": matching[:limit],
            "rules_count": len(temp_segment.rules),
        }


# Singleton instance
_engine: Optional[SegmentationEngine] = None


def get_segmentation_engine() -> SegmentationEngine:
    """Get the segmentation engine singleton."""
    global _engine
    if _engine is None:
        _engine = SegmentationEngine()
    return _engine
