"""
AI Assistant Routes - Conversational AI sales assistant
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from enum import Enum
import structlog
import uuid
import random

logger = structlog.get_logger()

router = APIRouter(prefix="/ai-assistant", tags=["AI Assistant"])


class AssistantType(str, Enum):
    SALES_COACH = "sales_coach"
    DEAL_ADVISOR = "deal_advisor"
    EMAIL_COMPOSER = "email_composer"
    MEETING_PREP = "meeting_prep"
    OBJECTION_HANDLER = "objection_handler"
    COMPETITOR_ANALYST = "competitor_analyst"
    DATA_ANALYST = "data_analyst"
    GENERAL = "general"


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class FeedbackType(str, Enum):
    HELPFUL = "helpful"
    NOT_HELPFUL = "not_helpful"
    INCORRECT = "incorrect"
    INCOMPLETE = "incomplete"


class SuggestionType(str, Enum):
    EMAIL = "email"
    TALKING_POINT = "talking_point"
    QUESTION = "question"
    ACTION = "action"
    INSIGHT = "insight"
    WARNING = "warning"


# In-memory storage
conversations = {}
messages = {}
suggestions = {}
prompts = {}
feedback = {}
assistant_settings = {}
usage_analytics = {}


class ConversationStart(BaseModel):
    assistant_type: AssistantType
    context: Optional[Dict[str, Any]] = None
    initial_message: Optional[str] = None


class MessageRequest(BaseModel):
    content: str
    attachments: Optional[List[Dict[str, Any]]] = None


class PromptTemplate(BaseModel):
    name: str
    assistant_type: AssistantType
    prompt: str
    variables: Optional[List[str]] = None
    description: Optional[str] = None


# Conversations
@router.post("/conversations")
async def start_conversation(
    request: ConversationStart,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Start a new AI assistant conversation"""
    conversation_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    conversation = {
        "id": conversation_id,
        "assistant_type": request.assistant_type.value,
        "context": request.context or {},
        "user_id": user_id,
        "tenant_id": tenant_id,
        "message_count": 0,
        "started_at": now.isoformat(),
        "last_message_at": now.isoformat()
    }
    
    conversations[conversation_id] = conversation
    
    # Generate initial assistant message
    if request.initial_message:
        # Process user's initial message
        await send_message(conversation_id, MessageRequest(content=request.initial_message))
    else:
        # Generate greeting based on assistant type
        greeting = generate_greeting(request.assistant_type, request.context)
        message_id = str(uuid.uuid4())
        
        messages[message_id] = {
            "id": message_id,
            "conversation_id": conversation_id,
            "role": MessageRole.ASSISTANT.value,
            "content": greeting,
            "created_at": now.isoformat()
        }
        conversation["message_count"] = 1
    
    logger.info("conversation_started", conversation_id=conversation_id, type=request.assistant_type.value)
    return conversation


