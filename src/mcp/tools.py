"""
CaseyOS MCP Tools.

Defines all tools exposed to MCP clients (Claude Desktop, etc.)
These tools allow AI assistants to interact with CaseyOS capabilities.
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def register_caseyos_tools(server):
    """Register all CaseyOS tools with the MCP server."""
    
    # ============================================================
    # TOOL: read_command_queue
    # ============================================================
    server.register_tool(
        name="read_command_queue",
        description="""Read Today's Moves from the CaseyOS command queue.
Returns prioritized list of recommended actions with APS scores and reasoning.
Use this to see what Casey should focus on today.""",
        input_schema={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of items to return (default: 10)",
                    "default": 10
                },
                "status_filter": {
                    "type": "string",
                    "enum": ["pending", "accepted", "dismissed", "executed", "all"],
                    "description": "Filter by item status",
                    "default": "pending"
                }
            },
            "required": []
        },
        handler=handle_read_command_queue
    )
    
    # ============================================================
    # TOOL: execute_action
    # ============================================================
    server.register_tool(
        name="execute_action",
        description="""Execute an action from the command queue.
Supports: send_email, create_draft, create_task, complete_task, book_meeting, update_deal_stage.
Use dry_run=true to preview without executing.""",
        input_schema={
            "type": "object",
            "properties": {
                "queue_item_id": {
                    "type": "string",
                    "description": "ID of the command queue item to execute"
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "If true, preview action without executing",
                    "default": False
                }
            },
            "required": ["queue_item_id"]
        },
        handler=handle_execute_action
    )
    
    # ============================================================
    # TOOL: search_contacts
    # ============================================================
    server.register_tool(
        name="search_contacts",
        description="""Search HubSpot contacts by email, name, or company.
Returns contact details including email, company, lifecycle stage, and recent activity.""",
        input_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (email, name, or company)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results to return",
                    "default": 10
                }
            },
            "required": ["query"]
        },
        handler=handle_search_contacts
    )
    
    # ============================================================
    # TOOL: create_email_draft
    # ============================================================
    server.register_tool(
        name="create_email_draft",
        description="""Create a personalized email draft for a prospect.
Uses CaseyOS voice profile and prospect context to generate email.
Draft is saved to Gmail, not sent automatically.""",
        input_schema={
            "type": "object",
            "properties": {
                "to_email": {
                    "type": "string",
                    "description": "Recipient email address"
                },
                "subject": {
                    "type": "string", 
                    "description": "Email subject line"
                },
                "context": {
                    "type": "string",
                    "description": "Context for personalization (e.g., 'follow up on proposal', 'reconnect after conference')"
                },
                "tone": {
                    "type": "string",
                    "enum": ["professional", "casual", "urgent"],
                    "description": "Email tone",
                    "default": "professional"
                }
            },
            "required": ["to_email", "subject", "context"]
        },
        handler=handle_create_email_draft
    )
    
    # ============================================================
    # TOOL: get_notifications
    # ============================================================
    server.register_tool(
        name="get_notifications",
        description="""Get proactive notifications from CaseyOS.
