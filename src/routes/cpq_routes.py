"""
CPQ Routes - Configure, Price, Quote system
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from enum import Enum
import structlog
import uuid

logger = structlog.get_logger()

router = APIRouter(prefix="/cpq", tags=["CPQ - Configure Price Quote"])


class PricingModel(str, Enum):
    FLAT = "flat"
    TIERED = "tiered"
    VOLUME = "volume"
    PER_USER = "per_user"
    PER_UNIT = "per_unit"
    USAGE = "usage"
    SUBSCRIPTION = "subscription"


class DiscountType(str, Enum):
    PERCENTAGE = "percentage"
    FIXED = "fixed"
    OVERRIDE = "override"


class QuoteStatus(str, Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SENT = "sent"
    VIEWED = "viewed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ProductConfig(BaseModel):
    product_id: str
    quantity: int = 1
    configuration: Optional[Dict[str, Any]] = None
    discount_type: Optional[DiscountType] = None
    discount_value: Optional[float] = None


class QuoteCreate(BaseModel):
    opportunity_id: Optional[str] = None
    account_id: str
    contact_id: Optional[str] = None
    name: str
    valid_until: Optional[str] = None
    currency: str = "USD"
    notes: Optional[str] = None
    line_items: List[ProductConfig]


class QuoteUpdate(BaseModel):
    name: Optional[str] = None
    valid_until: Optional[str] = None
    notes: Optional[str] = None
    terms_and_conditions: Optional[str] = None


class PriceBookEntry(BaseModel):
    product_id: str
    price: float
    currency: str = "USD"
    pricing_model: PricingModel
    tiers: Optional[List[Dict[str, float]]] = None
    effective_date: Optional[str] = None
    expiration_date: Optional[str] = None


class DiscountRuleCreate(BaseModel):
    name: str
    discount_type: DiscountType
    value: float
    conditions: Dict[str, Any]
    requires_approval: bool = False
    approval_threshold: Optional[float] = None


# In-memory storage
quotes = {}
quote_line_items = {}
price_books = {}
price_book_entries = {}
discount_rules = {}
product_bundles = {}
approvals = {}
quote_templates = {}


# Price Books
@router.post("/price-books")
async def create_price_book(
    name: str,
    description: Optional[str] = None,
    is_default: bool = False,
    currency: str = "USD",
    tenant_id: str = Query(default="default")
):
    """Create a price book"""
    price_book_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    price_book = {
        "id": price_book_id,
        "name": name,
        "description": description,
        "is_default": is_default,
        "currency": currency,
        "is_active": True,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    price_books[price_book_id] = price_book
    price_book_entries[price_book_id] = []
    
    logger.info("price_book_created", price_book_id=price_book_id, name=name)
    return price_book


@router.get("/price-books")
async def list_price_books(
    is_active: Optional[bool] = None,
    tenant_id: str = Query(default="default")
):
    """List price books"""
    result = [pb for pb in price_books.values() if pb.get("tenant_id") == tenant_id]
    
    if is_active is not None:
        result = [pb for pb in result if pb.get("is_active") == is_active]
    
    return {"price_books": result, "total": len(result)}


@router.get("/price-books/{price_book_id}")
async def get_price_book(price_book_id: str):
    """Get price book details"""
    if price_book_id not in price_books:
        raise HTTPException(status_code=404, detail="Price book not found")
    
    price_book = price_books[price_book_id]
    entries = price_book_entries.get(price_book_id, [])
    
    return {**price_book, "entries": entries}


@router.post("/price-books/{price_book_id}/entries")
async def add_price_book_entry(
    price_book_id: str,
    request: PriceBookEntry
):
    """Add a product to a price book"""
    if price_book_id not in price_books:
        raise HTTPException(status_code=404, detail="Price book not found")
    
    entry_id = str(uuid.uuid4())
    
    entry = {
        "id": entry_id,
        "price_book_id": price_book_id,
        "product_id": request.product_id,
        "price": request.price,
        "currency": request.currency,
        "pricing_model": request.pricing_model.value,
        "tiers": request.tiers,
        "effective_date": request.effective_date,
        "expiration_date": request.expiration_date,
        "created_at": datetime.utcnow().isoformat()
    }
    
    if price_book_id not in price_book_entries:
        price_book_entries[price_book_id] = []
    price_book_entries[price_book_id].append(entry)
    
    return entry


# Quotes
@router.post("/quotes")
async def create_quote(
    request: QuoteCreate,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Create a new quote"""
    quote_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    # Calculate line items and totals
    line_items = []
    subtotal = 0
    total_discount = 0
    
    for i, item in enumerate(request.line_items):
        # Get base price (mock)
        base_price = 1000.0  # In production, look up from price book
        
        line_total = base_price * item.quantity
        discount_amount = 0
        
        if item.discount_type and item.discount_value:
            if item.discount_type == DiscountType.PERCENTAGE:
                discount_amount = line_total * (item.discount_value / 100)
            elif item.discount_type == DiscountType.FIXED:
                discount_amount = item.discount_value
            elif item.discount_type == DiscountType.OVERRIDE:
                discount_amount = line_total - item.discount_value
        
        net_total = line_total - discount_amount
        
        line_item = {
            "id": str(uuid.uuid4()),
            "quote_id": quote_id,
            "line_number": i + 1,
            "product_id": item.product_id,
            "quantity": item.quantity,
            "unit_price": base_price,
            "list_price": line_total,
            "discount_type": item.discount_type.value if item.discount_type else None,
            "discount_value": item.discount_value,
            "discount_amount": discount_amount,
            "net_price": net_total,
            "configuration": item.configuration or {}
        }
        line_items.append(line_item)
        subtotal += line_total
        total_discount += discount_amount
    
    # Check if approval needed
    discount_percent = (total_discount / subtotal * 100) if subtotal > 0 else 0
    requires_approval = discount_percent > 20  # Example: >20% discount needs approval
    
    quote = {
        "id": quote_id,
        "quote_number": f"Q-{now.strftime('%Y%m%d')}-{quote_id[:6].upper()}",
        "opportunity_id": request.opportunity_id,
        "account_id": request.account_id,
        "contact_id": request.contact_id,
        "name": request.name,
        "status": QuoteStatus.PENDING_APPROVAL.value if requires_approval else QuoteStatus.DRAFT.value,
        "currency": request.currency,
        "subtotal": subtotal,
        "total_discount": total_discount,
        "discount_percent": round(discount_percent, 2),
        "tax_amount": 0,
        "total": subtotal - total_discount,
        "valid_until": request.valid_until or (now + timedelta(days=30)).strftime("%Y-%m-%d"),
        "notes": request.notes,
        "terms_and_conditions": None,
        "requires_approval": requires_approval,
        "created_by": user_id,
        "tenant_id": tenant_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    quotes[quote_id] = quote
    quote_line_items[quote_id] = line_items
    
    # Create approval if needed
    if requires_approval:
        approval_id = str(uuid.uuid4())
        approvals[approval_id] = {
            "id": approval_id,
            "quote_id": quote_id,
            "status": ApprovalStatus.PENDING.value,
            "reason": f"Discount of {discount_percent:.1f}% exceeds 20% threshold",
            "requested_by": user_id,
            "created_at": now.isoformat()
        }
        quote["approval_id"] = approval_id
    
    logger.info("quote_created", quote_id=quote_id, total=quote["total"], requires_approval=requires_approval)
    return {**quote, "line_items": line_items}


@router.get("/quotes")
async def list_quotes(
    status: Optional[QuoteStatus] = None,
    account_id: Optional[str] = None,
    opportunity_id: Optional[str] = None,
    created_by: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    offset: int = 0,
    tenant_id: str = Query(default="default")
):
    """List quotes"""
    result = [q for q in quotes.values() if q.get("tenant_id") == tenant_id]
    
    if status:
        result = [q for q in result if q.get("status") == status.value]
    if account_id:
        result = [q for q in result if q.get("account_id") == account_id]
    if opportunity_id:
        result = [q for q in result if q.get("opportunity_id") == opportunity_id]
    if created_by:
        result = [q for q in result if q.get("created_by") == created_by]
    
    result.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return {
        "quotes": result[offset:offset + limit],
        "total": len(result),
        "limit": limit,
        "offset": offset
    }


@router.get("/quotes/{quote_id}")
async def get_quote(quote_id: str):
    """Get quote details"""
    if quote_id not in quotes:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    quote = quotes[quote_id]
    line_items = quote_line_items.get(quote_id, [])
    
    return {**quote, "line_items": line_items}


@router.put("/quotes/{quote_id}")
async def update_quote(quote_id: str, request: QuoteUpdate):
    """Update quote details"""
    if quote_id not in quotes:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    quote = quotes[quote_id]
    
    if quote["status"] not in [QuoteStatus.DRAFT.value, QuoteStatus.APPROVED.value]:
        raise HTTPException(status_code=400, detail="Quote cannot be modified in current status")
    
    if request.name is not None:
        quote["name"] = request.name
    if request.valid_until is not None:
        quote["valid_until"] = request.valid_until
    if request.notes is not None:
        quote["notes"] = request.notes
    if request.terms_and_conditions is not None:
        quote["terms_and_conditions"] = request.terms_and_conditions
    
    quote["updated_at"] = datetime.utcnow().isoformat()
    
    return quote


@router.post("/quotes/{quote_id}/line-items")
async def add_line_item(
    quote_id: str,
    request: ProductConfig
):
    """Add a line item to a quote"""
    if quote_id not in quotes:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    quote = quotes[quote_id]
    items = quote_line_items.get(quote_id, [])
    
    # Get base price (mock)
    base_price = 1000.0
    line_total = base_price * request.quantity
    discount_amount = 0
    
    if request.discount_type and request.discount_value:
        if request.discount_type == DiscountType.PERCENTAGE:
            discount_amount = line_total * (request.discount_value / 100)
        elif request.discount_type == DiscountType.FIXED:
            discount_amount = request.discount_value
    
    net_total = line_total - discount_amount
    
    line_item = {
        "id": str(uuid.uuid4()),
        "quote_id": quote_id,
        "line_number": len(items) + 1,
        "product_id": request.product_id,
        "quantity": request.quantity,
        "unit_price": base_price,
        "list_price": line_total,
        "discount_type": request.discount_type.value if request.discount_type else None,
        "discount_value": request.discount_value,
        "discount_amount": discount_amount,
        "net_price": net_total,
        "configuration": request.configuration or {}
    }
    
    items.append(line_item)
    quote_line_items[quote_id] = items
    
    # Recalculate totals
    quote["subtotal"] = sum(i["list_price"] for i in items)
    quote["total_discount"] = sum(i["discount_amount"] for i in items)
    quote["total"] = quote["subtotal"] - quote["total_discount"]
    quote["updated_at"] = datetime.utcnow().isoformat()
    
    return line_item


@router.delete("/quotes/{quote_id}/line-items/{item_id}")
async def remove_line_item(quote_id: str, item_id: str):
    """Remove a line item from a quote"""
    if quote_id not in quotes:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    items = quote_line_items.get(quote_id, [])
    quote_line_items[quote_id] = [i for i in items if i["id"] != item_id]
    
    # Recalculate totals
    quote = quotes[quote_id]
    remaining_items = quote_line_items[quote_id]
    quote["subtotal"] = sum(i["list_price"] for i in remaining_items)
    quote["total_discount"] = sum(i["discount_amount"] for i in remaining_items)
    quote["total"] = quote["subtotal"] - quote["total_discount"]
    quote["updated_at"] = datetime.utcnow().isoformat()
    
    return {"status": "removed", "item_id": item_id}


# Quote Actions
@router.post("/quotes/{quote_id}/submit-for-approval")
async def submit_for_approval(quote_id: str, user_id: str = Query(default="default")):
    """Submit quote for approval"""
    if quote_id not in quotes:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    quote = quotes[quote_id]
    
    if quote["status"] != QuoteStatus.DRAFT.value:
        raise HTTPException(status_code=400, detail="Quote is not in draft status")
    
    approval_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    approvals[approval_id] = {
        "id": approval_id,
        "quote_id": quote_id,
        "status": ApprovalStatus.PENDING.value,
        "reason": "Manual approval requested",
        "requested_by": user_id,
        "created_at": now.isoformat()
    }
    
    quote["status"] = QuoteStatus.PENDING_APPROVAL.value
    quote["approval_id"] = approval_id
    quote["updated_at"] = now.isoformat()
    
    return quote


@router.post("/quotes/{quote_id}/approve")
async def approve_quote(
    quote_id: str,
    notes: Optional[str] = None,
    approver_id: str = Query(default="default")
):
    """Approve a quote"""
    if quote_id not in quotes:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    quote = quotes[quote_id]
    now = datetime.utcnow()
    
    if quote["status"] != QuoteStatus.PENDING_APPROVAL.value:
        raise HTTPException(status_code=400, detail="Quote is not pending approval")
    
    # Update approval record
    if quote.get("approval_id") and quote["approval_id"] in approvals:
        approval = approvals[quote["approval_id"]]
        approval["status"] = ApprovalStatus.APPROVED.value
        approval["approved_by"] = approver_id
        approval["approved_at"] = now.isoformat()
        approval["notes"] = notes
    
    quote["status"] = QuoteStatus.APPROVED.value
    quote["approved_by"] = approver_id
    quote["approved_at"] = now.isoformat()
    quote["updated_at"] = now.isoformat()
    
    logger.info("quote_approved", quote_id=quote_id, approver_id=approver_id)
    return quote


@router.post("/quotes/{quote_id}/reject")
async def reject_quote(
    quote_id: str,
    reason: str,
    approver_id: str = Query(default="default")
):
    """Reject a quote"""
    if quote_id not in quotes:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    quote = quotes[quote_id]
    now = datetime.utcnow()
    
    if quote["status"] != QuoteStatus.PENDING_APPROVAL.value:
        raise HTTPException(status_code=400, detail="Quote is not pending approval")
    
    # Update approval record
    if quote.get("approval_id") and quote["approval_id"] in approvals:
        approval = approvals[quote["approval_id"]]
        approval["status"] = ApprovalStatus.REJECTED.value
        approval["rejected_by"] = approver_id
        approval["rejected_at"] = now.isoformat()
        approval["rejection_reason"] = reason
    
    quote["status"] = QuoteStatus.DRAFT.value  # Back to draft for revision
    quote["rejection_reason"] = reason
    quote["updated_at"] = now.isoformat()
    
    logger.info("quote_rejected", quote_id=quote_id, reason=reason)
    return quote


@router.post("/quotes/{quote_id}/send")
async def send_quote(
    quote_id: str,
    recipient_email: str,
    cc_emails: Optional[List[str]] = None,
    message: Optional[str] = None
):
    """Send quote to customer"""
    if quote_id not in quotes:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    quote = quotes[quote_id]
    
    if quote["status"] not in [QuoteStatus.APPROVED.value, QuoteStatus.DRAFT.value]:
        raise HTTPException(status_code=400, detail="Quote cannot be sent in current status")
    
    now = datetime.utcnow()
    
    quote["status"] = QuoteStatus.SENT.value
    quote["sent_at"] = now.isoformat()
    quote["sent_to"] = recipient_email
    quote["view_link"] = f"https://app.example.com/quotes/view/{quote_id}"
    quote["updated_at"] = now.isoformat()
    
    logger.info("quote_sent", quote_id=quote_id, recipient=recipient_email)
    return quote


@router.post("/quotes/{quote_id}/mark-viewed")
async def mark_quote_viewed(quote_id: str):
    """Mark quote as viewed"""
    if quote_id not in quotes:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    quote = quotes[quote_id]
    
    if quote["status"] == QuoteStatus.SENT.value:
        quote["status"] = QuoteStatus.VIEWED.value
    
    quote["last_viewed_at"] = datetime.utcnow().isoformat()
    quote["view_count"] = quote.get("view_count", 0) + 1
    
    return quote


@router.post("/quotes/{quote_id}/accept")
async def accept_quote(
    quote_id: str,
    signature: Optional[str] = None,
    accepted_by: Optional[str] = None
):
    """Customer accepts quote"""
    if quote_id not in quotes:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    quote = quotes[quote_id]
    now = datetime.utcnow()
    
    quote["status"] = QuoteStatus.ACCEPTED.value
    quote["accepted_at"] = now.isoformat()
    quote["accepted_by"] = accepted_by
    quote["signature"] = signature
    quote["updated_at"] = now.isoformat()
    
    logger.info("quote_accepted", quote_id=quote_id)
    return quote


# Discount Rules
@router.post("/discount-rules")
async def create_discount_rule(
    request: DiscountRuleCreate,
    tenant_id: str = Query(default="default")
):
    """Create a discount rule"""
    rule_id = str(uuid.uuid4())
    
    rule = {
        "id": rule_id,
        "name": request.name,
        "discount_type": request.discount_type.value,
        "value": request.value,
        "conditions": request.conditions,
        "requires_approval": request.requires_approval,
        "approval_threshold": request.approval_threshold,
        "is_active": True,
        "tenant_id": tenant_id,
        "created_at": datetime.utcnow().isoformat()
    }
    
    discount_rules[rule_id] = rule
    
    return rule


@router.get("/discount-rules")
async def list_discount_rules(
    is_active: Optional[bool] = None,
    tenant_id: str = Query(default="default")
):
    """List discount rules"""
    result = [r for r in discount_rules.values() if r.get("tenant_id") == tenant_id]
    
    if is_active is not None:
        result = [r for r in result if r.get("is_active") == is_active]
    
    return {"rules": result, "total": len(result)}


# Product Bundles
@router.post("/bundles")
async def create_product_bundle(
    name: str,
    products: List[Dict[str, Any]],
    bundle_discount: float = 0,
    description: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Create a product bundle"""
    bundle_id = str(uuid.uuid4())
    
    bundle = {
        "id": bundle_id,
        "name": name,
        "description": description,
        "products": products,
        "bundle_discount": bundle_discount,
        "is_active": True,
        "tenant_id": tenant_id,
        "created_at": datetime.utcnow().isoformat()
    }
    
    product_bundles[bundle_id] = bundle
    
    return bundle


@router.get("/bundles")
async def list_product_bundles(
    is_active: Optional[bool] = None,
    tenant_id: str = Query(default="default")
):
    """List product bundles"""
    result = [b for b in product_bundles.values() if b.get("tenant_id") == tenant_id]
    
    if is_active is not None:
        result = [b for b in result if b.get("is_active") == is_active]
    
    return {"bundles": result, "total": len(result)}


@router.post("/bundles/{bundle_id}/add-to-quote")
async def add_bundle_to_quote(bundle_id: str, quote_id: str):
    """Add a bundle to a quote"""
    if bundle_id not in product_bundles:
        raise HTTPException(status_code=404, detail="Bundle not found")
    if quote_id not in quotes:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    bundle = product_bundles[bundle_id]
    items = quote_line_items.get(quote_id, [])
    quote = quotes[quote_id]
    
    # Add each product from bundle
    for product in bundle.get("products", []):
        line_item = {
            "id": str(uuid.uuid4()),
            "quote_id": quote_id,
            "line_number": len(items) + 1,
            "product_id": product.get("product_id"),
            "quantity": product.get("quantity", 1),
            "unit_price": product.get("price", 1000),
            "list_price": product.get("price", 1000) * product.get("quantity", 1),
            "discount_type": "percentage",
            "discount_value": bundle.get("bundle_discount", 0),
            "discount_amount": product.get("price", 1000) * product.get("quantity", 1) * (bundle.get("bundle_discount", 0) / 100),
            "net_price": product.get("price", 1000) * product.get("quantity", 1) * (1 - bundle.get("bundle_discount", 0) / 100),
            "bundle_id": bundle_id,
            "configuration": {}
        }
        items.append(line_item)
    
    quote_line_items[quote_id] = items
    
    # Recalculate totals
    quote["subtotal"] = sum(i["list_price"] for i in items)
    quote["total_discount"] = sum(i["discount_amount"] for i in items)
    quote["total"] = quote["subtotal"] - quote["total_discount"]
    quote["updated_at"] = datetime.utcnow().isoformat()
    
    return {**quote, "line_items": items}


# Pricing Calculator
@router.post("/calculate-price")
async def calculate_price(
    products: List[ProductConfig],
    price_book_id: Optional[str] = None,
    apply_discount_rules: bool = True
):
    """Calculate pricing for products"""
    subtotal = 0
    total_discount = 0
    line_items = []
    
    for product in products:
        # Mock price lookup
        unit_price = 1000.0
        line_total = unit_price * product.quantity
        discount = 0
        
        if product.discount_type and product.discount_value:
            if product.discount_type == DiscountType.PERCENTAGE:
                discount = line_total * (product.discount_value / 100)
            elif product.discount_type == DiscountType.FIXED:
                discount = product.discount_value
        
        line_items.append({
            "product_id": product.product_id,
            "quantity": product.quantity,
            "unit_price": unit_price,
            "list_price": line_total,
            "discount": discount,
            "net_price": line_total - discount
        })
        
        subtotal += line_total
        total_discount += discount
    
    return {
        "line_items": line_items,
        "subtotal": subtotal,
        "total_discount": total_discount,
        "total": subtotal - total_discount,
        "currency": "USD"
    }


# Quote Templates
@router.post("/templates")
async def create_quote_template(
    name: str,
    default_terms: Optional[str] = None,
    default_validity_days: int = 30,
    line_item_template: Optional[List[ProductConfig]] = None,
    tenant_id: str = Query(default="default")
):
    """Create a quote template"""
    template_id = str(uuid.uuid4())
    
    template = {
        "id": template_id,
        "name": name,
        "default_terms": default_terms,
        "default_validity_days": default_validity_days,
        "line_item_template": [l.dict() for l in line_item_template] if line_item_template else [],
        "tenant_id": tenant_id,
        "created_at": datetime.utcnow().isoformat()
    }
    
    quote_templates[template_id] = template
    
    return template


@router.get("/templates")
async def list_quote_templates(tenant_id: str = Query(default="default")):
    """List quote templates"""
    result = [t for t in quote_templates.values() if t.get("tenant_id") == tenant_id]
    return {"templates": result, "total": len(result)}


# Generate PDF
@router.post("/quotes/{quote_id}/generate-pdf")
async def generate_quote_pdf(quote_id: str):
    """Generate PDF for a quote"""
    if quote_id not in quotes:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    quote = quotes[quote_id]
    
    return {
        "quote_id": quote_id,
        "pdf_url": f"https://storage.example.com/quotes/{quote_id}.pdf",
        "generated_at": datetime.utcnow().isoformat(),
        "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat()
    }


# Stats
@router.get("/stats")
async def get_cpq_stats(tenant_id: str = Query(default="default")):
    """Get CPQ statistics"""
    tenant_quotes = [q for q in quotes.values() if q.get("tenant_id") == tenant_id]
    
    return {
        "total_quotes": len(tenant_quotes),
        "by_status": {
            status.value: len([q for q in tenant_quotes if q.get("status") == status.value])
            for status in QuoteStatus
        },
        "total_value": sum(q.get("total", 0) for q in tenant_quotes),
        "accepted_value": sum(q.get("total", 0) for q in tenant_quotes if q.get("status") == QuoteStatus.ACCEPTED.value),
        "avg_quote_value": sum(q.get("total", 0) for q in tenant_quotes) / len(tenant_quotes) if tenant_quotes else 0,
        "avg_discount_percent": sum(q.get("discount_percent", 0) for q in tenant_quotes) / len(tenant_quotes) if tenant_quotes else 0,
        "pending_approvals": len([q for q in tenant_quotes if q.get("status") == QuoteStatus.PENDING_APPROVAL.value]),
        "conversion_rate": len([q for q in tenant_quotes if q.get("status") == QuoteStatus.ACCEPTED.value]) / len(tenant_quotes) * 100 if tenant_quotes else 0
    }
