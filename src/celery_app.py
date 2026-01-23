"""
Celery application configuration and setup.

Provides async task processing for workflow orchestration.
"""
import logging
from celery import Celery
from celery.signals import task_prerun, task_postrun, task_failure

from src.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# Create Celery app
celery_app = Celery(
    "sales_agent",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["src.tasks"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minutes max
    task_soft_time_limit=540,  # 9 minutes soft limit
    worker_prefetch_multiplier=1,  # One task at a time
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks
    task_acks_late=True,  # Acknowledge task after completion
    task_reject_on_worker_lost=True,  # Reject task if worker dies
    result_expires=86400,  # Keep results for 24 hours
)

# Retry policy
celery_app.conf.task_default_retry_delay = 60  # 1 minute
celery_app.conf.task_max_retries = 3

# Celery Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    'refresh-expiring-oauth-tokens': {
        'task': 'src.oauth_manager.refresh_expiring_tokens_task',
        'schedule': 1800.0,  # Every 30 minutes
        'options': {'expires': 300}  # Expire if not run within 5 minutes
    },
}


@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **extra):
    """Log task start."""
    logger.info(
        f"Task started: {task.name}",
        extra={"task_id": task_id, "task_name": task.name}
    )


@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **extra):
    """Log task completion."""
    logger.info(
        f"Task completed: {task.name}",
        extra={"task_id": task_id, "task_name": task.name, "state": state}
    )


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, args=None, kwargs=None, traceback=None, einfo=None, **extra):
    """Log task failure."""
    logger.error(
        f"Task failed: {sender.name}",
        extra={
            "task_id": task_id,
            "task_name": sender.name,
            "exception": str(exception),
            "traceback": str(traceback)
        },
        exc_info=einfo
    )


if __name__ == "__main__":
    # Start worker with: python -m src.celery_app worker --loglevel=info
    celery_app.start()
