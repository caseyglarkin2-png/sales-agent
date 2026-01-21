"""
Automation Service - Rule-Based Workflow Engine
================================================
Handles rule definitions, condition evaluation, and action execution.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional
import uuid


class TriggerType(str, Enum):
    """Types of triggers for automation rules."""
    # Record events
    RECORD_CREATED = "record_created"
    RECORD_UPDATED = "record_updated"
    RECORD_DELETED = "record_deleted"
    FIELD_CHANGED = "field_changed"
    
    # Deal/Pipeline events
    DEAL_STAGE_CHANGED = "deal_stage_changed"
    DEAL_WON = "deal_won"
    DEAL_LOST = "deal_lost"
    DEAL_AMOUNT_CHANGED = "deal_amount_changed"
    
    # Activity events
    EMAIL_OPENED = "email_opened"
    EMAIL_CLICKED = "email_clicked"
    EMAIL_REPLIED = "email_replied"
    EMAIL_BOUNCED = "email_bounced"
    CALL_COMPLETED = "call_completed"
    MEETING_SCHEDULED = "meeting_scheduled"
    MEETING_COMPLETED = "meeting_completed"
    
    # Time-based events
    SCHEDULE = "schedule"
    DATE_REACHED = "date_reached"
    INACTIVITY = "inactivity"
    
    # Score events
    SCORE_CHANGED = "score_changed"
    SCORE_THRESHOLD = "score_threshold"
    
    # Manual
    MANUAL = "manual"
    API_TRIGGERED = "api_triggered"


class ConditionOperator(str, Enum):
    """Operators for rule conditions."""
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
    BETWEEN = "between"
    REGEX_MATCH = "regex_match"
    IS_TRUE = "is_true"
    IS_FALSE = "is_false"


class ActionType(str, Enum):
    """Types of actions for automation rules."""
    # Field updates
    UPDATE_FIELD = "update_field"
    CLEAR_FIELD = "clear_field"
    INCREMENT_FIELD = "increment_field"
    
    # Record operations
    CREATE_RECORD = "create_record"
    UPDATE_RECORD = "update_record"
    DELETE_RECORD = "delete_record"
    
    # Assignment
    ASSIGN_OWNER = "assign_owner"
    ASSIGN_TEAM = "assign_team"
    ROUND_ROBIN = "round_robin"
    
    # Communication
    SEND_EMAIL = "send_email"
    SEND_NOTIFICATION = "send_notification"
    SEND_SLACK = "send_slack"
    SEND_SMS = "send_sms"
    
    # Task/Activity
    CREATE_TASK = "create_task"
    CREATE_FOLLOW_UP = "create_follow_up"
    SCHEDULE_CALL = "schedule_call"
    ADD_TO_SEQUENCE = "add_to_sequence"
    REMOVE_FROM_SEQUENCE = "remove_from_sequence"
    
    # Tags/Scoring
    ADD_TAG = "add_tag"
    REMOVE_TAG = "remove_tag"
    UPDATE_SCORE = "update_score"
    
    # Webhooks/Integration
    CALL_WEBHOOK = "call_webhook"
    TRIGGER_INTEGRATION = "trigger_integration"
    
    # Other
    WAIT = "wait"
    BRANCH = "branch"
    END = "end"


class EntityType(str, Enum):
    """Entity types for automation."""
    CONTACT = "contact"
    ACCOUNT = "account"
    DEAL = "deal"
    LEAD = "lead"
    TASK = "task"
    MEETING = "meeting"


@dataclass
class RuleCondition:
    """Condition for rule evaluation."""
    id: str
    field: str
    operator: ConditionOperator
    value: Any = None
    secondary_value: Any = None  # For BETWEEN operator
    logic: str = "and"  # and, or
    group_id: Optional[str] = None  # For grouping conditions


@dataclass
class RuleAction:
    """Action to execute when rule triggers."""
    id: str
    action_type: ActionType
    config: dict[str, Any] = field(default_factory=dict)
    order: int = 0
    delay_seconds: int = 0
    continue_on_error: bool = True


@dataclass
class RuleExecution:
    """Record of a rule execution."""
    id: str
    rule_id: str
    entity_type: EntityType
    entity_id: str
    trigger_type: TriggerType
    trigger_data: dict[str, Any] = field(default_factory=dict)
    conditions_met: bool = True
    actions_executed: list[dict[str, Any]] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    status: str = "running"  # running, completed, failed, cancelled
    error: Optional[str] = None


@dataclass
class AutomationRule:
    """Automation rule definition."""
    id: str
    name: str
    description: Optional[str] = None
    entity_type: EntityType = EntityType.CONTACT
    trigger_type: TriggerType = TriggerType.RECORD_UPDATED
    trigger_config: dict[str, Any] = field(default_factory=dict)
    conditions: list[RuleCondition] = field(default_factory=list)
    condition_logic: str = "all"  # all, any, custom
    actions: list[RuleAction] = field(default_factory=list)
    is_active: bool = True
    priority: int = 0
    max_executions: Optional[int] = None  # Per entity
    cooldown_seconds: int = 0  # Minimum time between executions
    execution_count: int = 0
    last_executed_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


class AutomationService:
    """Service for automation rule management."""
    
    def __init__(self):
        """Initialize automation service."""
        self.rules: dict[str, AutomationRule] = {}
        self.executions: dict[str, RuleExecution] = {}
        self._trigger_index: dict[TriggerType, list[str]] = {}  # trigger -> rule_ids
        self._entity_index: dict[EntityType, list[str]] = {}  # entity_type -> rule_ids
        self._execution_history: dict[str, list[str]] = {}  # entity_key -> execution_ids
    
    async def create_rule(
        self,
        name: str,
        entity_type: EntityType,
        trigger_type: TriggerType,
        conditions: Optional[list[dict[str, Any]]] = None,
        actions: Optional[list[dict[str, Any]]] = None,
        description: Optional[str] = None,
        trigger_config: Optional[dict[str, Any]] = None,
        condition_logic: str = "all",
        priority: int = 0,
        created_by: Optional[str] = None,
    ) -> AutomationRule:
        """Create a new automation rule."""
        rule_id = str(uuid.uuid4())
        
        # Convert conditions
        rule_conditions = []
        if conditions:
            for cond in conditions:
                rule_conditions.append(RuleCondition(
                    id=str(uuid.uuid4()),
                    field=cond.get("field", ""),
                    operator=ConditionOperator(cond.get("operator", "equals")),
                    value=cond.get("value"),
                    secondary_value=cond.get("secondary_value"),
                    logic=cond.get("logic", "and"),
                    group_id=cond.get("group_id"),
                ))
        
        # Convert actions
        rule_actions = []
        if actions:
            for i, act in enumerate(actions):
                rule_actions.append(RuleAction(
                    id=str(uuid.uuid4()),
                    action_type=ActionType(act.get("action_type", "update_field")),
                    config=act.get("config", {}),
                    order=act.get("order", i),
                    delay_seconds=act.get("delay_seconds", 0),
                    continue_on_error=act.get("continue_on_error", True),
                ))
        
        rule = AutomationRule(
            id=rule_id,
            name=name,
            description=description,
            entity_type=entity_type,
            trigger_type=trigger_type,
            trigger_config=trigger_config or {},
            conditions=rule_conditions,
            condition_logic=condition_logic,
            actions=rule_actions,
            priority=priority,
            created_by=created_by,
        )
        
        self.rules[rule_id] = rule
        
        # Update indexes
        if trigger_type not in self._trigger_index:
            self._trigger_index[trigger_type] = []
        self._trigger_index[trigger_type].append(rule_id)
        
        if entity_type not in self._entity_index:
            self._entity_index[entity_type] = []
        self._entity_index[entity_type].append(rule_id)
        
        return rule
    
    async def get_rule(self, rule_id: str) -> Optional[AutomationRule]:
        """Get rule by ID."""
        return self.rules.get(rule_id)
    
    async def update_rule(
        self,
        rule_id: str,
        updates: dict[str, Any]
    ) -> Optional[AutomationRule]:
        """Update automation rule."""
        rule = self.rules.get(rule_id)
        if not rule:
            return None
        
        for key, value in updates.items():
            if hasattr(rule, key) and key not in ['id', 'created_at', 'execution_count']:
                setattr(rule, key, value)
        
        rule.updated_at = datetime.utcnow()
        return rule
    
    async def delete_rule(self, rule_id: str) -> bool:
        """Delete automation rule."""
        rule = self.rules.get(rule_id)
        if not rule:
            return False
        
        # Remove from indexes
        if rule.trigger_type in self._trigger_index:
            if rule_id in self._trigger_index[rule.trigger_type]:
                self._trigger_index[rule.trigger_type].remove(rule_id)
        
        if rule.entity_type in self._entity_index:
            if rule_id in self._entity_index[rule.entity_type]:
                self._entity_index[rule.entity_type].remove(rule_id)
        
        del self.rules[rule_id]
        return True
    
    async def toggle_rule(self, rule_id: str, active: bool) -> Optional[AutomationRule]:
        """Enable or disable a rule."""
        rule = self.rules.get(rule_id)
        if not rule:
            return None
        
        rule.is_active = active
        rule.updated_at = datetime.utcnow()
        return rule
    
    async def list_rules(
        self,
        entity_type: Optional[EntityType] = None,
        trigger_type: Optional[TriggerType] = None,
        active_only: bool = True,
    ) -> list[AutomationRule]:
        """List automation rules."""
        rules = list(self.rules.values())
        
        if active_only:
            rules = [r for r in rules if r.is_active]
        
        if entity_type:
            rules = [r for r in rules if r.entity_type == entity_type]
        
        if trigger_type:
            rules = [r for r in rules if r.trigger_type == trigger_type]
        
        return sorted(rules, key=lambda r: (-r.priority, r.name))
    
    # Rule execution
    async def evaluate_trigger(
        self,
        trigger_type: TriggerType,
        entity_type: EntityType,
        entity_id: str,
        entity_data: dict[str, Any],
        trigger_data: Optional[dict[str, Any]] = None,
    ) -> list[RuleExecution]:
        """Evaluate and execute rules for a trigger."""
        executions = []
        
        # Find matching rules
        rule_ids = self._trigger_index.get(trigger_type, [])
        
        for rule_id in rule_ids:
            rule = self.rules.get(rule_id)
            if not rule or not rule.is_active:
                continue
            
            if rule.entity_type != entity_type:
                continue
            
            # Check cooldown
            if rule.cooldown_seconds > 0 and rule.last_executed_at:
                elapsed = (datetime.utcnow() - rule.last_executed_at).total_seconds()
                if elapsed < rule.cooldown_seconds:
                    continue
            
            # Evaluate conditions
            conditions_met = await self._evaluate_conditions(
                rule.conditions,
                rule.condition_logic,
                entity_data
            )
            
            if not conditions_met:
                continue
            
            # Execute actions
            execution = await self._execute_rule(
                rule, entity_type, entity_id, trigger_type, trigger_data or {}
            )
            executions.append(execution)
        
        return executions
    
    async def _evaluate_conditions(
        self,
        conditions: list[RuleCondition],
        logic: str,
        data: dict[str, Any]
    ) -> bool:
        """Evaluate rule conditions."""
        if not conditions:
            return True
        
        results = []
        for condition in conditions:
            result = await self._evaluate_condition(condition, data)
            results.append(result)
        
        if logic == "all":
            return all(results)
        elif logic == "any":
            return any(results)
        else:
            return all(results)
    
    async def _evaluate_condition(
        self,
        condition: RuleCondition,
        data: dict[str, Any]
    ) -> bool:
        """Evaluate a single condition."""
        field_value = data.get(condition.field)
        compare_value = condition.value
        
        op = condition.operator
        
        if op == ConditionOperator.EQUALS:
            return field_value == compare_value
        elif op == ConditionOperator.NOT_EQUALS:
            return field_value != compare_value
        elif op == ConditionOperator.CONTAINS:
            return compare_value in str(field_value) if field_value else False
        elif op == ConditionOperator.NOT_CONTAINS:
            return compare_value not in str(field_value) if field_value else True
        elif op == ConditionOperator.STARTS_WITH:
            return str(field_value).startswith(str(compare_value)) if field_value else False
        elif op == ConditionOperator.ENDS_WITH:
            return str(field_value).endswith(str(compare_value)) if field_value else False
        elif op == ConditionOperator.GREATER_THAN:
            return float(field_value) > float(compare_value) if field_value else False
        elif op == ConditionOperator.LESS_THAN:
            return float(field_value) < float(compare_value) if field_value else False
        elif op == ConditionOperator.GREATER_OR_EQUAL:
            return float(field_value) >= float(compare_value) if field_value else False
        elif op == ConditionOperator.LESS_OR_EQUAL:
            return float(field_value) <= float(compare_value) if field_value else False
        elif op == ConditionOperator.IS_EMPTY:
            return not field_value
        elif op == ConditionOperator.IS_NOT_EMPTY:
            return bool(field_value)
        elif op == ConditionOperator.IN_LIST:
            return field_value in compare_value if isinstance(compare_value, list) else False
        elif op == ConditionOperator.NOT_IN_LIST:
            return field_value not in compare_value if isinstance(compare_value, list) else True
        elif op == ConditionOperator.BETWEEN:
            if field_value and condition.secondary_value:
                return float(compare_value) <= float(field_value) <= float(condition.secondary_value)
            return False
        elif op == ConditionOperator.IS_TRUE:
            return bool(field_value)
        elif op == ConditionOperator.IS_FALSE:
            return not bool(field_value)
        
        return False
    
    async def _execute_rule(
        self,
        rule: AutomationRule,
        entity_type: EntityType,
        entity_id: str,
        trigger_type: TriggerType,
        trigger_data: dict[str, Any],
    ) -> RuleExecution:
        """Execute a rule's actions."""
        execution_id = str(uuid.uuid4())
        
        execution = RuleExecution(
            id=execution_id,
            rule_id=rule.id,
            entity_type=entity_type,
            entity_id=entity_id,
            trigger_type=trigger_type,
            trigger_data=trigger_data,
        )
        
        self.executions[execution_id] = execution
        
        # Track execution history
        entity_key = f"{entity_type.value}:{entity_id}"
        if entity_key not in self._execution_history:
            self._execution_history[entity_key] = []
        self._execution_history[entity_key].append(execution_id)
        
        # Execute actions in order
        sorted_actions = sorted(rule.actions, key=lambda a: a.order)
        
        for action in sorted_actions:
            action_result = await self._execute_action(action, entity_type, entity_id, trigger_data)
            execution.actions_executed.append(action_result)
            
            if not action_result["success"] and not action.continue_on_error:
                execution.status = "failed"
                execution.error = action_result.get("error")
                break
        
        if execution.status != "failed":
            execution.status = "completed"
        
        execution.completed_at = datetime.utcnow()
        
        # Update rule stats
        rule.execution_count += 1
        rule.last_executed_at = datetime.utcnow()
        
        return execution
    
    async def _execute_action(
        self,
        action: RuleAction,
        entity_type: EntityType,
        entity_id: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a single action."""
        result = {
            "action_id": action.id,
            "action_type": action.action_type.value,
            "success": True,
            "executed_at": datetime.utcnow().isoformat(),
        }
        
        try:
            # In production, these would call actual services
            if action.action_type == ActionType.UPDATE_FIELD:
                result["changes"] = {
                    "field": action.config.get("field"),
                    "value": action.config.get("value"),
                }
            elif action.action_type == ActionType.SEND_EMAIL:
                result["email_sent"] = True
                result["template_id"] = action.config.get("template_id")
            elif action.action_type == ActionType.CREATE_TASK:
                result["task_created"] = True
                result["task_title"] = action.config.get("title")
            elif action.action_type == ActionType.ADD_TAG:
                result["tag_added"] = action.config.get("tag_id")
            elif action.action_type == ActionType.SEND_NOTIFICATION:
                result["notification_sent"] = True
            elif action.action_type == ActionType.ASSIGN_OWNER:
                result["assigned_to"] = action.config.get("user_id")
            elif action.action_type == ActionType.UPDATE_SCORE:
                result["score_change"] = action.config.get("change")
            elif action.action_type == ActionType.CALL_WEBHOOK:
                result["webhook_url"] = action.config.get("url")
            # ... other action types
            
        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
        
        return result
    
    async def trigger_manually(
        self,
        rule_id: str,
        entity_type: EntityType,
        entity_id: str,
        entity_data: Optional[dict[str, Any]] = None,
    ) -> Optional[RuleExecution]:
        """Manually trigger a rule."""
        rule = self.rules.get(rule_id)
        if not rule:
            return None
        
        return await self._execute_rule(
            rule,
            entity_type,
            entity_id,
            TriggerType.MANUAL,
            entity_data or {}
        )
    
    async def get_execution(self, execution_id: str) -> Optional[RuleExecution]:
        """Get execution by ID."""
        return self.executions.get(execution_id)
    
    async def get_rule_executions(
        self,
        rule_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[RuleExecution]:
        """Get executions for a rule."""
        executions = [e for e in self.executions.values() if e.rule_id == rule_id]
        executions = sorted(executions, key=lambda e: e.started_at, reverse=True)
        return executions[offset:offset + limit]
    
    async def get_entity_executions(
        self,
        entity_type: EntityType,
        entity_id: str,
        limit: int = 50,
    ) -> list[RuleExecution]:
        """Get executions for an entity."""
        entity_key = f"{entity_type.value}:{entity_id}"
        execution_ids = self._execution_history.get(entity_key, [])
        
        executions = []
        for eid in execution_ids[-limit:]:
            execution = self.executions.get(eid)
            if execution:
                executions.append(execution)
        
        return sorted(executions, key=lambda e: e.started_at, reverse=True)
    
    async def get_rule_stats(self, rule_id: str) -> dict[str, Any]:
        """Get statistics for a rule."""
        rule = self.rules.get(rule_id)
        if not rule:
            return {}
        
        executions = [e for e in self.executions.values() if e.rule_id == rule_id]
        
        successful = len([e for e in executions if e.status == "completed"])
        failed = len([e for e in executions if e.status == "failed"])
        
        return {
            "rule_id": rule_id,
            "total_executions": len(executions),
            "successful": successful,
            "failed": failed,
            "success_rate": successful / len(executions) if executions else 0,
            "last_executed": rule.last_executed_at.isoformat() if rule.last_executed_at else None,
        }
    
    async def get_automation_stats(self) -> dict[str, Any]:
        """Get overall automation statistics."""
        active_rules = len([r for r in self.rules.values() if r.is_active])
        total_executions = len(self.executions)
        
        # Executions by status
        by_status: dict[str, int] = {}
        for e in self.executions.values():
            by_status[e.status] = by_status.get(e.status, 0) + 1
        
        # Top rules by execution
        top_rules = sorted(
            self.rules.values(),
            key=lambda r: r.execution_count,
            reverse=True
        )[:10]
        
        return {
            "total_rules": len(self.rules),
            "active_rules": active_rules,
            "total_executions": total_executions,
            "executions_by_status": by_status,
            "top_rules": [
                {"id": r.id, "name": r.name, "executions": r.execution_count}
                for r in top_rules
            ],
        }


# Singleton instance
_automation_service: Optional[AutomationService] = None


def get_automation_service() -> AutomationService:
    """Get automation service singleton."""
    global _automation_service
    if _automation_service is None:
        _automation_service = AutomationService()
    return _automation_service
