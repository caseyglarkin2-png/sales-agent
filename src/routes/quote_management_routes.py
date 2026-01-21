"""
Quote Management Routes - Quote generation, approval workflows, and CPQ
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

router = APIRouter(prefix="/quotes-v2", tags=["Quote Management V2"])


class QuoteStatus(str, Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SENT = "sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class QuoteType(str, Enum):
    NEW_BUSINESS = "new_business"
    RENEWAL = "renewal"
    EXPANSION = "expansion"
    UPSELL = "upsell"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"


class DiscountType(str, Enum):
    PERCENTAGE = "percentage"
    FIXED_AMOUNT = "fixed_amount"
    VOLUME = "volume"
    PROMOTIONAL = "promotional"


class PricingModel(str, Enum):
    FLAT_RATE = "flat_rate"
    PER_USER = "per_user"
    USAGE_BASED = "usage_based"
    TIERED = "tiered"
    HYBRID = "hybrid"


# In-memory storage
quotes = {}
quote_templates = {}
pricing_rules = {}
approval_workflows = {}


class LineItemCreate(BaseModel):
    product_id: str
    product_name: str
    quantity: int = 1
    unit_price: float
    discount_pct: float = 0
    discount_reason: Optional[str] = None


class QuoteCreate(BaseModel):
    deal_id: str
    deal_name: str
    account_id: str
    account_name: str
    quote_type: QuoteType
    line_items: List[LineItemCreate]
    valid_until: Optional[datetime] = None
    payment_terms: str = "Net 30"
    notes: Optional[str] = None


class PricingRuleCreate(BaseModel):
    name: str
    product_id: str
    pricing_model: PricingModel
    base_price: float
    tiers: Optional[List[Dict[str, Any]]] = None
    conditions: Optional[Dict[str, Any]] = None


class ApprovalRequest(BaseModel):
    quote_id: str
    approver_id: str
    decision: ApprovalStatus
    comments: Optional[str] = None


# Quote CRUD
@router.post("/")
async def create_quote(
    request: QuoteCreate,
    tenant_id: str = Query(default="default")
):
    """Create a new quote"""
    quote_id = str(uuid.uuid4())
    quote_number = f"Q-{datetime.utcnow().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
    now = datetime.utcnow()
    
    # Calculate totals
    line_items = []
    subtotal = 0
    total_discount = 0
    
    for item in request.line_items:
        item_subtotal = item.quantity * item.unit_price
        discount_amount = item_subtotal * (item.discount_pct / 100)
        item_total = item_subtotal - discount_amount
        
        line_items.append({
            "id": str(uuid.uuid4()),
            "product_id": item.product_id,
            "product_name": item.product_name,
            "quantity": item.quantity,
            "unit_price": item.unit_price,
            "subtotal": item_subtotal,
            "discount_pct": item.discount_pct,
            "discount_amount": discount_amount,
            "discount_reason": item.discount_reason,
            "total": item_total
        })
        subtotal += item_subtotal
        total_discount += discount_amount
    
    # Determine if approval needed
    max_discount = max([item.discount_pct for item in request.line_items], default=0)
    needs_approval = max_discount > 15 or total_discount > 10000
    
    quote = {
        "id": quote_id,
        "quote_number": quote_number,
        "deal_id": request.deal_id,
        "deal_name": request.deal_name,
        "account_id": request.account_id,
        "account_name": request.account_name,
        "quote_type": request.quote_type.value,
        "status": QuoteStatus.PENDING_APPROVAL.value if needs_approval else QuoteStatus.DRAFT.value,
        "line_items": line_items,
        "subtotal": subtotal,
        "total_discount": total_discount,
        "total": subtotal - total_discount,
        "valid_until": (request.valid_until or (now + timedelta(days=30))).isoformat(),
        "payment_terms": request.payment_terms,
        "notes": request.notes,
        "needs_approval": needs_approval,
        "approval_history": [],
        "version": 1,
        "tenant_id": tenant_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    quotes[quote_id] = quote
    
    return quote


@router.get("/{quote_id}")
async def get_quote(
    quote_id: str,
    tenant_id: str = Query(default="default")
):
    """Get a quote by ID"""
    quote = quotes.get(quote_id)
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    return quote


@router.get("/")
async def list_quotes(
    deal_id: Optional[str] = None,
    account_id: Optional[str] = None,
    status: Optional[QuoteStatus] = None,
    quote_type: Optional[QuoteType] = None,
    limit: int = Query(default=50, le=100),
    tenant_id: str = Query(default="default")
):
    """List quotes"""
    result = [q for q in quotes.values() if q.get("tenant_id") == tenant_id]
    
    if deal_id:
        result = [q for q in result if q.get("deal_id") == deal_id]
    if account_id:
        result = [q for q in result if q.get("account_id") == account_id]
    if status:
        result = [q for q in result if q.get("status") == status.value]
    if quote_type:
        result = [q for q in result if q.get("quote_type") == quote_type.value]
    
    return {"quotes": result[:limit], "total": len(result)}


@router.put("/{quote_id}")
async def update_quote(
    quote_id: str,
    updates: Dict[str, Any],
    tenant_id: str = Query(default="default")
):
    """Update a quote"""
    quote = quotes.get(quote_id)
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    quote.update(updates)
    quote["updated_at"] = datetime.utcnow().isoformat()
    quote["version"] = quote.get("version", 1) + 1
    
    return quote


# Quote Actions
@router.post("/{quote_id}/send")
async def send_quote(
    quote_id: str,
    recipient_emails: List[str],
    message: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Send quote to customer"""
    quote = quotes.get(quote_id)
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    if quote.get("status") not in [QuoteStatus.DRAFT.value, QuoteStatus.APPROVED.value]:
        raise HTTPException(status_code=400, detail="Quote must be draft or approved to send")
    
    quote["status"] = QuoteStatus.SENT.value
    quote["sent_at"] = datetime.utcnow().isoformat()
    quote["sent_to"] = recipient_emails
    
    return {
        "quote_id": quote_id,
        "status": "sent",
        "sent_to": recipient_emails,
        "sent_at": quote["sent_at"]
    }