Returns urgent items, new signals, and recommended actions.
Use this for Casey's morning briefing or real-time updates.""",
        input_schema={
            "type": "object",
            "properties": {
                "priority": {
                    "type": "string",
                    "enum": ["all", "urgent", "high", "medium"],
                    "description": "Minimum priority level to include",
                    "default": "all"
                },
                "since_hours": {
                    "type": "integer",
                    "description": "Get notifications from last N hours",
                    "default": 24
                }
            },
            "required": []
        },
        handler=handle_get_notifications
    )
    
    # ============================================================
    # TOOL: record_outcome
    # ============================================================
    server.register_tool(
        name="record_outcome",
        description="""Record an outcome for a command queue action.
Used to close the loop and improve APS scoring.
Outcomes: replied, meeting_booked, deal_advanced, task_completed, no_response, unsubscribed.""",
        input_schema={
            "type": "object",
            "properties": {
                "queue_item_id": {
                    "type": "string",
                    "description": "ID of the command queue item"
                },
                "outcome_type": {
                    "type": "string",
                    "enum": ["replied", "meeting_booked", "deal_advanced", "task_completed", "no_response", "unsubscribed"],
                    "description": "Type of outcome"
                },
                "notes": {
                    "type": "string",
                    "description": "Optional notes about the outcome"
                }
            },
            "required": ["queue_item_id", "outcome_type"]
        },
        handler=handle_record_outcome
    )
    
    # ============================================================
    # TOOL: get_deal_pipeline
    # ============================================================
    server.register_tool(
        name="get_deal_pipeline",
        description="""Get current deal pipeline status from HubSpot.
Shows active deals by stage with values and close dates.
Use for pipeline reviews and forecasting.""",
        input_schema={
            "type": "object",
            "properties": {
                "stage_filter": {
                    "type": "string",
                    "description": "Filter by deal stage (e.g., 'proposal', 'negotiation')"
                },
                "min_value": {
                    "type": "number",
                    "description": "Minimum deal value to include"
                },
                "days_to_close": {
                    "type": "integer",
                    "description": "Only show deals closing within N days"
                }
            },
            "required": []
        },
        handler=handle_get_deal_pipeline
    )
    
    # ============================================================
    # TOOL: schedule_followup
    # ============================================================
    server.register_tool(
        name="schedule_followup",
        description="""Schedule a follow-up action for a contact.
Creates a command queue item for future execution.
Great for setting reminders after meetings or proposals.""",
        input_schema={
            "type": "object",
            "properties": {
                "contact_email": {
                    "type": "string",
                    "description": "Contact email address"
                },
                "action_type": {
                    "type": "string",
                    "enum": ["send_email", "create_task", "book_meeting"],
                    "description": "Type of follow-up action"
                },
                "delay_days": {
                    "type": "integer",
                    "description": "Days from now to schedule follow-up",
                    "default": 3
                },
                "context": {
                    "type": "string",
                    "description": "Context for the follow-up"
                }
            },
            "required": ["contact_email", "action_type"]
        },
        handler=handle_schedule_followup
    )
    
    logger.info(f"Registered {len(server._tools)} MCP tools")


# ================================================================
# TOOL HANDLERS
# ================================================================

async def handle_read_command_queue(
    limit: int = 10,
    status_filter: str = "pending"
) -> Dict[str, Any]:
    """Fetch command queue items."""
    from src.db import get_session
    from src.models.command_queue import CommandQueueItem
    from sqlalchemy import select
    
    async with get_session() as session:
        query = select(CommandQueueItem).order_by(
            CommandQueueItem.priority_score.desc()
        ).limit(limit)
        
        if status_filter != "all":
            query = query.where(CommandQueueItem.status == status_filter)
        
        result = await session.execute(query)
        items = result.scalars().all()
        
        return {
            "count": len(items),
            "items": [
                {
                    "id": str(item.id),
                    "action_type": item.action_type,
                    "priority_score": item.priority_score,
                    "status": item.status,
                    "context": item.action_context,
                    "reasoning": item.reasoning if hasattr(item, 'reasoning') else None,
                    "due_by": item.due_by.isoformat() if item.due_by else None,
                    "created_at": item.created_at.isoformat() if item.created_at else None
                }
                for item in items
            ]
        }


async def handle_execute_action(
    queue_item_id: str,
    dry_run: bool = False
) -> Dict[str, Any]:
    """Execute a command queue action."""
    from src.actions.executor import get_executor
    from src.db import get_session
    from src.models.command_queue import CommandQueueItem
    from sqlalchemy import select
    
    async with get_session() as session:
        result = await session.execute(
            select(CommandQueueItem).where(CommandQueueItem.id == queue_item_id)
        )
        item = result.scalar_one_or_none()
        
        if not item:
            return {"error": f"Queue item not found: {queue_item_id}"}
        
        executor = get_executor()
        exec_result = await executor.execute(
            action_type=item.action_type,
            context=item.action_context or {},
            queue_item_id=queue_item_id,
            dry_run=dry_run
        )
        
        return {
            "queue_item_id": queue_item_id,
            "action_type": item.action_type,
            "dry_run": dry_run,
            "result": exec_result
        }


