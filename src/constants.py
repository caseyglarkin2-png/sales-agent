"""Application constants."""

# Email constraints
MAX_EMAILS_PER_DAY = 20
MAX_EMAILS_PER_WEEK = 2
MAX_EMAILS_PER_CONTACT_PER_WEEK = 2

# Message patterns
MESSAGE_INTENT_PATTERNS = {
    "greeting": r"^(hi|hello|hey)\b",
    "question": r"\?$",
    "proposal": r"(would you|interested|opportunity|partnership)",
}

# Operator modes
class OperatorMode:
    """Operator mode configurations."""
    DRAFT_ONLY = "DRAFT_ONLY"
    SEND_ALLOWED = "SEND_ALLOWED"


# Draft statuses
class DraftStatus:
    """Draft status enumeration."""
    CREATED = "CREATED"
    SENT = "SENT"
    BLOCKED = "BLOCKED"
    REJECTED = "REJECTED"


# Task types
class TaskType:
    """Task type enumeration."""
    FOLLOW_UP = "FOLLOW_UP"
    RESEARCH = "RESEARCH"
    SYNC = "SYNC"
    VALIDATE = "VALIDATE"


# Feature flags
FEATURE_FLAGS = {
    "cold_start_demo": True,
    "validation_agent": False,
    "outcome_reporter": False,
}

# Monitoring thresholds
ALERT_THRESHOLD_EMAIL_RATE = 10  # per hour
ALERT_THRESHOLD_API_LATENCY = 1000  # ms
ALERT_THRESHOLD_ERROR_RATE = 5  # percent
