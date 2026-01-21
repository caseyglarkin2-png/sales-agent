"""
Dashboard Metrics Aggregator.

Aggregates metrics from all components for real-time dashboard display.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class DashboardMetrics:
    """Real-time dashboard metrics."""
    # Email metrics
    drafts_pending_approval: int = 0
    drafts_sent_today: int = 0
    emails_sent_this_week: int = 0
    
    # Pipeline metrics
    contacts_new: int = 0
    contacts_outreached: int = 0
    contacts_replied: int = 0
    contacts_meeting: int = 0
    contacts_proposal: int = 0
    
    # Sequence metrics
    sequences_active: int = 0
    sequence_steps_today: int = 0
    
    # Response metrics
    reply_rate: float = 0.0
    avg_response_time_hours: float = 0.0
    positive_sentiment_rate: float = 0.0
    
    # Activity metrics
    linkedin_pending: int = 0
    meetings_scheduled: int = 0
    tasks_due_today: int = 0
    
    # AI metrics
    ai_generations_today: int = 0
    ai_success_rate: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DashboardAggregator:
    """Aggregates metrics for dashboard display."""
    
    def __init__(self):
        self.metrics = DashboardMetrics()
        self.last_updated: Optional[datetime] = None
        
        # Track daily counters
        self.daily_counters: Dict[str, int] = {}
        self.counter_date: Optional[datetime] = None
    
    def _check_daily_reset(self):
        """Reset daily counters if new day."""
        today = datetime.utcnow().date()
        if self.counter_date != today:
            self.daily_counters = {}
            self.counter_date = today
    
    def increment_counter(self, name: str, amount: int = 1):
        """Increment a daily counter."""
        self._check_daily_reset()
        self.daily_counters[name] = self.daily_counters.get(name, 0) + amount
    
    def get_counter(self, name: str) -> int:
        """Get daily counter value."""
        self._check_daily_reset()
        return self.daily_counters.get(name, 0)
    
    async def refresh_metrics(self) -> DashboardMetrics:
        """Refresh all metrics from components.
        
        Returns:
            Updated dashboard metrics
        """
        try:
            # Email metrics from draft queue
            await self._refresh_email_metrics()
            
            # Pipeline metrics from analytics
            await self._refresh_pipeline_metrics()
            
            # Sequence metrics
            await self._refresh_sequence_metrics()
            
            # Response metrics
            await self._refresh_response_metrics()
            
            # Activity metrics
            await self._refresh_activity_metrics()
            
            self.last_updated = datetime.utcnow()
            logger.info("Dashboard metrics refreshed")
            
        except Exception as e:
            logger.error(f"Error refreshing metrics: {e}")
        
        return self.metrics
    
    async def _refresh_email_metrics(self):
        """Refresh email-related metrics."""
        try:
            from src.queue import get_queue
            queue = get_queue()
            
            pending = queue.get_pending_count() if hasattr(queue, 'get_pending_count') else 0
            self.metrics.drafts_pending_approval = pending
            self.metrics.drafts_sent_today = self.get_counter("drafts_sent")
            self.metrics.emails_sent_this_week = self.get_counter("emails_sent_week")
            
        except Exception as e:
            logger.debug(f"Could not refresh email metrics: {e}")
    
    async def _refresh_pipeline_metrics(self):
        """Refresh pipeline metrics."""
        try:
            from src.analytics import get_analytics_tracker
            tracker = get_analytics_tracker()
            
            summary = tracker.get_summary()
            self.metrics.contacts_outreached = summary.get("total_sent", 0)
            self.metrics.contacts_replied = summary.get("total_replied", 0)
            
        except Exception as e:
            logger.debug(f"Could not refresh pipeline metrics: {e}")
    
    async def _refresh_sequence_metrics(self):
        """Refresh sequence metrics."""
        try:
            from src.sequences import get_sequence_engine
            engine = get_sequence_engine()
            
            # Count active sequences (enrolled but not completed)
            active = sum(
                1 for e in engine.enrollments.values()
                if e.status.value == "active"
            )
            self.metrics.sequences_active = active
            self.metrics.sequence_steps_today = self.get_counter("sequence_steps")
            
        except Exception as e:
            logger.debug(f"Could not refresh sequence metrics: {e}")
    
    async def _refresh_response_metrics(self):
        """Refresh response rate metrics."""
        try:
            from src.analytics import get_analytics_tracker
            tracker = get_analytics_tracker()
            
            summary = tracker.get_summary()
            total_sent = summary.get("total_sent", 0)
            total_replied = summary.get("total_replied", 0)
            
            if total_sent > 0:
                self.metrics.reply_rate = round(total_replied / total_sent * 100, 1)
            
        except Exception as e:
            logger.debug(f"Could not refresh response metrics: {e}")
    
    async def _refresh_activity_metrics(self):
        """Refresh activity metrics."""
        try:
            from src.outreach import get_linkedin_manager
            from src.scheduling import get_meeting_scheduler
            
            # LinkedIn pending
            manager = get_linkedin_manager()
            stats = manager.get_stats()
            self.metrics.linkedin_pending = stats.get("pending_count", 0)
            
            # Meetings
            scheduler = get_meeting_scheduler()
            meetings = scheduler.get_scheduled_meetings()
            self.metrics.meetings_scheduled = len(meetings)
            
        except Exception as e:
            logger.debug(f"Could not refresh activity metrics: {e}")
    
    def record_draft_sent(self):
        """Record that a draft was sent."""
        self.increment_counter("drafts_sent")
        self.increment_counter("emails_sent_week")
    
    def record_sequence_step(self):
        """Record sequence step execution."""
        self.increment_counter("sequence_steps")
    
    def record_ai_generation(self, success: bool = True):
        """Record AI generation attempt."""
        self.increment_counter("ai_generations")
        if success:
            self.increment_counter("ai_successes")
        
        total = self.get_counter("ai_generations")
        successes = self.get_counter("ai_successes")
        self.metrics.ai_generations_today = total
        if total > 0:
            self.metrics.ai_success_rate = round(successes / total * 100, 1)
    
    def get_quick_stats(self) -> Dict[str, Any]:
        """Get quick stats for dashboard header."""
        return {
            "pending_drafts": self.metrics.drafts_pending_approval,
            "sent_today": self.metrics.drafts_sent_today,
            "reply_rate": f"{self.metrics.reply_rate}%",
            "active_sequences": self.metrics.sequences_active,
            "meetings_scheduled": self.metrics.meetings_scheduled,
            "tasks_today": self.metrics.tasks_due_today,
        }
    
    def get_pipeline_summary(self) -> List[Dict[str, Any]]:
        """Get pipeline summary for visualization."""
        return [
            {"stage": "New", "count": self.metrics.contacts_new, "color": "#3b82f6"},
            {"stage": "Outreached", "count": self.metrics.contacts_outreached, "color": "#8b5cf6"},
            {"stage": "Replied", "count": self.metrics.contacts_replied, "color": "#10b981"},
            {"stage": "Meeting", "count": self.metrics.contacts_meeting, "color": "#f59e0b"},
            {"stage": "Proposal", "count": self.metrics.contacts_proposal, "color": "#ef4444"},
        ]


# Singleton
_aggregator: Optional[DashboardAggregator] = None


def get_dashboard_aggregator() -> DashboardAggregator:
    """Get singleton dashboard aggregator."""
    global _aggregator
    if _aggregator is None:
        _aggregator = DashboardAggregator()
    return _aggregator
