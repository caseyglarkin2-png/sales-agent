"""SocialSchedulerAgent - Schedule and track social media posts.

Manages the social media calendar, optimizes posting times,
and tracks engagement metrics.
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from enum import Enum

from src.agents.base import BaseAgent
from src.logger import get_logger

logger = get_logger(__name__)


class Platform(str, Enum):
    """Supported social platforms."""
    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"


class PostStatus(str, Enum):
    """Status of a scheduled post."""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"


class SocialSchedulerAgent(BaseAgent):
    """Schedules social media posts and tracks engagement.
    
    Features:
    - Optimal time scheduling based on audience data
    - Cross-platform scheduling
    - Engagement tracking and reporting
    - Best performer identification
    
    Example:
        agent = SocialSchedulerAgent()
        result = await agent.execute({
            "action": "schedule",
            "platform": "linkedin",
            "content": "Great insights from our latest case study...",
            "preferred_time": "2026-01-25T10:00:00Z",
        })
    """

    # Optimal posting times by platform (UTC)
    OPTIMAL_TIMES = {
        Platform.LINKEDIN: [
            {"day": "tuesday", "hour": 10},
            {"day": "wednesday", "hour": 10},
            {"day": "thursday", "hour": 10},
        ],
        Platform.TWITTER: [
            {"day": "monday", "hour": 14},
            {"day": "wednesday", "hour": 12},
            {"day": "friday", "hour": 9},
        ],
    }

    def __init__(self, buffer_connector=None, linkedin_connector=None):
        """Initialize with optional social connectors."""
        super().__init__(
            name="Social Scheduler Agent",
            description="Schedules posts and tracks social media engagement"
        )
        self.buffer_connector = buffer_connector
        self.linkedin_connector = linkedin_connector
        
        # In-memory schedule (would be DB in production)
        self._schedule: List[Dict[str, Any]] = []

    async def validate_input(self, context: Dict[str, Any]) -> bool:
        """Validate input."""
        action = context.get("action", "schedule")
        if action == "schedule":
            return "content" in context and "platform" in context
        return True

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute social scheduling action."""
        action = context.get("action", "schedule")
        
        if action == "schedule":
            return await self._schedule_post(context)
        elif action == "list":
            return await self._list_scheduled(context)
        elif action == "optimize":
            return await self._optimize_schedule(context)
        elif action == "analytics":
            return await self._get_analytics(context)
        else:
            return {"status": "error", "error": f"Unknown action: {action}"}

    async def _schedule_post(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Schedule a post for publishing."""
        content = context["content"]
        platform = context["platform"]
        preferred_time = context.get("preferred_time")
        
        # Determine optimal time if not specified
        if preferred_time:
            schedule_time = datetime.fromisoformat(preferred_time.replace("Z", "+00:00"))
        else:
            schedule_time = self._get_next_optimal_time(platform)
        
        post = {
            "id": f"post-{datetime.utcnow().timestamp()}",
            "platform": platform,
            "content": content,
            "scheduled_time": schedule_time.isoformat(),
            "status": PostStatus.SCHEDULED.value,
            "created_at": datetime.utcnow().isoformat(),
        }
        
        self._schedule.append(post)
        
        # If we have a real connector, schedule there too
        if platform == "linkedin" and self.linkedin_connector:
            # TODO: Implement real LinkedIn scheduling
            pass
        
        logger.info(f"Scheduled {platform} post for {schedule_time}")
        
        return {
            "status": "success",
            "post": post,
            "message": f"Post scheduled for {schedule_time.strftime('%B %d at %I:%M %p')}",
        }

    async def _list_scheduled(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """List scheduled posts."""
        platform = context.get("platform")
        status = context.get("status")
        
        posts = self._schedule
        
        if platform:
            posts = [p for p in posts if p["platform"] == platform]
        if status:
            posts = [p for p in posts if p["status"] == status]
        
        return {
            "status": "success",
            "count": len(posts),
            "posts": sorted(posts, key=lambda x: x["scheduled_time"]),
        }

    async def _optimize_schedule(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest optimal posting times based on engagement data."""
        platform = context.get("platform", "linkedin")
        
        optimal_times = self.OPTIMAL_TIMES.get(Platform(platform), [])
        
        suggestions = []
        now = datetime.utcnow()
        
        for opt in optimal_times:
            # Find next occurrence of this day/hour
            days_ahead = self._days_until_weekday(opt["day"])
            next_time = now.replace(
                hour=opt["hour"], 
                minute=0, 
                second=0, 
                microsecond=0
            ) + timedelta(days=days_ahead)
            
            if next_time <= now:
                next_time += timedelta(days=7)
            
            suggestions.append({
                "time": next_time.isoformat(),
                "display": next_time.strftime("%A, %B %d at %I:%M %p"),
                "reason": f"High engagement on {opt['day'].title()}s at {opt['hour']}:00",
            })
        
        return {
            "status": "success",
            "platform": platform,
            "suggestions": suggestions[:5],
        }

    async def _get_analytics(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get engagement analytics for posts."""
        # Mock analytics - would pull from real platform APIs
        return {
            "status": "success",
            "period": "last_30_days",
            "metrics": {
                "total_posts": 12,
                "total_impressions": 45000,
                "total_engagements": 2340,
                "avg_engagement_rate": 5.2,
                "top_performers": [
                    {
                        "post_id": "post-001",
                        "content_preview": "Just helped a client save 40%...",
                        "engagements": 450,
                        "impressions": 8500,
                    },
                ],
            },
        }

    def _get_next_optimal_time(self, platform: str) -> datetime:
        """Get the next optimal posting time for a platform."""
        try:
            platform_enum = Platform(platform)
        except ValueError:
            platform_enum = Platform.LINKEDIN
        
        optimal_times = self.OPTIMAL_TIMES.get(platform_enum, [])
        if not optimal_times:
            # Default to tomorrow at 10am
            return datetime.utcnow().replace(hour=10, minute=0) + timedelta(days=1)
        
        # Find next available slot
        now = datetime.utcnow()
        opt = optimal_times[0]
        days_ahead = self._days_until_weekday(opt["day"])
        
        return now.replace(
            hour=opt["hour"],
            minute=0,
            second=0,
            microsecond=0
        ) + timedelta(days=days_ahead if days_ahead > 0 else 7)

    @staticmethod
    def _days_until_weekday(weekday_name: str) -> int:
        """Calculate days until next occurrence of a weekday."""
        weekdays = {
            "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
            "friday": 4, "saturday": 5, "sunday": 6
        }
        target = weekdays.get(weekday_name.lower(), 0)
        today = datetime.utcnow().weekday()
        days = target - today
        return days if days > 0 else days + 7
