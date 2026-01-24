"""
Signal polling tasks for CaseyOS.

Celery tasks that poll external services for signals and create recommendations.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional
import logging

from celery import shared_task

from src.celery_app import celery_app
from src.routes.celery_health import update_task_heartbeat

logger = logging.getLogger(__name__)


# Track last poll times (in production, use Redis)
_last_poll_times = {}


def _run_async(coro):
    """Run async coroutine in sync context."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


@celery_app.task(
    name="src.tasks.signal_polling.poll_hubspot_signals",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def poll_hubspot_signals(self):
    """
    Poll HubSpot for new deals and create signals.
    
    Runs every 5 minutes via Celery beat.
    """
    logger.info("Starting HubSpot signal polling")
    update_task_heartbeat("src.tasks.signal_polling.poll_hubspot_signals")
    
    try:
        result = _run_async(_poll_hubspot_signals_async())
        logger.info(f"HubSpot polling complete: {result}")
        return result
    except Exception as e:
        logger.error(f"HubSpot polling failed: {e}", exc_info=True)
        raise


async def _poll_hubspot_signals_async():
    """Async implementation of HubSpot polling."""
    from src.db import get_async_session
    from src.services.signal_service import SignalService
    from src.models.signal import SignalSource
    from src.connectors.hubspot import HubSpotConnector
    from src.config import get_settings
    
    settings = get_settings()
    signals_created = 0
    errors = []
    
    # Get last poll time
    last_poll = _last_poll_times.get("hubspot", datetime.utcnow() - timedelta(hours=1))
    
    try:
        # Initialize HubSpot connector
        connector = HubSpotConnector(api_key=settings.hubspot_api_key)
        
        # Get recent deals (created or modified since last poll)
        deals = await connector.get_recent_deals(since=last_poll)
        
        logger.info(f"Found {len(deals)} recent HubSpot deals")
        
        async with get_async_session() as db:
            signal_service = SignalService(db)
            
            for deal in deals:
                try:
                    # Determine event type
                    event_type = "deal_created"
                    if deal.get("updated_at") and deal.get("created_at"):
                        created = datetime.fromisoformat(deal["created_at"].replace("Z", "+00:00"))
                        updated = datetime.fromisoformat(deal["updated_at"].replace("Z", "+00:00"))
                        if updated > created + timedelta(minutes=5):
                            event_type = "deal_stage_changed"
                    
                    # Create signal
                    signal, item = await signal_service.create_and_process(
                        source=SignalSource.HUBSPOT,
                        event_type=event_type,
                        payload={
                            "deal_id": deal.get("id"),
                            "deal_name": deal.get("properties", {}).get("dealname"),
                            "deal_amount": deal.get("properties", {}).get("amount"),
                            "deal_stage": deal.get("properties", {}).get("dealstage"),
                            "contact_email": deal.get("contact_email"),
                            "contact_name": deal.get("contact_name"),
                            "company_name": deal.get("company_name"),
                        },
                        source_id=str(deal.get("id")),
                    )
                    
                    if signal:
                        signals_created += 1
                        logger.info(f"Created signal for deal {deal.get('id')}")
                        
                except Exception as e:
                    logger.error(f"Error processing deal {deal.get('id')}: {e}")
                    errors.append(str(e))
            
            await db.commit()
        
        # Update last poll time
        _last_poll_times["hubspot"] = datetime.utcnow()
        
    except Exception as e:
        logger.error(f"HubSpot connector error: {e}", exc_info=True)
        errors.append(str(e))
    
    return {
        "signals_created": signals_created,
        "errors": errors,
        "polled_at": datetime.utcnow().isoformat(),
    }


@celery_app.task(
    name="src.tasks.signal_polling.poll_gmail_signals",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def poll_gmail_signals(self):
    """
    Poll Gmail for new replies and create signals.
    
    Runs every 5 minutes via Celery beat.
    """
    logger.info("Starting Gmail signal polling")
    update_task_heartbeat("src.tasks.signal_polling.poll_gmail_signals")
    
    try:
        result = _run_async(_poll_gmail_signals_async())
        logger.info(f"Gmail polling complete: {result}")
        return result
    except Exception as e:
        logger.error(f"Gmail polling failed: {e}", exc_info=True)
        raise


async def _poll_gmail_signals_async():
    """Async implementation of Gmail polling."""
    from src.db import get_async_session
    from src.services.signal_service import SignalService
    from src.models.signal import SignalSource
    from src.connectors.gmail import GmailConnector
    from src.config import get_settings
    
    settings = get_settings()
    signals_created = 0
    errors = []
    
    # Get last poll time
    last_poll = _last_poll_times.get("gmail", datetime.utcnow() - timedelta(hours=1))
    
    try:
        # Initialize Gmail connector (requires OAuth credentials)
        connector = GmailConnector()
        
        if not await connector.is_authenticated():
            logger.warning("Gmail not authenticated, skipping polling")
            return {
                "signals_created": 0,
                "errors": ["Gmail not authenticated"],
                "polled_at": datetime.utcnow().isoformat(),
            }
        
        # Get threads with recent replies
        threads = await connector.get_threads_with_replies(since=last_poll)
        
        logger.info(f"Found {len(threads)} threads with recent replies")
        
        async with get_async_session() as db:
            signal_service = SignalService(db)
            
            for thread in threads:
                try:
                    # Get the most recent reply (not from us)
                    reply = thread.get("latest_reply", {})
                    
                    # Skip if the reply is from us
                    if reply.get("is_from_us", False):
                        continue
                    
                    # Create signal
                    signal, item = await signal_service.create_and_process(
                        source=SignalSource.GMAIL,
                        event_type="reply_received",
                        payload={
                            "thread_id": thread.get("id"),
                            "message_id": reply.get("id"),
                            "subject": thread.get("subject"),
                            "from_email": reply.get("from_email"),
                            "sender_name": reply.get("sender_name"),
                            "snippet": reply.get("snippet"),
                            "received_at": reply.get("date"),
                        },
                        source_id=reply.get("id"),
                    )
                    
                    if signal:
                        signals_created += 1
                        logger.info(f"Created signal for reply {reply.get('id')}")
                        
                except Exception as e:
                    logger.error(f"Error processing thread {thread.get('id')}: {e}")
                    errors.append(str(e))
            
            await db.commit()
        
        # Update last poll time
        _last_poll_times["gmail"] = datetime.utcnow()
        
    except Exception as e:
        logger.error(f"Gmail connector error: {e}", exc_info=True)
        errors.append(str(e))
    
    return {
        "signals_created": signals_created,
        "errors": errors,
        "polled_at": datetime.utcnow().isoformat(),
    }


@celery_app.task(
    name="src.tasks.signal_polling.process_unprocessed_signals",
    bind=True,
)
def process_unprocessed_signals(self, limit: int = 100):
    """
    Process any signals that haven't been processed yet.
    
    This is a catch-up task for signals that may have been
    created but not processed (e.g., due to errors).
    """
    logger.info(f"Processing unprocessed signals (limit={limit})")
    update_task_heartbeat("src.tasks.signal_polling.process_unprocessed_signals")
    
    try:
        result = _run_async(_process_unprocessed_signals_async(limit))
        logger.info(f"Unprocessed signals complete: {result}")
        return result
    except Exception as e:
        logger.error(f"Unprocessed signals task failed: {e}", exc_info=True)
        raise


async def _process_unprocessed_signals_async(limit: int):
    """Async implementation of unprocessed signal processing."""
    from src.db import get_async_session
    from src.services.signal_service import SignalService
    
    processed = 0
    errors = []
    
    async with get_async_session() as db:
        signal_service = SignalService(db)
        
        # Get unprocessed signals
        signals = await signal_service.get_unprocessed_signals(limit=limit)
        
        logger.info(f"Found {len(signals)} unprocessed signals")
        
        for signal in signals:
            try:
                item = await signal_service.process_signal(signal)
                if item:
                    processed += 1
            except Exception as e:
                logger.error(f"Error processing signal {signal.id}: {e}")
                errors.append(f"{signal.id}: {str(e)}")
        
        await db.commit()
    
    return {
        "processed": processed,
        "total": len(signals),
        "errors": errors,
    }