@router.post("/{quote_id}/clone")
async def clone_quote(
    quote_id: str,
    tenant_id: str = Query(default="default")
):
    """Clone an existing quote"""
    original = quotes.get(quote_id)
    if not original:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    new_id = str(uuid.uuid4())
    new_number = f"Q-{datetime.utcnow().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
    now = datetime.utcnow()
    
    new_quote = original.copy()
    new_quote["id"] = new_id
    new_quote["quote_number"] = new_number
    new_quote["status"] = QuoteStatus.DRAFT.value
    new_quote["version"] = 1
    new_quote["cloned_from"] = quote_id
    new_quote["created_at"] = now.isoformat()
    new_quote["updated_at"] = now.isoformat()
    new_quote["valid_until"] = (now + timedelta(days=30)).isoformat()
    new_quote["approval_history"] = []
    
    quotes[new_id] = new_quote
    
    return new_quote


# Approval Workflow
@router.post("/{quote_id}/submit-for-approval")
async def submit_for_approval(
    quote_id: str,
    tenant_id: str = Query(default="default")
):
    """Submit quote for approval"""
    quote = quotes.get(quote_id)
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    quote["status"] = QuoteStatus.PENDING_APPROVAL.value
    quote["submitted_for_approval_at"] = datetime.utcnow().isoformat()
    
    # Determine approvers based on discount level
    total_discount_pct = (quote["total_discount"] / quote["subtotal"]) * 100 if quote["subtotal"] > 0 else 0
    
    if total_discount_pct > 30:
        required_approvers = ["vp_sales", "cfo"]
    elif total_discount_pct > 20:
        required_approvers = ["vp_sales"]
    else:
        required_approvers = ["sales_manager"]
    
    quote["required_approvers"] = required_approvers
    quote["pending_approvers"] = required_approvers.copy()
    
    return {
        "quote_id": quote_id,
        "status": "pending_approval",
        "required_approvers": required_approvers
    }


@router.post("/approve")
async def process_approval(
    request: ApprovalRequest,
    tenant_id: str = Query(default="default")
):
    """Process an approval decision"""
    quote = quotes.get(request.quote_id)
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    now = datetime.utcnow()
    
    approval_record = {
        "approver_id": request.approver_id,
        "decision": request.decision.value,
        "comments": request.comments,
        "decided_at": now.isoformat()
    }
    
    quote["approval_history"].append(approval_record)
    
    if request.decision == ApprovalStatus.APPROVED:
        pending = quote.get("pending_approvers", [])
        if request.approver_id in pending:
            pending.remove(request.approver_id)
        
        if not pending:
            quote["status"] = QuoteStatus.APPROVED.value
            quote["approved_at"] = now.isoformat()
    elif request.decision == ApprovalStatus.REJECTED:
        quote["status"] = QuoteStatus.DRAFT.value
        quote["rejection_reason"] = request.comments
    
    return {
        "quote_id": request.quote_id,
        "status": quote["status"],
        "decision": request.decision.value
    }


@router.get("/pending-approvals")
async def get_pending_approvals(
    approver_id: str,
    tenant_id: str = Query(default="default")
):
    """Get quotes pending approval"""
    pending = [q for q in quotes.values() 
               if q.get("status") == QuoteStatus.PENDING_APPROVAL.value 
               and q.get("tenant_id") == tenant_id]
    
    return {"pending_quotes": pending, "total": len(pending)}


