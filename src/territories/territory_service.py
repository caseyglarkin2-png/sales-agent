"""
Territory Service - Territory Management
=========================================
Handles territory definition and assignments.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
import uuid


class TerritoryType(str, Enum):
    """Territory type values."""
    GEOGRAPHIC = "geographic"
    NAMED_ACCOUNT = "named_account"
    INDUSTRY = "industry"
    COMPANY_SIZE = "company_size"
    CUSTOM = "custom"


class TerritoryStatus(str, Enum):
    """Territory status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class RuleOperator(str, Enum):
    """Rule comparison operators."""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    IN = "in"
    NOT_IN = "not_in"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    BETWEEN = "between"


class RuleField(str, Enum):
    """Fields used for territory rules."""
    COUNTRY = "country"
    STATE = "state"
    CITY = "city"
    POSTAL_CODE = "postal_code"
    REGION = "region"
    INDUSTRY = "industry"
    COMPANY_SIZE = "company_size"
    REVENUE = "revenue"
    EMPLOYEE_COUNT = "employee_count"
    COMPANY_NAME = "company_name"
    DOMAIN = "domain"
    CUSTOM_FIELD = "custom_field"


@dataclass
class TerritoryRule:
    """A rule for territory assignment."""
    id: str
    field: RuleField
    operator: RuleOperator
    value: Any  # Can be string, list, number, etc.
    custom_field_name: Optional[str] = None  # For CUSTOM_FIELD
    priority: int = 0
    is_active: bool = True


@dataclass
class TerritoryAssignment:
    """Assignment of a rep to a territory."""
    id: str
    territory_id: str
    user_id: str
    role: str = "owner"  # owner, member, backup
    quota: float = 0.0
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_primary: bool = False
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TerritoryMetrics:
    """Territory performance metrics."""
    account_count: int = 0
    deal_count: int = 0
    pipeline_value: float = 0.0
    closed_won: float = 0.0
    quota: float = 0.0
    attainment: float = 0.0


@dataclass
class Territory:
    """A sales territory."""
    id: str
    name: str
    description: str
    
    # Type and status
    territory_type: TerritoryType = TerritoryType.GEOGRAPHIC
    status: TerritoryStatus = TerritoryStatus.ACTIVE
    
    # Hierarchy
    parent_id: Optional[str] = None
    level: int = 0  # 0 = top level
    
    # Rules
    rules: list[TerritoryRule] = field(default_factory=list)
    rule_logic: str = "AND"  # AND or OR
    
    # Assignments
    assignments: list[TerritoryAssignment] = field(default_factory=list)
    
    # Metrics
    metrics: TerritoryMetrics = field(default_factory=TerritoryMetrics)
    
    # Settings
    auto_assign: bool = True
    allow_overlap: bool = False
    
    # Accounts
    named_accounts: list[str] = field(default_factory=list)  # Company IDs
    excluded_accounts: list[str] = field(default_factory=list)
    
    # Metadata
    color: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    custom_fields: dict[str, Any] = field(default_factory=dict)
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def primary_owner_id(self) -> Optional[str]:
        """Get primary owner ID."""
        for assignment in self.assignments:
            if assignment.is_primary and assignment.is_active:
                return assignment.user_id
        return None