@router.get("/conversations")
async def list_conversations(
    assistant_type: Optional[AssistantType] = None,
    limit: int = Query(default=20, le=50),
    offset: int = 0,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """List conversations"""
    result = [
        c for c in conversations.values() 
        if c.get("tenant_id") == tenant_id and c.get("user_id") == user_id
    ]
    
    if assistant_type:
        result = [c for c in result if c.get("assistant_type") == assistant_type.value]
    
    result.sort(key=lambda x: x.get("last_message_at", ""), reverse=True)
    
    return {
        "conversations": result[offset:offset + limit],
        "total": len(result),
        "limit": limit,
        "offset": offset
    }


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get conversation with messages"""
    if conversation_id not in conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    conversation = conversations[conversation_id]
    conv_messages = [
        m for m in messages.values() if m.get("conversation_id") == conversation_id
    ]
    conv_messages.sort(key=lambda x: x.get("created_at", ""))
    
    return {
        **conversation,
        "messages": conv_messages
    }


@router.post("/conversations/{conversation_id}/messages")
async def send_message(conversation_id: str, request: MessageRequest):
    """Send a message in a conversation"""
    if conversation_id not in conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    conversation = conversations[conversation_id]
    now = datetime.utcnow()
    
    # Store user message
    user_message_id = str(uuid.uuid4())
    messages[user_message_id] = {
        "id": user_message_id,
        "conversation_id": conversation_id,
        "role": MessageRole.USER.value,
        "content": request.content,
        "attachments": request.attachments,
        "created_at": now.isoformat()
    }
    
    # Generate AI response
    response = generate_ai_response(
        request.content,
        AssistantType(conversation["assistant_type"]),
        conversation.get("context", {})
    )
    
    assistant_message_id = str(uuid.uuid4())
    messages[assistant_message_id] = {
        "id": assistant_message_id,
        "conversation_id": conversation_id,
        "role": MessageRole.ASSISTANT.value,
        "content": response["content"],
        "suggestions": response.get("suggestions", []),
        "sources": response.get("sources", []),
        "created_at": datetime.utcnow().isoformat()
    }
    
    conversation["message_count"] += 2
    conversation["last_message_at"] = now.isoformat()
    
    return {
        "user_message": messages[user_message_id],
        "assistant_message": messages[assistant_message_id]
    }


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation"""
    if conversation_id not in conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    conversations.pop(conversation_id)
    
    # Delete associated messages
    to_delete = [mid for mid, m in messages.items() if m.get("conversation_id") == conversation_id]
    for mid in to_delete:
        messages.pop(mid)
    
    return {"message": "Conversation deleted", "conversation_id": conversation_id}


# Quick Suggestions
@router.post("/suggestions")
async def get_suggestions(
    context_type: str,
    context_id: str,
    suggestion_types: Optional[List[SuggestionType]] = None,
    limit: int = Query(default=5, le=10)
):
    """Get AI suggestions for a given context"""
    suggestion_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    generated_suggestions = generate_contextual_suggestions(
        context_type, 
        context_id, 
        suggestion_types or list(SuggestionType),
        limit
    )
    
    suggestion = {
        "id": suggestion_id,
        "context_type": context_type,
        "context_id": context_id,
        "suggestions": generated_suggestions,
        "generated_at": now.isoformat()
    }
    
    suggestions[suggestion_id] = suggestion
    
    return suggestion


@router.get("/suggestions/deal/{deal_id}")
async def get_deal_suggestions(deal_id: str):
    """Get AI suggestions for a deal"""
    return {
        "deal_id": deal_id,
        "suggestions": [
            {
                "type": "insight",
                "title": "Deal Velocity Concern",
                "content": "This deal has been in the current stage for 15 days, which is 50% longer than your average.",
                "priority": "high",
                "action": "Schedule a follow-up call to identify blockers"
            },
            {
                "type": "talking_point",
                "title": "ROI Discussion",
                "content": "Based on similar deals, emphasizing 3-month ROI timeframe increases close rates by 23%.",
                "priority": "medium"
            },
            {
                "type": "action",
                "title": "Add Champion",
                "content": "Deals with identified champions are 2.5x more likely to close. Consider identifying an internal advocate.",
                "priority": "medium"
            },
            {
                "type": "warning",
                "title": "Competitor Activity",
                "content": "Intel suggests the prospect is also evaluating Competitor X. Review competitive positioning.",
                "priority": "high"
            }
        ]
    }


@router.get("/suggestions/email/{email_id}")
async def get_email_suggestions(email_id: str):
    """Get AI suggestions for email response"""
    return {
        "email_id": email_id,
        "suggestions": [
            {
                "type": "email",
                "title": "Suggested Response",
                "content": "Thank you for your interest! I'd be happy to schedule a demo to show you how our solution can help with [specific pain point mentioned]. Would Tuesday or Wednesday work for a 30-minute call?",
                "tone": "professional",
                "category": "positive_engagement"
            },
            {
                "type": "question",
                "title": "Discovery Question",
                "content": "What is your current process for handling [relevant area]?",
                "purpose": "qualify"
            }
        ]
    }


# Email Composition
@router.post("/compose/email")
async def compose_email(
    recipient_id: str,
    email_type: str,
    context: Optional[Dict[str, Any]] = None,
    tone: str = Query(default="professional"),
    length: str = Query(default="medium")
):
    """AI-powered email composition"""
    templates = {
        "introduction": {
            "subject": "Introduction - [Your Company] can help with [Pain Point]",
            "body": """Hi {first_name},

I noticed that {company_name} is focused on {initiative}. At [Your Company], we've helped similar organizations achieve {outcome}.

I'd love to share how we might be able to support your goals. Would you be open to a brief 15-minute conversation next week?

Best regards,
{sender_name}"""
        },
        "follow_up": {
            "subject": "Following up on our conversation",
            "body": """Hi {first_name},

I wanted to follow up on our conversation from {meeting_date}. As we discussed, I believe we can help {company_name} with {pain_point}.

I've attached some additional resources that address the points you raised. Would you like to schedule a follow-up call to discuss next steps?

Looking forward to hearing from you.

Best,
{sender_name}"""
        },
        "proposal": {
            "subject": "Proposal for {company_name}",
            "body": """Hi {first_name},

Thank you for the opportunity to present our proposal. Based on our discussions, I've prepared a customized solution that addresses your key priorities:

1. {priority_1}
2. {priority_2}
3. {priority_3}

Please find the detailed proposal attached. I'm available to walk through it at your convenience.

Best regards,
{sender_name}"""
        }
    }
    
    template = templates.get(email_type, templates["introduction"])
    
    return {
        "email_type": email_type,
        "subject": template["subject"],
        "body": template["body"],
        "tone": tone,
        "length": length,
        "personalization_suggestions": [
            "Add specific industry reference",
            "Include mutual connection",
            "Reference recent company news"
        ],
        "improvement_tips": [
            "Keep subject line under 50 characters",
            "Include clear call-to-action",
            "Personalize the opening line"
        ]
    }


# Meeting Prep
@router.get("/meeting-prep/{meeting_id}")
async def get_meeting_prep(meeting_id: str):
    """Get AI-generated meeting preparation"""
    return {
        "meeting_id": meeting_id,
        "preparation": {
            "attendees": [
                {
                    "name": "John Smith",
                    "title": "VP of Sales",
                    "linkedin_insights": ["Recently promoted", "Shared article on sales automation"],
                    "communication_style": "Direct, data-driven"
                }
            ],
            "company_insights": {
                "recent_news": ["Announced Q3 earnings beat expectations", "Expanding into EMEA market"],
                "challenges": ["Scaling sales team", "Improving forecast accuracy"],
                "competitors_mentioned": ["Salesforce", "HubSpot"]
            },
            "suggested_agenda": [
                "Recap previous discussion (5 min)",
                "Demo key features (15 min)",
                "ROI discussion (10 min)",
                "Q&A and next steps (10 min)"
            ],
            "talking_points": [
                "Reference their EMEA expansion and how your solution scales globally",
                "Prepare ROI calculation based on their team size",
                "Have competitor comparison ready"
            ],
            "questions_to_ask": [
                "What does success look like for this initiative?",
                "Who else is involved in the decision-making process?",
                "What's your timeline for implementation?"
            ],
            "potential_objections": [
                {
                    "objection": "Already using Salesforce",
                    "response": "We integrate seamlessly with Salesforce and can enhance your existing investment..."
                },
                {
                    "objection": "Budget constraints",
                    "response": "Let me share how customers typically see 3x ROI within the first quarter..."
                }
            ]
        }
    }


# Objection Handling
@router.post("/objection-handler")
async def handle_objection(
    objection: str,
    deal_context: Optional[Dict[str, Any]] = None
):
    """Get AI suggestions for handling objections"""
    common_objections = {
        "price": [
            "Focus on value delivered rather than cost. Help them calculate ROI.",
            "Ask: 'What's the cost of NOT solving this problem?'",
            "Offer flexible payment terms or phased implementation."
        ],
        "competitor": [
            "Acknowledge the competitor's strengths, then differentiate.",
            "Ask what specific features they're comparing.",
            "Offer a side-by-side evaluation or proof of concept."
        ],
        "timing": [
            "Understand the urgency drivers and create compelling events.",
            "Ask: 'What needs to happen for this to become a priority?'",
            "Offer a low-commitment next step to maintain momentum."
        ],
        "stakeholder": [
            "Offer to help prepare materials for the additional stakeholder.",
            "Ask to meet the stakeholder to address their concerns directly.",
            "Create a business case document they can share internally."
        ]
    }
    
    # Classify objection
    objection_lower = objection.lower()
    objection_type = "general"
    for key in common_objections:
        if key in objection_lower:
            objection_type = key
            break
    
    return {
        "objection": objection,
        "objection_type": objection_type,
        "responses": common_objections.get(objection_type, [
            "Acknowledge the concern and ask clarifying questions.",
            "Provide relevant case study or social proof.",
            "Focus on their specific pain points and how you solve them."
        ]),
        "follow_up_questions": [
            "Can you tell me more about your concern?",
            "What would address this for you?",
            "How have you handled similar decisions in the past?"
        ],
        "resources": [
            {"type": "case_study", "title": "How Company X overcame similar concerns"},
            {"type": "roi_calculator", "title": "ROI Calculator"}
        ]
    }


# Prompt Templates
@router.post("/prompts")
async def create_prompt_template(
    request: PromptTemplate,
    tenant_id: str = Query(default="default")
):
    """Create a custom prompt template"""
    prompt_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    prompt = {
        "id": prompt_id,
        "name": request.name,
        "assistant_type": request.assistant_type.value,
        "prompt": request.prompt,
        "variables": request.variables or [],
        "description": request.description,
        "usage_count": 0,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    prompts[prompt_id] = prompt
    
    return prompt


@router.get("/prompts")
async def list_prompt_templates(
    assistant_type: Optional[AssistantType] = None,
    tenant_id: str = Query(default="default")
):
    """List prompt templates"""
    result = [p for p in prompts.values() if p.get("tenant_id") == tenant_id]
    
    if assistant_type:
        result = [p for p in result if p.get("assistant_type") == assistant_type.value]
    
    return {"prompts": result, "total": len(result)}


# Feedback
@router.post("/feedback")
async def submit_feedback(
    message_id: str,
    feedback_type: FeedbackType,
    comment: Optional[str] = None,
    user_id: str = Query(default="default")
):
    """Submit feedback on AI response"""
    feedback_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    fb = {
        "id": feedback_id,
        "message_id": message_id,
        "feedback_type": feedback_type.value,
        "comment": comment,
        "user_id": user_id,
        "submitted_at": now.isoformat()
    }
    
    feedback[feedback_id] = fb
    
    return fb


# Analytics
@router.get("/analytics")
async def get_assistant_analytics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Get AI assistant usage analytics"""
    tenant_conversations = [c for c in conversations.values() if c.get("tenant_id") == tenant_id]
    
    by_type = {}
    for assistant_type in AssistantType:
        by_type[assistant_type.value] = len([
            c for c in tenant_conversations if c.get("assistant_type") == assistant_type.value
        ])
    
    total_messages = len([m for m in messages.values()])
    
    return {
        "total_conversations": len(tenant_conversations),
        "total_messages": total_messages,
        "by_assistant_type": by_type,
        "avg_messages_per_conversation": round(total_messages / max(len(tenant_conversations), 1), 1),
        "feedback_summary": {
            "helpful": len([f for f in feedback.values() if f.get("feedback_type") == "helpful"]),
            "not_helpful": len([f for f in feedback.values() if f.get("feedback_type") == "not_helpful"]),
            "satisfaction_rate": round(random.uniform(0.85, 0.95), 3)
        },
        "popular_topics": [
            {"topic": "Deal strategy", "count": random.randint(50, 100)},
            {"topic": "Email composition", "count": random.randint(40, 80)},
            {"topic": "Objection handling", "count": random.randint(30, 60)},
            {"topic": "Meeting prep", "count": random.randint(20, 50)}
        ],
        "period": {"start_date": start_date, "end_date": end_date}
    }


# Helper functions
def generate_greeting(assistant_type: AssistantType, context: Optional[Dict]) -> str:
    greetings = {
        AssistantType.SALES_COACH: "Hi! I'm your AI Sales Coach. I'm here to help you improve your sales skills and strategy. What would you like to work on today?",
        AssistantType.DEAL_ADVISOR: "Hello! I'm your Deal Advisor. I can help you strategize on specific deals, identify risks, and suggest next best actions. Tell me about the deal you're working on.",
        AssistantType.EMAIL_COMPOSER: "Hi there! I can help you compose effective sales emails. What type of email would you like to write?",
        AssistantType.MEETING_PREP: "Hello! Let me help you prepare for your upcoming meeting. Which meeting would you like to prepare for?",
        AssistantType.OBJECTION_HANDLER: "Hi! I can help you handle sales objections effectively. What objection are you facing?",
        AssistantType.COMPETITOR_ANALYST: "Hello! I can provide competitive intelligence and positioning strategies. Which competitor would you like to discuss?",
        AssistantType.DATA_ANALYST: "Hi! I can help analyze your sales data and provide insights. What would you like to explore?",
        AssistantType.GENERAL: "Hello! I'm your AI sales assistant. How can I help you today?"
    }
    
    return greetings.get(assistant_type, greetings[AssistantType.GENERAL])


def generate_ai_response(content: str, assistant_type: AssistantType, context: Dict) -> Dict:
    # Simulated AI response generation
    responses = {
        AssistantType.SALES_COACH: f"That's a great question! Based on best practices, here's my advice: When dealing with {content[:50]}..., focus on understanding the customer's underlying needs first. Would you like me to elaborate on specific techniques?",
        AssistantType.DEAL_ADVISOR: f"Looking at this deal, I see a few key points to consider regarding {content[:50]}... Let me suggest some next best actions and potential risks to watch for.",
        AssistantType.EMAIL_COMPOSER: f"I've drafted an email based on your request. Here's a compelling approach that addresses {content[:50]}... Would you like me to adjust the tone or add more details?",
        AssistantType.MEETING_PREP: f"For this meeting, I recommend focusing on the following talking points: 1) Address their key concern about {content[:30]}..., 2) Prepare ROI data, 3) Have customer references ready.",
        AssistantType.OBJECTION_HANDLER: f"I understand the objection about {content[:50]}... Here are three effective approaches you can use to address this concern.",
        AssistantType.GENERAL: f"Thank you for your question about {content[:50]}... Here's what I can share based on best practices and your context."
    }
    
    return {
        "content": responses.get(assistant_type, responses[AssistantType.GENERAL]),
        "suggestions": [
            {"type": "action", "text": "Would you like specific examples?"},
            {"type": "action", "text": "Should I elaborate on any point?"}
        ],
        "sources": []
    }


def generate_contextual_suggestions(
    context_type: str, 
    context_id: str, 
    suggestion_types: List[SuggestionType],
    limit: int
) -> List[Dict]:
    generated = []
    
    for i in range(limit):
        stype = random.choice(suggestion_types)
        generated.append({
            "type": stype.value,
            "title": f"Suggested {stype.value.replace('_', ' ').title()}",
            "content": f"AI-generated {stype.value} based on {context_type} analysis",
            "confidence": round(random.uniform(0.7, 0.95), 2),
            "priority": random.choice(["high", "medium", "low"])
        })
    
    return generated
