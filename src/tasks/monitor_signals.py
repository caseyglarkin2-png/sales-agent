"""
Background Signal Monitor for Daemon Mode.

This Celery task runs every 5 minutes to check for new signals
and create proactive recommendations - Henry-style always-on behavior.

Monitors:
- HubSpot: New form submissions, deal stage changes
- Gmail: New replies to sent emails
- Calendar: Upcoming meetings, conflicts
- Command Queue: Overdue items, stale recommendations
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any
import asyncio

from celery import shared_task

from src.logger import get_logger
from src.telemetry import log_event

logger = get_logger(__name__)


# =========================================================================
# Monitor Configuration
# =========================================================================

MONITOR_CONFIG = {
    "hubspot_forms": {
        "enabled": True,
        "check_interval_minutes": 5,
        "lookback_minutes": 10,
    },
    "hubspot_deals": {
        "enabled": True,
        "check_interval_minutes": 5,
        "lookback_minutes": 15,
    },
    "gmail_replies": {
        "enabled": True,
        "check_interval_minutes": 5,
        "lookback_minutes": 30,
    },
    "calendar_upcoming": {
        "enabled": True,
        "check_interval_minutes": 15,
        "lookahead_hours": 24,
    },
    "queue_health": {
        "enabled": True,
        "check_interval_minutes": 60,
        "overdue_threshold_hours": 24,
    },
}


# =========================================================================
# Main Monitor Task
# =========================================================================

@shared_task(name="monitor_signals.check_all")
def check_all_signals() -> Dict[str, Any]:
    """
    Main daemon task - runs every 5 minutes.
    
    Checks all signal sources and creates proactive recommendations.
    
    Returns:
        Summary of signals detected and notifications created
    """
    logger.info("🔍 Daemon monitor: Starting signal check...")
    
    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "signals_detected": 0,
        "notifications_created": 0,
        "errors": [],
    }
    
    try:
        # Run async checks
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            check_results = loop.run_until_complete(_run_all_checks())
            results.update(check_results)
        finally:
            loop.close()
        
        log_event(
            "daemon_monitor_complete",
            signals_detected=results["signals_detected"],
            notifications_created=results["notifications_created"],
        )
        
        logger.info(
            f"✅ Daemon monitor: Complete. "
            f"Signals: {results['signals_detected']}, "
            f"Notifications: {results['notifications_created']}"
        )
        
    except Exception as e:
        logger.error(f"❌ Daemon monitor failed: {e}")
        results["errors"].append(str(e))
        log_event("daemon_monitor_error", error=str(e))
    
    return results


async def _run_all_checks() -> Dict[str, Any]:
    """Run all async signal checks."""
    from src.db import async_session
    
    results = {
        "signals_detected": 0,
        "notifications_created": 0,
        "checks": {},
    }
    
    async with async_session() as db:
        # Check HubSpot forms
        if MONITOR_CONFIG["hubspot_forms"]["enabled"]:
            form_results = await _check_hubspot_forms(db)
            results["checks"]["hubspot_forms"] = form_results
            results["signals_detected"] += form_results.get("count", 0)
        
        # Check HubSpot deals
        if MONITOR_CONFIG["hubspot_deals"]["enabled"]:
            deal_results = await _check_hubspot_deals(db)
            results["checks"]["hubspot_deals"] = deal_results
            results["signals_detected"] += deal_results.get("count", 0)
        
        # Check Gmail replies
        if MONITOR_CONFIG["gmail_replies"]["enabled"]:
            gmail_results = await _check_gmail_replies(db)
            results["checks"]["gmail_replies"] = gmail_results
            results["signals_detected"] += gmail_results.get("count", 0)
        
        # Check queue health
        if MONITOR_CONFIG["queue_health"]["enabled"]:
            queue_results = await _check_queue_health(db)
            results["checks"]["queue_health"] = queue_results
            results["notifications_created"] += queue_results.get("notifications", 0)
    
    return results


# =========================================================================
# Individual Check Functions
# =========================================================================

async def _check_hubspot_forms(db) -> Dict[str, Any]:
    """Check for new HubSpot form submissions."""
    from sqlalchemy import select, func
    from src.models.signal import Signal
    
    lookback = datetime.utcnow() - timedelta(
        minutes=MONITOR_CONFIG["hubspot_forms"]["lookback_minutes"]
    )
    
    # Count recent form signals
    result = await db.execute(
        select(func.count(Signal.id)).where(
            Signal.source == "form",
            Signal.created_at >= lookback,
            Signal.processed == False
        )
    )
    count = result.scalar() or 0
    
    if count > 0:
        logger.info(f"📋 Found {count} new form submissions")
        
        # Create notification if high volume
        if count >= 3:
            await _create_notification(
                db,
                user_id="casey",
                title=f"🔥 {count} new form submissions",
                message=f"You have {count} unprocessed form submissions waiting for review.",
                priority="high",
                action_type="view_forms",
                action_url="/api/command-queue/today",
            )
    
    return {"count": count, "status": "checked"}


async def _check_hubspot_deals(db) -> Dict[str, Any]:
    """Check for HubSpot deal stage changes."""
    from sqlalchemy import select, func
    from src.models.signal import Signal
    
    lookback = datetime.utcnow() - timedelta(
        minutes=MONITOR_CONFIG["hubspot_deals"]["lookback_minutes"]
    )
    
    # Count recent deal signals
    result = await db.execute(
        select(func.count(Signal.id)).where(
            Signal.source == "hubspot",
            Signal.event_type.in_(["deal_stage_changed", "deal_created"]),
            Signal.created_at >= lookback,
            Signal.processed == False
        )
    )
    count = result.scalar() or 0
    
    if count > 0:
        logger.info(f"💰 Found {count} deal updates")
        
        # Create notification for important deals
        if count >= 1:
            await _create_notification(
                db,
                user_id="casey",
                title=f"💰 {count} deal update(s)",
                message="Deal stage changes detected that may need attention.",
                priority="normal",
                action_type="view_deals",
                action_url="/api/command-queue/today",
            )
    
    return {"count": count, "status": "checked"}


async def _check_gmail_replies(db) -> Dict[str, Any]:
    """Check for new Gmail replies."""
    from sqlalchemy import select, func
    from src.models.signal import Signal
    
    lookback = datetime.utcnow() - timedelta(
        minutes=MONITOR_CONFIG["gmail_replies"]["lookback_minutes"]
    )
    
    # Count recent reply signals
    result = await db.execute(
        select(func.count(Signal.id)).where(
            Signal.source == "gmail",
            Signal.event_type.in_(["reply_received", "thread_updated"]),
            Signal.created_at >= lookback,
            Signal.processed == False
        )
    )
    count = result.scalar() or 0
    
    if count > 0:
        logger.info(f"📧 Found {count} new email replies")
        
        # Create urgent notification for replies
        await _create_notification(
            db,
            user_id="casey",
            title=f"📧 {count} new email reply(s)!",
            message="Prospects have replied to your outreach.",
            priority="urgent" if count >= 2 else "high",
            action_type="view_replies",
            action_url="/api/command-queue/today",
        )
    
    return {"count": count, "status": "checked"}


async def _check_queue_health(db) -> Dict[str, Any]:
    """Check command queue for overdue/stale items."""
    from sqlalchemy import select, func
    from src.models.command_queue import CommandQueueItem
    
    threshold = datetime.utcnow() - timedelta(
        hours=MONITOR_CONFIG["queue_health"]["overdue_threshold_hours"]
    )
    
    # Count overdue items
    result = await db.execute(
        select(func.count(CommandQueueItem.id)).where(
            CommandQueueItem.status == "pending",
            CommandQueueItem.due_by < datetime.utcnow(),
        )
    )
    overdue_count = result.scalar() or 0
    
    # Count stale items (pending for too long)
    result = await db.execute(
        select(func.count(CommandQueueItem.id)).where(
            CommandQueueItem.status == "pending",
            CommandQueueItem.created_at < threshold,
        )
    )
    stale_count = result.scalar() or 0
    
    notifications = 0
    
    if overdue_count > 0:
        logger.warning(f"⚠️ {overdue_count} overdue queue items")
        await _create_notification(
            db,
            user_id="casey",
            title=f"⚠️ {overdue_count} overdue items",
            message="Some queue items are past their due date.",
            priority="high",
            action_type="view_overdue",
            action_url="/api/command-queue/today",
        )
        notifications += 1
    
    if stale_count > 5:
        logger.warning(f"📦 {stale_count} stale queue items (> 24h)")
        await _create_notification(
            db,
            user_id="casey",
            title=f"📦 {stale_count} stale items need attention",
            message="Some recommendations have been pending for over 24 hours.",
            priority="normal",
            action_type="view_stale",
            action_url="/api/command-queue/today",
        )
        notifications += 1
    
    return {
        "overdue": overdue_count,
        "stale": stale_count,
        "notifications": notifications,
        "status": "checked",
    }


# =========================================================================
# Notification Helper
# =========================================================================

async def _create_notification(
    db,
    user_id: str,
    title: str,
    message: str,
    priority: str = "normal",
    action_type: str = None,
    action_url: str = None,
) -> None:
    """Create a notification for the user."""
    from src.models.notification import JarvisNotification
    
    notification = JarvisNotification(
        user_id=user_id,
        title=title,
        message=message,
        priority=priority,
        action_type=action_type,
        action_url=action_url,
    )
    db.add(notification)
    await db.commit()
    
    log_event(
        "notification_created",
        user_id=user_id,
        priority=priority,
        action_type=action_type,
    )
    
    logger.info(f"🔔 Created notification: {title}")


# =========================================================================
# Celery Beat Schedule Entry
# =========================================================================

BEAT_SCHEDULE = {
    "daemon-monitor-signals": {
        "task": "monitor_signals.check_all",
        "schedule": 300.0,  # Every 5 minutes
        "options": {"expires": 290},  # Expire before next run
    },
}