# Pricing & CPQ
@router.post("/pricing/calculate")
async def calculate_pricing(
    product_id: str,
    quantity: int,
    pricing_model: Optional[PricingModel] = None,
    tenant_id: str = Query(default="default")
):
    """Calculate pricing for a product"""
    base_price = random.uniform(50, 500)
    
    if pricing_model == PricingModel.PER_USER:
        unit_price = base_price
        total = unit_price * quantity
        volume_discount = 0.05 if quantity >= 10 else (0.10 if quantity >= 50 else (0.15 if quantity >= 100 else 0))
        final_total = total * (1 - volume_discount)
    elif pricing_model == PricingModel.TIERED:
        tiers = [
            {"min": 1, "max": 10, "price": base_price},
            {"min": 11, "max": 50, "price": base_price * 0.9},
            {"min": 51, "max": 100, "price": base_price * 0.8},
            {"min": 101, "max": None, "price": base_price * 0.7}
        ]
        unit_price = base_price
        for tier in tiers:
            if tier["max"] is None or quantity <= tier["max"]:
                unit_price = tier["price"]
                break
        total = unit_price * quantity
        volume_discount = 0
        final_total = total
    else:
        unit_price = base_price
        total = unit_price * quantity
        volume_discount = 0
        final_total = total
    
    return {
        "product_id": product_id,
        "quantity": quantity,
        "pricing_model": pricing_model.value if pricing_model else "flat_rate",
        "base_price": base_price,
        "unit_price": unit_price,
        "subtotal": total,
        "volume_discount_pct": volume_discount,
        "volume_discount_amount": total * volume_discount,
        "total": final_total
    }


@router.post("/pricing/rules")
async def create_pricing_rule(
    request: PricingRuleCreate,
    tenant_id: str = Query(default="default")
):
    """Create a pricing rule"""
    rule_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    rule = {
        "id": rule_id,
        "name": request.name,
        "product_id": request.product_id,
        "pricing_model": request.pricing_model.value,
        "base_price": request.base_price,
        "tiers": request.tiers,
        "conditions": request.conditions,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    pricing_rules[rule_id] = rule
    
    return rule


# Quote Templates
@router.post("/templates")
async def create_quote_template(
    name: str,
    description: Optional[str] = None,
    default_line_items: List[Dict[str, Any]] = [],
    terms_and_conditions: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Create a quote template"""
    template_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    template = {
        "id": template_id,
        "name": name,
        "description": description,
        "default_line_items": default_line_items,
        "terms_and_conditions": terms_and_conditions,
        "usage_count": 0,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    quote_templates[template_id] = template
    
    return template


@router.get("/templates")
async def list_templates(
    tenant_id: str = Query(default="default")
):
    """List quote templates"""
    result = [t for t in quote_templates.values() if t.get("tenant_id") == tenant_id]
    return {"templates": result, "total": len(result)}


# Analytics
@router.get("/analytics")
async def get_quote_analytics(
    period: str = Query(default="quarter"),
    tenant_id: str = Query(default="default")
):
    """Get quote analytics"""
    return {
        "period": period,
        "generated_at": datetime.utcnow().isoformat(),
        "summary": {
            "quotes_created": random.randint(100, 300),
            "quotes_sent": random.randint(80, 250),
            "quotes_accepted": random.randint(30, 100),
            "quotes_rejected": random.randint(10, 40),
            "quotes_expired": random.randint(20, 60),
            "acceptance_rate": round(random.uniform(0.30, 0.50), 2),
            "avg_quote_value": random.randint(40000, 100000),
            "total_quoted_value": random.randint(3000000, 15000000),
            "total_accepted_value": random.randint(1500000, 8000000)
        },
        "discount_analysis": {
            "avg_discount_pct": round(random.uniform(8, 18), 1),
            "max_discount_given": round(random.uniform(25, 40), 1),
            "quotes_with_discount": round(random.uniform(0.60, 0.85), 2),
            "discount_value_total": random.randint(200000, 800000)
        },
        "approval_metrics": {
            "quotes_requiring_approval": random.randint(30, 80),
            "avg_approval_time_hours": round(random.uniform(4, 24), 1),
            "approval_rate": round(random.uniform(0.85, 0.98), 2),
            "escalations": random.randint(2, 10)
        },
        "velocity": {
            "avg_time_to_send_hours": round(random.uniform(2, 12), 1),
            "avg_time_to_decision_days": round(random.uniform(3, 14), 1),
            "quotes_pending": random.randint(20, 60)
        }
    }


# Export
@router.get("/{quote_id}/export")
async def export_quote(
    quote_id: str,
    format: str = Query(default="pdf"),
    tenant_id: str = Query(default="default")
):
    """Export quote to PDF or other format"""
    quote = quotes.get(quote_id)
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    return {
        "quote_id": quote_id,
        "format": format,
        "export_url": f"https://api.example.com/exports/quotes/{quote_id}.{format}",
        "generated_at": datetime.utcnow().isoformat(),
        "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat()
    }
