"""
Commands Routes - AI assistant commands and conversational interface
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from enum import Enum
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/commands", tags=["Commands"])


class CommandType(str, Enum):
    QUERY = "query"  # Get information
    ACTION = "action"  # Perform an action
    NAVIGATION = "navigation"  # Navigate to a page
    REPORT = "report"  # Generate a report
    HELP = "help"  # Get help
    SEARCH = "search"  # Search entities
    CREATE = "create"  # Create entity
    UPDATE = "update"  # Update entity
    SUMMARIZE = "summarize"  # Summarize data
    SCHEDULE = "schedule"  # Schedule an action


class CommandStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REQUIRES_CONFIRMATION = "requires_confirmation"


class CommandRequest(BaseModel):
    input: str  # Natural language input
    context: Optional[Dict[str, Any]] = None  # Current context (page, selected entity, etc.)
    conversation_id: Optional[str] = None  # For multi-turn conversations
    voice_input: bool = False


class CommandConfirmation(BaseModel):
    command_id: str
    confirmed: bool
    modifications: Optional[Dict[str, Any]] = None


class QuickActionCreate(BaseModel):
    name: str
    description: Optional[str] = None
    command: str
    icon: Optional[str] = None
    shortcut: Optional[str] = None
    category: Optional[str] = None


class ConversationContext(BaseModel):
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    current_page: Optional[str] = None
    selected_items: Optional[List[str]] = None


# In-memory storage
command_history = {}
conversations = {}
quick_actions = {}
command_patterns = {}


@router.post("/execute")
async def execute_command(
    request: CommandRequest,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Execute a natural language command"""
    import uuid
    
    command_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    # Parse and classify the command
    parsed = _parse_command(request.input, request.context)
    
    # Get or create conversation
    if request.conversation_id:
        conversation = conversations.get(request.conversation_id, {"messages": []})
    else:
        conversation_id = str(uuid.uuid4())
        conversation = {
            "id": conversation_id,
            "messages": [],
            "context": request.context or {},
            "created_at": now.isoformat()
        }
        conversations[conversation_id] = conversation
        request.conversation_id = conversation_id
    
    # Add user message to conversation
    conversation["messages"].append({
        "role": "user",
        "content": request.input,
        "timestamp": now.isoformat()
    })
    
    # Execute command based on type
    result = await _execute_parsed_command(parsed, request.context, user_id, tenant_id)
    
    # Add assistant response
    conversation["messages"].append({
        "role": "assistant",
        "content": result.get("response", ""),
        "timestamp": datetime.utcnow().isoformat()
    })
    
    command_record = {
        "id": command_id,
        "input": request.input,
        "parsed": parsed,
        "result": result,
        "conversation_id": request.conversation_id,
        "status": result.get("status", CommandStatus.COMPLETED.value),
        "user_id": user_id,
        "tenant_id": tenant_id,
        "created_at": now.isoformat(),
        "completed_at": datetime.utcnow().isoformat()
    }
    
    command_history[command_id] = command_record
    
    logger.info("command_executed", command_id=command_id, type=parsed.get("type"))
    
    return {
        "command_id": command_id,
        "conversation_id": request.conversation_id,
        **result
    }


def _parse_command(input_text: str, context: Optional[Dict] = None) -> Dict[str, Any]:
    """Parse natural language input into structured command"""
    input_lower = input_text.lower()
    
    # Detect command type based on keywords
    if any(word in input_lower for word in ["show", "list", "get", "find", "what", "how many"]):
        command_type = CommandType.QUERY
    elif any(word in input_lower for word in ["create", "add", "new"]):
        command_type = CommandType.CREATE
    elif any(word in input_lower for word in ["update", "change", "modify", "edit", "set"]):
        command_type = CommandType.UPDATE
    elif any(word in input_lower for word in ["schedule", "remind", "when"]):
        command_type = CommandType.SCHEDULE
    elif any(word in input_lower for word in ["report", "analysis", "analytics"]):
        command_type = CommandType.REPORT
    elif any(word in input_lower for word in ["search", "look for"]):
        command_type = CommandType.SEARCH
    elif any(word in input_lower for word in ["summarize", "summary", "overview"]):
        command_type = CommandType.SUMMARIZE
    elif any(word in input_lower for word in ["help", "how do i", "what can"]):
        command_type = CommandType.HELP
    elif any(word in input_lower for word in ["go to", "open", "navigate"]):
        command_type = CommandType.NAVIGATION
    else:
        command_type = CommandType.ACTION
    
    # Extract entities
    entities = []
    entity_keywords = {
        "deal": ["deal", "deals", "opportunity", "opportunities"],
        "contact": ["contact", "contacts", "person", "people"],
        "account": ["account", "accounts", "company", "companies"],
        "lead": ["lead", "leads"],
        "task": ["task", "tasks"],
        "meeting": ["meeting", "meetings"],
        "email": ["email", "emails"]
    }
    
    for entity_type, keywords in entity_keywords.items():
        if any(kw in input_lower for kw in keywords):
            entities.append(entity_type)
    
    return {
        "type": command_type.value,
        "original_input": input_text,
        "entities": entities,
        "intent": _extract_intent(input_lower),
        "parameters": _extract_parameters(input_lower),
        "confidence": 0.85
    }