class TerritoryService:
    """Service for territory management."""
    
    def __init__(self):
        self.territories: dict[str, Territory] = {}
        self.assignments: dict[str, TerritoryAssignment] = {}
        self._init_sample_territories()
    
    def _init_sample_territories(self) -> None:
        """Initialize sample territories."""
        # Create regional territories
        us_west = Territory(
            id="terr-us-west",
            name="US West",
            description="Western United States",
            territory_type=TerritoryType.GEOGRAPHIC,
            rules=[
                TerritoryRule(
                    id="rule-1",
                    field=RuleField.STATE,
                    operator=RuleOperator.IN,
                    value=["CA", "WA", "OR", "NV", "AZ", "UT", "CO"]
                )
            ],
        )
        
        us_east = Territory(
            id="terr-us-east",
            name="US East",
            description="Eastern United States",
            territory_type=TerritoryType.GEOGRAPHIC,
            rules=[
                TerritoryRule(
                    id="rule-2",
                    field=RuleField.STATE,
                    operator=RuleOperator.IN,
                    value=["NY", "NJ", "PA", "MA", "CT", "VA", "MD", "DC"]
                )
            ],
        )
        
        self.territories[us_west.id] = us_west
        self.territories[us_east.id] = us_east
    
    # Territory CRUD
    async def create_territory(
        self,
        name: str,
        description: str,
        territory_type: TerritoryType = TerritoryType.GEOGRAPHIC,
        parent_id: Optional[str] = None,
        **kwargs
    ) -> Territory:
        """Create a new territory."""
        territory_id = str(uuid.uuid4())
        
        # Determine level
        level = 0
        if parent_id and parent_id in self.territories:
            level = self.territories[parent_id].level + 1
        
        territory = Territory(
            id=territory_id,
            name=name,
            description=description,
            territory_type=territory_type,
            parent_id=parent_id,
            level=level,
            **kwargs
        )
        
        self.territories[territory_id] = territory
        return territory
    
    async def get_territory(self, territory_id: str) -> Optional[Territory]:
        """Get a territory by ID."""
        return self.territories.get(territory_id)
    
    async def update_territory(
        self,
        territory_id: str,
        updates: dict[str, Any]
    ) -> Optional[Territory]:
        """Update a territory."""
        territory = self.territories.get(territory_id)
        if not territory:
            return None
        
        for key, value in updates.items():
            if hasattr(territory, key):
                setattr(territory, key, value)
        
        territory.updated_at = datetime.utcnow()
        return territory
    
    async def delete_territory(self, territory_id: str) -> bool:
        """Delete a territory."""
        if territory_id in self.territories:
            del self.territories[territory_id]
            return True
        return False
    
    async def list_territories(
        self,
        territory_type: Optional[TerritoryType] = None,
        status: Optional[TerritoryStatus] = None,
        parent_id: Optional[str] = None,
        owner_id: Optional[str] = None
    ) -> list[Territory]:
        """List territories with filters."""
        territories = list(self.territories.values())
        
        if territory_type:
            territories = [t for t in territories if t.territory_type == territory_type]
        if status:
            territories = [t for t in territories if t.status == status]
        if parent_id is not None:
            territories = [t for t in territories if t.parent_id == parent_id]
        if owner_id:
            territories = [
                t for t in territories
                if any(a.user_id == owner_id and a.is_active for a in t.assignments)
            ]
        
        territories.sort(key=lambda t: (t.level, t.name))
        return territories
    
    async def get_territory_hierarchy(self, territory_id: str) -> list[Territory]:
        """Get territory and all ancestors."""
        hierarchy = []
        current = self.territories.get(territory_id)
        
        while current:
            hierarchy.insert(0, current)
            if current.parent_id:
                current = self.territories.get(current.parent_id)
            else:
                break
        
        return hierarchy
    
    async def get_children(self, territory_id: str) -> list[Territory]:
        """Get child territories."""
        return [
            t for t in self.territories.values()
            if t.parent_id == territory_id
        ]
    
    # Rules
    async def add_rule(
        self,
        territory_id: str,
        field: RuleField,
        operator: RuleOperator,
        value: Any,
        **kwargs
    ) -> Optional[TerritoryRule]:
        """Add a rule to a territory."""
        territory = self.territories.get(territory_id)
        if not territory:
            return None
        
        rule = TerritoryRule(
            id=str(uuid.uuid4()),
            field=field,
            operator=operator,
            value=value,
            **kwargs
        )
        
        territory.rules.append(rule)
        territory.updated_at = datetime.utcnow()
        
        return rule
    
    async def update_rule(
        self,
        territory_id: str,
        rule_id: str,
        updates: dict[str, Any]
    ) -> Optional[TerritoryRule]:
        """Update a rule."""
        territory = self.territories.get(territory_id)
        if not territory:
            return None
        
        for rule in territory.rules:
            if rule.id == rule_id:
                for key, value in updates.items():
                    if hasattr(rule, key):
                        setattr(rule, key, value)
                territory.updated_at = datetime.utcnow()
                return rule
        
        return None
    
    async def remove_rule(self, territory_id: str, rule_id: str) -> bool:
        """Remove a rule."""
        territory = self.territories.get(territory_id)
        if not territory:
            return False
        
        original_count = len(territory.rules)
        territory.rules = [r for r in territory.rules if r.id != rule_id]
        
        if len(territory.rules) < original_count:
            territory.updated_at = datetime.utcnow()
            return True
        
        return False
    
    # Assignments
    async def assign_user(
        self,
        territory_id: str,
        user_id: str,
        role: str = "owner",
        is_primary: bool = False,
        quota: float = 0.0,
        **kwargs
    ) -> Optional[TerritoryAssignment]:
        """Assign a user to a territory."""
        territory = self.territories.get(territory_id)
        if not territory:
            return None
        
        # Check if already assigned
        for existing in territory.assignments:
            if existing.user_id == user_id and existing.is_active:
                return existing
        
        # If setting as primary, unset others
        if is_primary:
            for assignment in territory.assignments:
                assignment.is_primary = False
        
        assignment = TerritoryAssignment(
            id=str(uuid.uuid4()),
            territory_id=territory_id,
            user_id=user_id,
            role=role,
            is_primary=is_primary,
            quota=quota,
            **kwargs
        )
        
        territory.assignments.append(assignment)
        self.assignments[assignment.id] = assignment
        territory.updated_at = datetime.utcnow()
        
        return assignment
    
    async def update_assignment(
        self,
        assignment_id: str,
        updates: dict[str, Any]
    ) -> Optional[TerritoryAssignment]:
        """Update an assignment."""
        assignment = self.assignments.get(assignment_id)
        if not assignment:
            return None
        
        for key, value in updates.items():
            if hasattr(assignment, key):
                setattr(assignment, key, value)
        
        return assignment
    
    async def remove_assignment(
        self,
        territory_id: str,
        user_id: str
    ) -> bool:
        """Remove a user from a territory."""
        territory = self.territories.get(territory_id)
        if not territory:
            return False
        
        for assignment in territory.assignments:
            if assignment.user_id == user_id and assignment.is_active:
                assignment.is_active = False
                assignment.end_date = datetime.utcnow()
                territory.updated_at = datetime.utcnow()
                return True
        
        return False
    
    async def get_user_territories(self, user_id: str) -> list[Territory]:
        """Get all territories a user is assigned to."""
        return [
            t for t in self.territories.values()
            if any(a.user_id == user_id and a.is_active for a in t.assignments)
        ]
    
    async def get_territory_team(self, territory_id: str) -> list[dict[str, Any]]:
        """Get team members for a territory."""
        territory = self.territories.get(territory_id)
        if not territory:
            return []
        
        return [
            {
                "assignment_id": a.id,
                "user_id": a.user_id,
                "role": a.role,
                "is_primary": a.is_primary,
                "quota": a.quota,
                "start_date": a.start_date.isoformat() if a.start_date else None,
            }
            for a in territory.assignments
            if a.is_active
        ]
    
    # Named accounts
    async def add_named_account(
        self,
        territory_id: str,
        company_id: str
    ) -> bool:
        """Add a named account to a territory."""
        territory = self.territories.get(territory_id)
        if not territory:
            return False
        
        if company_id not in territory.named_accounts:
            territory.named_accounts.append(company_id)
            territory.updated_at = datetime.utcnow()
        
        return True
    
    async def remove_named_account(
        self,
        territory_id: str,
        company_id: str
    ) -> bool:
        """Remove a named account."""
        territory = self.territories.get(territory_id)
        if not territory:
            return False
        
        if company_id in territory.named_accounts:
            territory.named_accounts.remove(company_id)
            territory.updated_at = datetime.utcnow()
            return True
        
        return False
    
    async def add_excluded_account(
        self,
        territory_id: str,
        company_id: str
    ) -> bool:
        """Add an excluded account."""
        territory = self.territories.get(territory_id)
        if not territory:
            return False
        
        if company_id not in territory.excluded_accounts:
            territory.excluded_accounts.append(company_id)
            territory.updated_at = datetime.utcnow()
        
        return True
    
    # Territory matching
    async def match_territory(
        self,
        company_data: dict[str, Any]
    ) -> Optional[Territory]:
        """Find matching territory for a company."""
        matching_territories = []
        
        for territory in self.territories.values():
            if territory.status != TerritoryStatus.ACTIVE:
                continue
            
            # Check if in excluded accounts
            company_id = company_data.get("id")
            if company_id and company_id in territory.excluded_accounts:
                continue
            
            # Check if named account
            if company_id and company_id in territory.named_accounts:
                matching_territories.append((territory, 1000))  # High priority
                continue
            
            # Evaluate rules
            if territory.rules:
                match = self._evaluate_rules(territory, company_data)
                if match:
                    matching_territories.append((territory, territory.level))
        
        if not matching_territories:
            return None
        
        # Return highest priority (lowest level = more specific)
        matching_territories.sort(key=lambda x: (-x[1], x[0].name))
        return matching_territories[0][0]
    
    def _evaluate_rules(
        self,
        territory: Territory,
        company_data: dict[str, Any]
    ) -> bool:
        """Evaluate territory rules against company data."""
        if not territory.rules:
            return True
        
        results = []
        
        for rule in territory.rules:
            if not rule.is_active:
                continue
            
            # Get field value
            field_name = rule.field.value
            if rule.field == RuleField.CUSTOM_FIELD:
                field_name = rule.custom_field_name
            
            value = company_data.get(field_name)
            
            # Evaluate rule
            match = self._evaluate_rule(rule, value)
            results.append(match)
        
        if not results:
            return True
        
        if territory.rule_logic == "AND":
            return all(results)
        else:  # OR
            return any(results)
    
    def _evaluate_rule(self, rule: TerritoryRule, value: Any) -> bool:
        """Evaluate a single rule."""
        if value is None:
            return False
        
        rule_value = rule.value
        
        if rule.operator == RuleOperator.EQUALS:
            return str(value).lower() == str(rule_value).lower()
        elif rule.operator == RuleOperator.NOT_EQUALS:
            return str(value).lower() != str(rule_value).lower()
        elif rule.operator == RuleOperator.CONTAINS:
            return str(rule_value).lower() in str(value).lower()
        elif rule.operator == RuleOperator.NOT_CONTAINS:
            return str(rule_value).lower() not in str(value).lower()
        elif rule.operator == RuleOperator.STARTS_WITH:
            return str(value).lower().startswith(str(rule_value).lower())
        elif rule.operator == RuleOperator.ENDS_WITH:
            return str(value).lower().endswith(str(rule_value).lower())
        elif rule.operator == RuleOperator.IN:
            if isinstance(rule_value, list):
                return value in rule_value
            return False
        elif rule.operator == RuleOperator.NOT_IN:
            if isinstance(rule_value, list):
                return value not in rule_value
            return False
        elif rule.operator == RuleOperator.GREATER_THAN:
            try:
                return float(value) > float(rule_value)
            except ValueError:
                return False
        elif rule.operator == RuleOperator.LESS_THAN:
            try:
                return float(value) < float(rule_value)
            except ValueError:
                return False
        elif rule.operator == RuleOperator.BETWEEN:
            if isinstance(rule_value, list) and len(rule_value) == 2:
                try:
                    return float(rule_value[0]) <= float(value) <= float(rule_value[1])
                except ValueError:
                    return False
            return False
        
        return False
    
    async def bulk_assign(
        self,
        company_ids: list[str],
        company_data_fetcher  # Callable to get company data
    ) -> dict[str, Optional[str]]:
        """Bulk assign companies to territories."""
        results = {}
        
        for company_id in company_ids:
            company_data = await company_data_fetcher(company_id)
            if company_data:
                territory = await self.match_territory(company_data)
                results[company_id] = territory.id if territory else None
            else:
                results[company_id] = None
        
        return results
    
    # Metrics
    async def update_metrics(
        self,
        territory_id: str,
        metrics: TerritoryMetrics
    ) -> bool:
        """Update territory metrics."""
        territory = self.territories.get(territory_id)
        if not territory:
            return False
        
        territory.metrics = metrics
        territory.updated_at = datetime.utcnow()
        return True
    
    async def get_territory_stats(
        self,
        territory_id: str
    ) -> Optional[dict[str, Any]]:
        """Get territory statistics."""
        territory = self.territories.get(territory_id)
        if not territory:
            return None
        
        children = await self.get_children(territory_id)
        
        return {
            "territory_id": territory.id,
            "name": territory.name,
            "type": territory.territory_type.value,
            "status": territory.status.value,
            "level": territory.level,
            "child_count": len(children),
            "assignment_count": len([a for a in territory.assignments if a.is_active]),
            "named_account_count": len(territory.named_accounts),
            "rule_count": len(territory.rules),
            "metrics": {
                "account_count": territory.metrics.account_count,
                "deal_count": territory.metrics.deal_count,
                "pipeline_value": territory.metrics.pipeline_value,
                "closed_won": territory.metrics.closed_won,
                "quota": territory.metrics.quota,
                "attainment": territory.metrics.attainment,
            },
        }
    
    # Export/Import
    async def export_territories(self) -> dict[str, Any]:
        """Export all territories."""
        return {
            "territories": [
                {
                    "id": t.id,
                    "name": t.name,
                    "description": t.description,
                    "type": t.territory_type.value,
                    "status": t.status.value,
                    "parent_id": t.parent_id,
                    "rules": [
                        {
                            "field": r.field.value,
                            "operator": r.operator.value,
                            "value": r.value,
                        }
                        for r in t.rules
                    ],
                    "rule_logic": t.rule_logic,
                    "named_accounts": t.named_accounts,
                }
                for t in self.territories.values()
            ],
            "exported_at": datetime.utcnow().isoformat(),
        }


# Singleton instance
_territory_service: Optional[TerritoryService] = None


def get_territory_service() -> TerritoryService:
    """Get territory service singleton."""
    global _territory_service
    if _territory_service is None:
        _territory_service = TerritoryService()
    return _territory_service
