"""API routes for reply classification."""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from src.classification import get_reply_classifier, ReplyIntent

router = APIRouter(prefix="/api/classification", tags=["classification"])


class ClassifyReplyRequest(BaseModel):
    body: str
    subject: str = ""
    sender: str = ""
    context: Optional[dict] = None


class BatchClassifyRequest(BaseModel):
    replies: list[dict]


@router.post("/reply")
async def classify_reply(request: ClassifyReplyRequest):
    """Classify a single email reply."""
    classifier = get_reply_classifier()
    
    classification = classifier.classify(
        reply_body=request.body,
        subject=request.subject,
        sender=request.sender,
        context=request.context,
    )
    
    return classification.to_dict()


@router.post("/batch")
async def batch_classify(request: BatchClassifyRequest):
    """Classify multiple replies at once."""
    classifier = get_reply_classifier()
    
    classifications = classifier.batch_classify(request.replies)
    
    return {
        "classifications": [c.to_dict() for c in classifications],
        "summary": {
            "total": len(classifications),
            "by_intent": _count_by_intent(classifications),
            "avg_confidence": sum(c.confidence for c in classifications) / len(classifications) if classifications else 0,
        }
    }


@router.get("/intents")
async def list_intents():
    """List all possible reply intents."""
    return {
        "intents": [
            {
                "intent": intent.value,
                "name": intent.name.replace("_", " ").title(),
                "description": _get_intent_description(intent),
            }
            for intent in ReplyIntent
        ]
    }


def _count_by_intent(classifications) -> dict:
    """Count classifications by intent."""
    counts = {}
    for c in classifications:
        intent = c.intent.value
        counts[intent] = counts.get(intent, 0) + 1
    return counts


def _get_intent_description(intent: ReplyIntent) -> str:
    """Get description for an intent."""
    descriptions = {
        ReplyIntent.INTERESTED: "Prospect is expressing interest, wants more information",
        ReplyIntent.MEETING_REQUEST: "Prospect wants to schedule a meeting or call",
        ReplyIntent.MEETING_CONFIRMED: "Prospect has confirmed a meeting time",
        ReplyIntent.QUESTION: "Prospect has questions that need answering",
        ReplyIntent.OBJECTION: "Prospect has objections (price, timing, competitor, etc.)",
        ReplyIntent.NOT_NOW: "Prospect says it's not the right time, but may be open later",
        ReplyIntent.NOT_INTERESTED: "Prospect clearly not interested",
        ReplyIntent.UNSUBSCRIBE: "Prospect wants to opt out of communications",
        ReplyIntent.OUT_OF_OFFICE: "Auto-reply indicating absence",
        ReplyIntent.BOUNCE: "Email delivery failed",
        ReplyIntent.REFERRAL: "Prospect is referring you to another contact",
        ReplyIntent.POSITIVE_FEEDBACK: "Thanks or appreciation without clear intent",
        ReplyIntent.UNCLEAR: "Intent cannot be determined automatically",
    }
    return descriptions.get(intent, "")