def _extract_intent(text: str) -> str:
    """Extract user intent from text"""
    if "today" in text or "this week" in text:
        return "time_filtered_query"
    if "top" in text or "best" in text:
        return "ranking_query"
    if "email" in text and "send" in text:
        return "send_email"
    if "call" in text:
        return "make_call"
    if "meeting" in text and ("schedule" in text or "book" in text):
        return "schedule_meeting"
    return "general"


def _extract_parameters(text: str) -> Dict[str, Any]:
    """Extract parameters from text"""
    params = {}
    
    # Time parameters
    if "today" in text:
        params["time_range"] = "today"
    elif "this week" in text:
        params["time_range"] = "this_week"
    elif "this month" in text:
        params["time_range"] = "this_month"
    elif "last week" in text:
        params["time_range"] = "last_week"
    
    # Quantity
    if "top " in text:
        import re
        match = re.search(r"top (\d+)", text)
        if match:
            params["limit"] = int(match.group(1))
    
    return params


async def _execute_parsed_command(
    parsed: Dict[str, Any],
    context: Optional[Dict] = None,
    user_id: str = "default",
    tenant_id: str = "default"
) -> Dict[str, Any]:
    """Execute the parsed command"""
    
    command_type = parsed.get("type")
    entities = parsed.get("entities", [])
    parameters = parsed.get("parameters", {})
    
    if command_type == CommandType.HELP.value:
        return {
            "status": CommandStatus.COMPLETED.value,
            "response": "I can help you with:\n• View and search deals, contacts, accounts\n• Schedule meetings and tasks\n• Generate reports and analytics\n• Send emails and make calls\n• Navigate the CRM\n\nTry: 'Show my top deals' or 'Schedule a meeting with John'",
            "suggestions": [
                "Show my pipeline",
                "List today's tasks",
                "Create a new deal",
                "Send follow-up email"
            ]
        }
    
    elif command_type == CommandType.QUERY.value:
        if "deal" in entities:
            return {
                "status": CommandStatus.COMPLETED.value,
                "response": "Here are your top deals:\n\n1. **Acme Corp** - $150,000 (Negotiation)\n2. **TechStart Inc** - $85,000 (Proposal)\n3. **Global Services** - $200,000 (Discovery)",
                "data": {
                    "type": "deals",
                    "items": [
                        {"name": "Acme Corp", "value": 150000, "stage": "Negotiation"},
                        {"name": "TechStart Inc", "value": 85000, "stage": "Proposal"},
                        {"name": "Global Services", "value": 200000, "stage": "Discovery"}
                    ]
                },
                "actions": [
                    {"label": "View all deals", "action": "navigate", "target": "/deals"},
                    {"label": "Create deal", "action": "create", "entity": "deal"}
                ]
            }
        elif "task" in entities:
            return {
                "status": CommandStatus.COMPLETED.value,
                "response": "You have 5 tasks due today:\n\n1. Follow up with Acme Corp (Overdue)\n2. Send proposal to TechStart\n3. Review contract draft\n4. Call John Smith\n5. Update pipeline report",
                "data": {"type": "tasks", "count": 5},
                "actions": [
                    {"label": "View all tasks", "action": "navigate", "target": "/tasks"}
                ]
            }
        else:
            return {
                "status": CommandStatus.COMPLETED.value,
                "response": "Here's an overview of your CRM:\n\n• **Pipeline**: $2.5M across 45 deals\n• **Tasks**: 5 due today\n• **Meetings**: 3 scheduled\n• **New leads**: 12 this week",
                "data": {"type": "overview"}
            }
    
    elif command_type == CommandType.CREATE.value:
        if "deal" in entities:
            return {
                "status": CommandStatus.REQUIRES_CONFIRMATION.value,
                "response": "I'll help you create a new deal. Please provide the following:\n\n• Deal name\n• Account\n• Value\n• Expected close date",
                "form": {
                    "entity": "deal",
                    "fields": ["name", "account", "value", "close_date"]
                }
            }
        elif "task" in entities:
            return {
                "status": CommandStatus.REQUIRES_CONFIRMATION.value,
                "response": "Creating a new task. What should the task be about?",
                "form": {
                    "entity": "task",
                    "fields": ["title", "due_date", "priority"]
                }
            }
    
    elif command_type == CommandType.SCHEDULE.value:
        return {
            "status": CommandStatus.REQUIRES_CONFIRMATION.value,
            "response": "I'll help you schedule a meeting. Here are available times:\n\n• Tomorrow at 10:00 AM\n• Tomorrow at 2:00 PM\n• Friday at 11:00 AM",
            "data": {
                "type": "availability",
                "slots": ["Tomorrow 10:00 AM", "Tomorrow 2:00 PM", "Friday 11:00 AM"]
            },
            "confirmation_required": True
        }
    
    elif command_type == CommandType.REPORT.value:
        return {
            "status": CommandStatus.COMPLETED.value,
            "response": "📊 **Sales Report - This Month**\n\n• Revenue: $450,000\n• Deals Won: 12\n• Win Rate: 35%\n• Avg Deal Size: $37,500\n• Pipeline: $2.1M",
            "data": {
                "type": "report",
                "metrics": {
                    "revenue": 450000,
                    "deals_won": 12,
                    "win_rate": 35,
                    "avg_deal_size": 37500,
                    "pipeline": 2100000
                }
            },
            "actions": [
                {"label": "View full report", "action": "navigate", "target": "/reports/sales"},
                {"label": "Export to PDF", "action": "export", "format": "pdf"}
            ]
        }
    
    elif command_type == CommandType.SUMMARIZE.value:
        return {
            "status": CommandStatus.COMPLETED.value,
            "response": "📋 **Summary**\n\nYour sales pipeline is healthy with $2.5M in total value. Focus areas:\n\n1. **3 deals** in negotiation need follow-up\n2. **Acme Corp** is ready to close\n3. **5 overdue tasks** require attention\n\nRecommendation: Prioritize the Acme Corp deal and clear overdue tasks.",
            "insights": [
                "Pipeline is 15% higher than last month",
                "Win rate trending up",
                "Average sales cycle decreased by 5 days"
            ]
        }
    
    elif command_type == CommandType.NAVIGATION.value:
        target_pages = {
            "deal": "/deals",
            "contact": "/contacts",
            "account": "/accounts",
            "task": "/tasks",
            "report": "/reports",
            "dashboard": "/dashboard"
        }
        
        for entity in entities:
            if entity in target_pages:
                return {
                    "status": CommandStatus.COMPLETED.value,
                    "response": f"Navigating to {entity}s...",
                    "action": {
                        "type": "navigate",
                        "target": target_pages[entity]
                    }
                }
        
        return {
            "status": CommandStatus.COMPLETED.value,
            "response": "Opening dashboard...",
            "action": {"type": "navigate", "target": "/dashboard"}
        }
    
    else:
        return {
            "status": CommandStatus.COMPLETED.value,
            "response": f"I understood your request about {', '.join(entities) if entities else 'general sales'}. How can I help you specifically?",
            "suggestions": [
                "Show my pipeline",
                "Create a new deal",
                "Schedule a meeting"
            ]
        }


