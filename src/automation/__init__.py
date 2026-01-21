"""
Automation Rules Module
=======================
Rule-based automation engine for sales workflows.
"""

from .automation_service import (
    AutomationService,
    AutomationRule,
    RuleCondition,
    RuleAction,
    RuleExecution,
    TriggerType,
    ConditionOperator,
    ActionType,
    get_automation_service,
)

__all__ = [
    "AutomationService",
    "AutomationRule",
    "RuleCondition",
    "RuleAction",
    "RuleExecution",
    "TriggerType",
    "ConditionOperator",
    "ActionType",
    "get_automation_service",
]
