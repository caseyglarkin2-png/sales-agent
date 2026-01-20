"""Rate limiting and quota management for operator mode."""
from datetime import datetime, timedelta
from typing import Dict

from src.logger import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """Enforce rate limits on email sending."""

    def __init__(
        self,
        max_emails_per_day: int = 20,
        max_emails_per_week: int = 2,
        max_emails_per_contact_per_week: int = 2,
    ):
        """Initialize rate limiter."""
        self.max_per_day = max_emails_per_day
        self.max_per_week = max_emails_per_week
        self.max_per_contact_per_week = max_emails_per_contact_per_week

        # Tracking: {key: [timestamps]}
        self.daily_sends: Dict[str, list] = {}
        self.weekly_sends: Dict[str, list] = {}
        self.contact_weekly_sends: Dict[str, list] = {}

        logger.info(
            f"Rate limiter initialized: {max_emails_per_day}/day, {max_emails_per_week}/week"
        )

    async def check_can_send(self, contact_email: str) -> tuple[bool, str]:
        """Check if email can be sent based on rate limits."""
        now = datetime.utcnow()
        today = now.date().isoformat()
        week_start = (now - timedelta(days=now.weekday())).date().isoformat()

        # Check daily limit
        daily_key = f"day:{today}"
        self.daily_sends.setdefault(daily_key, [])
        if len(self.daily_sends[daily_key]) >= self.max_per_day:
            logger.warning(f"Daily limit reached for {today}")
            return False, f"Daily limit ({self.max_per_day}) reached"

        # Check weekly limit
        weekly_key = f"week:{week_start}"
        self.weekly_sends.setdefault(weekly_key, [])
        if len(self.weekly_sends[weekly_key]) >= self.max_per_week:
            logger.warning(f"Weekly limit reached for {week_start}")
            return False, f"Weekly limit ({self.max_per_week}) reached"

        # Check per-contact weekly limit
        contact_key = f"contact:{contact_email}:week:{week_start}"
        self.contact_weekly_sends.setdefault(contact_key, [])
        if len(self.contact_weekly_sends[contact_key]) >= self.max_emails_per_contact_per_week:
            logger.warning(f"Contact limit reached for {contact_email}")
            return (
                False,
                f"Contact weekly limit ({self.max_emails_per_contact_per_week}) reached",
            )

        return True, "OK"

    async def record_send(self, contact_email: str) -> None:
        """Record email send for rate limit tracking."""
        now = datetime.utcnow()
        today = now.date().isoformat()
        week_start = (now - timedelta(days=now.weekday())).date().isoformat()

        daily_key = f"day:{today}"
        weekly_key = f"week:{week_start}"
        contact_key = f"contact:{contact_email}:week:{week_start}"

        self.daily_sends.setdefault(daily_key, []).append(now)
        self.weekly_sends.setdefault(weekly_key, []).append(now)
        self.contact_weekly_sends.setdefault(contact_key, []).append(now)

        logger.info(
            f"Send recorded: {contact_email}, daily={len(self.daily_sends[daily_key])}, "
            f"weekly={len(self.weekly_sends[weekly_key])}, contact_weekly={len(self.contact_weekly_sends[contact_key])}"
        )

    async def get_remaining_quota(self, contact_email: str) -> Dict[str, int]:
        """Get remaining quota for contact."""
        now = datetime.utcnow()
        today = now.date().isoformat()
        week_start = (now - timedelta(days=now.weekday())).date().isoformat()

        daily_key = f"day:{today}"
        weekly_key = f"week:{week_start}"
        contact_key = f"contact:{contact_email}:week:{week_start}"

        return {
            "remaining_today": max(0, self.max_per_day - len(self.daily_sends.get(daily_key, []))),
            "remaining_this_week": max(0, self.max_per_week - len(self.weekly_sends.get(weekly_key, []))),
            "remaining_for_contact": max(
                0,
                self.max_emails_per_contact_per_week
                - len(self.contact_weekly_sends.get(contact_key, [])),
            ),
        }


# Global rate limiter
_rate_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    """Get or create global rate limiter."""
    global _rate_limiter
    if _rate_limiter is None:
        from src.config import get_settings
        settings = get_settings()
        _rate_limiter = RateLimiter(
            max_emails_per_day=settings.max_emails_per_day,
            max_emails_per_week=settings.max_emails_per_week,
        )
    return _rate_limiter