@router.post("/confirm")
async def confirm_command(
    request: CommandConfirmation,
    tenant_id: str = Query(default="default")
):
    """Confirm a pending command"""
    if request.command_id not in command_history:
        raise HTTPException(status_code=404, detail="Command not found")
    
    command = command_history[request.command_id]
    
    if command.get("status") != CommandStatus.REQUIRES_CONFIRMATION.value:
        raise HTTPException(status_code=400, detail="Command does not require confirmation")
    
    if request.confirmed:
        # Execute the confirmed action
        command["status"] = CommandStatus.COMPLETED.value
        command["confirmed_at"] = datetime.utcnow().isoformat()
        command["modifications"] = request.modifications
        
        logger.info("command_confirmed", command_id=request.command_id)
        return {
            "status": "confirmed",
            "response": "Action completed successfully!",
            "command_id": request.command_id
        }
    else:
        command["status"] = "cancelled"
        command["cancelled_at"] = datetime.utcnow().isoformat()
        
        return {
            "status": "cancelled",
            "message": "Action cancelled",
            "command_id": request.command_id
        }


@router.get("/history")
async def get_command_history(
    limit: int = Query(default=50, le=100),
    offset: int = 0,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Get command history"""
    history = [
        c for c in command_history.values()
        if c.get("user_id") == user_id and c.get("tenant_id") == tenant_id
    ]
    
    history.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return {
        "commands": history[offset:offset + limit],
        "total": len(history),
        "limit": limit,
        "offset": offset
    }


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get conversation history"""
    if conversation_id not in conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return conversations[conversation_id]


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation"""
    if conversation_id not in conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    del conversations[conversation_id]
    return {"status": "deleted", "conversation_id": conversation_id}


@router.post("/quick-actions")
async def create_quick_action(
    request: QuickActionCreate,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Create a quick action shortcut"""
    import uuid
    
    action_id = str(uuid.uuid4())
    
    action = {
        "id": action_id,
        "name": request.name,
        "description": request.description,
        "command": request.command,
        "icon": request.icon,
        "shortcut": request.shortcut,
        "category": request.category,
        "user_id": user_id,
        "tenant_id": tenant_id,
        "created_at": datetime.utcnow().isoformat()
    }
    
    quick_actions[action_id] = action
    logger.info("quick_action_created", action_id=action_id, name=request.name)
    return action


@router.get("/quick-actions")
async def list_quick_actions(
    category: Optional[str] = None,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """List quick actions"""
    actions = [
        a for a in quick_actions.values()
        if a.get("user_id") == user_id and a.get("tenant_id") == tenant_id
    ]
    
    if category:
        actions = [a for a in actions if a.get("category") == category]
    
    # Add default quick actions
    defaults = [
        {"id": "default-1", "name": "Show Pipeline", "command": "show my pipeline", "icon": "📊", "category": "sales"},
        {"id": "default-2", "name": "Today's Tasks", "command": "show today's tasks", "icon": "✅", "category": "productivity"},
        {"id": "default-3", "name": "New Deal", "command": "create a new deal", "icon": "💰", "category": "sales"},
        {"id": "default-4", "name": "Schedule Meeting", "command": "schedule a meeting", "icon": "📅", "category": "productivity"}
    ]
    
    return {
        "quick_actions": actions,
        "defaults": defaults
    }


@router.delete("/quick-actions/{action_id}")
async def delete_quick_action(action_id: str):
    """Delete a quick action"""
    if action_id not in quick_actions:
        raise HTTPException(status_code=404, detail="Quick action not found")
    
    del quick_actions[action_id]
    return {"status": "deleted", "action_id": action_id}


@router.get("/suggestions")
async def get_command_suggestions(
    context: Optional[str] = None,
    partial_input: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Get command suggestions based on context"""
    
    suggestions = []
    
    if partial_input:
        # Autocomplete suggestions
        all_commands = [
            "show my pipeline",
            "show today's tasks",
            "show top deals",
            "create a new deal",
            "create a task",
            "schedule a meeting",
            "send follow-up email",
            "generate sales report",
            "summarize this week",
            "find contacts at Acme"
        ]
        
        suggestions = [c for c in all_commands if partial_input.lower() in c.lower()][:5]
    
    elif context:
        # Context-based suggestions
        context_suggestions = {
            "deal": [
                "Update deal stage",
                "Add note to deal",
                "Schedule follow-up",
                "Generate proposal"
            ],
            "contact": [
                "Send email",
                "Schedule call",
                "Add to sequence",
                "View activity history"
            ],
            "dashboard": [
                "Show my pipeline",
                "List overdue tasks",
                "Summarize this week",
                "Generate report"
            ]
        }
        
        suggestions = context_suggestions.get(context, context_suggestions["dashboard"])
    
    else:
        suggestions = [
            "Show my pipeline",
            "What are my tasks for today?",
            "Create a new deal",
            "Send follow-up emails"
        ]
    
    return {"suggestions": suggestions}
