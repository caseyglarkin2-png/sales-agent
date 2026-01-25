"""Create __init__ for models package."""
from src.models.prospect import Prospect, Task
from src.models.workflow import (
    Workflow,
    WorkflowStatus,
    WorkflowMode,
    DraftEmail,
    HubSpotTask,
    WorkflowError,
)
from src.models.form_submission import FormSubmission
from src.models.command_queue import (
    CommandQueueItem, 
    ActionRecommendation,
    ActionType,
    QueueItemStatus,
)
from src.models.auto_approval import (
    AutoApprovalRule,
    ApprovedRecipient,
    AutoApprovalLog,
    RuleType,
    ApprovalDecision,
)
from src.models.memory import (
    JarvisSession,
    ConversationMemory,
    MemorySummary,
)

__all__ = [
    "Prospect",
    "Task",
    "Workflow",
    "WorkflowStatus",
    "WorkflowMode",
    "DraftEmail",
    "HubSpotTask",
    "WorkflowError",
    "FormSubmission",
    "CommandQueueItem",
    "ActionRecommendation",
    "ActionType",
    "QueueItemStatus",
    "AutoApprovalRule",
    "ApprovedRecipient",
    "AutoApprovalLog",
    "RuleType",
    "ApprovalDecision",
    # Memory models for Jarvis persistence
    "JarvisSession",
    "ConversationMemory",
    "MemorySummary",
]