async def handle_search_contacts(
    query: str,
    limit: int = 10
) -> Dict[str, Any]:
    """Search HubSpot contacts."""
    from src.connectors.hubspot import get_hubspot_connector
    
    try:
        hubspot = get_hubspot_connector()
        
        # Search by email first
        if "@" in query:
            contacts = await hubspot.search_contacts_by_email(query)
        else:
            # Search by name/company
            contacts = await hubspot.search_contacts(query, limit=limit)
        
        return {
            "query": query,
            "count": len(contacts) if contacts else 0,
            "contacts": contacts[:limit] if contacts else []
        }
    except Exception as e:
        logger.exception("Contact search failed")
        return {"error": str(e), "query": query}


async def handle_create_email_draft(
    to_email: str,
    subject: str,
    context: str,
    tone: str = "professional"
) -> Dict[str, Any]:
    """Create an email draft."""
    from src.connectors.gmail import get_gmail_connector
    from src.connectors.llm import get_llm_connector
    
    try:
        # Generate email body using LLM
        llm = get_llm_connector()
        
        prompt = f"""Write a {tone} email with the following details:
- To: {to_email}
- Subject: {subject}
- Context: {context}

Write only the email body. Be concise and action-oriented.
Sign off as Casey Larkin, but don't include a formal signature block."""
        
        body = await llm.generate(prompt)
        
        # Create draft in Gmail
        gmail = get_gmail_connector()
        draft = await gmail.create_draft(
            to=to_email,
            subject=subject,
            body=body
        )
        
        return {
            "status": "draft_created",
            "draft_id": draft.get("id"),
            "to": to_email,
            "subject": subject,
            "body_preview": body[:200] + "..." if len(body) > 200 else body
        }
    except Exception as e:
        logger.exception("Draft creation failed")
        return {"error": str(e)}


async def handle_get_notifications(
    priority: str = "all",
    since_hours: int = 24
) -> Dict[str, Any]:
    """Get proactive notifications."""
    from src.db import get_session
    from src.models.signal import Signal
    from src.models.command_queue import CommandQueueItem
    from sqlalchemy import select, and_
    from datetime import datetime, timedelta
    
    since = datetime.utcnow() - timedelta(hours=since_hours)
    
    notifications = []
    
    async with get_session() as session:
        # Get recent high-priority queue items
        queue_query = select(CommandQueueItem).where(
            and_(
                CommandQueueItem.status == "pending",
                CommandQueueItem.created_at >= since
            )
        ).order_by(CommandQueueItem.priority_score.desc()).limit(10)
        
        result = await session.execute(queue_query)
        queue_items = result.scalars().all()
        
        for item in queue_items:
            priority_level = "urgent" if item.priority_score >= 80 else \
                           "high" if item.priority_score >= 60 else \
                           "medium" if item.priority_score >= 40 else "low"
            
            if priority != "all" and priority_level not in [priority, "urgent"]:
                continue
                
            notifications.append({
                "type": "action_recommended",
                "priority": priority_level,
                "message": f"{item.action_type}: {item.action_context.get('recipient', 'unknown') if item.action_context else 'unknown'}",
                "queue_item_id": str(item.id),
                "score": item.priority_score
            })
        
        # Get recent signals
        signal_query = select(Signal).where(
            Signal.created_at >= since
        ).order_by(Signal.created_at.desc()).limit(5)
        
        result = await session.execute(signal_query)
        signals = result.scalars().all()
        
        for signal in signals:
            notifications.append({
                "type": "new_signal",
                "priority": "medium",
                "source": signal.source,
                "signal_type": signal.signal_type,
                "created_at": signal.created_at.isoformat() if signal.created_at else None
            })
    
    return {
        "count": len(notifications),
        "since_hours": since_hours,
        "notifications": notifications
    }


async def handle_record_outcome(
    queue_item_id: str,
    outcome_type: str,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """Record an outcome for a queue item."""
    from src.db import get_session
    from src.models.outcome import OutcomeRecord
    from src.models.command_queue import CommandQueueItem
    from sqlalchemy import select
    import uuid
    
    async with get_session() as session:
        # Verify queue item exists
        result = await session.execute(
            select(CommandQueueItem).where(CommandQueueItem.id == queue_item_id)
        )
        item = result.scalar_one_or_none()
        
        if not item:
            return {"error": f"Queue item not found: {queue_item_id}"}
        
        # Create outcome record
        outcome = OutcomeRecord(
            id=str(uuid.uuid4()),
            queue_item_id=queue_item_id,
            outcome_type=outcome_type,
            contact_email=item.action_context.get("recipient") if item.action_context else None,
            context={"notes": notes} if notes else {},
            source="mcp"
        )
        
        session.add(outcome)
        
        # Update queue item status
        item.status = "completed"
        item.outcome = {"type": outcome_type, "notes": notes}
        
        await session.commit()
        
        return {
            "status": "recorded",
            "outcome_id": outcome.id,
            "queue_item_id": queue_item_id,
            "outcome_type": outcome_type
        }


async def handle_get_deal_pipeline(
    stage_filter: Optional[str] = None,
    min_value: Optional[float] = None,
    days_to_close: Optional[int] = None
) -> Dict[str, Any]:
    """Get deal pipeline from HubSpot."""
    from src.connectors.hubspot import get_hubspot_connector
    
    try:
        hubspot = get_hubspot_connector()
        deals = await hubspot.get_deals()
        
        # Apply filters
        filtered = []
        for deal in deals or []:
            props = deal.get("properties", {})
            
            if stage_filter and props.get("dealstage") != stage_filter:
                continue
                
            if min_value and float(props.get("amount", 0) or 0) < min_value:
                continue
                
            if days_to_close:
                close_date = props.get("closedate")
                if close_date:
                    from datetime import datetime
                    close = datetime.fromisoformat(close_date.replace("Z", "+00:00"))
                    if (close - datetime.now(close.tzinfo)).days > days_to_close:
                        continue
            
            filtered.append({
                "id": deal.get("id"),
                "name": props.get("dealname"),
                "stage": props.get("dealstage"),
                "amount": props.get("amount"),
                "close_date": props.get("closedate"),
                "owner": props.get("hubspot_owner_id")
            })
        
        # Group by stage
        by_stage = {}
        total_value = 0
        for deal in filtered:
            stage = deal["stage"] or "unknown"
            if stage not in by_stage:
                by_stage[stage] = {"count": 0, "value": 0, "deals": []}
            by_stage[stage]["count"] += 1
            by_stage[stage]["value"] += float(deal["amount"] or 0)
            by_stage[stage]["deals"].append(deal)
            total_value += float(deal["amount"] or 0)
        
        return {
            "total_deals": len(filtered),
            "total_value": total_value,
            "by_stage": by_stage
        }
    except Exception as e:
        logger.exception("Pipeline fetch failed")
        return {"error": str(e)}


async def handle_schedule_followup(
    contact_email: str,
    action_type: str,
    delay_days: int = 3,
    context: Optional[str] = None
) -> Dict[str, Any]:
    """Schedule a follow-up action."""
    from src.db import get_session
    from src.models.command_queue import CommandQueueItem
    from datetime import datetime, timedelta
    import uuid
    
    due_by = datetime.utcnow() + timedelta(days=delay_days)
    
    async with get_session() as session:
        item = CommandQueueItem(
            id=str(uuid.uuid4()),
            priority_score=50.0,  # Medium priority for scheduled items
            action_type=action_type,
            action_context={
                "recipient": contact_email,
                "context": context,
                "scheduled_by": "mcp"
            },
            status="pending",
            owner="casey",
            due_by=due_by,
            reasoning=f"Scheduled follow-up: {context or action_type}"
        )
        
        session.add(item)
        await session.commit()
        
        return {
            "status": "scheduled",
            "queue_item_id": item.id,
            "action_type": action_type,
            "contact": contact_email,
            "due_by": due_by.isoformat(),
            "days_from_now": delay_days
        }
