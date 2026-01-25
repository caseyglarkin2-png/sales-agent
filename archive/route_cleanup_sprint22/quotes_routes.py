"""
Quotes Routes - Quote Management API
=====================================
REST API for quotes and proposals.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime

from src.quotes.quote_service import (
    get_quote_service,
    QuoteStatus,
    DiscountType,
    PaymentTerms,
    Currency,
)

router = APIRouter(prefix="/quotes", tags=["quotes"])


class CreateQuoteRequest(BaseModel):
    """Request to create a quote."""
    title: str
    owner_id: str
    deal_id: Optional[str] = None
    contact_id: Optional[str] = None
    company_id: Optional[str] = None
    template_id: Optional[str] = None
    valid_days: int = 30
    introduction: Optional[str] = None
    terms_and_conditions: Optional[str] = None
    notes: Optional[str] = None
    currency: str = "USD"
    payment_terms: str = "net_30"
    requires_approval: bool = False
    signature_required: bool = False


class UpdateQuoteRequest(BaseModel):
    """Request to update a quote."""
    title: Optional[str] = None
    introduction: Optional[str] = None
    terms_and_conditions: Optional[str] = None
    notes: Optional[str] = None
    discount_type: Optional[str] = None
    discount_value: Optional[float] = None
    tax_rate: Optional[float] = None
    shipping_amount: Optional[float] = None
    payment_terms: Optional[str] = None
    deposit_required: Optional[bool] = None
    deposit_percentage: Optional[float] = None


class AddItemRequest(BaseModel):
    """Request to add a line item."""
    name: str
    description: str = ""
    quantity: int = 1
    unit_price: float
    product_id: Optional[str] = None
    sku: Optional[str] = None
    unit: str = "unit"
    discount_type: Optional[str] = None
    discount_value: float = 0.0
    tax_rate: float = 0.0
    is_optional: bool = False
    notes: Optional[str] = None


class UpdateItemRequest(BaseModel):
    """Request to update a line item."""
    name: Optional[str] = None
    description: Optional[str] = None
    quantity: Optional[int] = None
    unit_price: Optional[float] = None
    discount_type: Optional[str] = None
    discount_value: Optional[float] = None
    tax_rate: Optional[float] = None
    is_optional: Optional[bool] = None
    notes: Optional[str] = None


class ReorderItemsRequest(BaseModel):
    """Request to reorder items."""
    item_order: list[str]


class ApprovalRequest(BaseModel):
    """Request for approval workflow."""
    notes: Optional[str] = None


class ApproveRequest(BaseModel):
    """Request to approve a quote."""
    approver_id: str


class RejectRequest(BaseModel):
    """Request to reject a quote."""
    reason: str


class AcceptQuoteRequest(BaseModel):
    """Request to accept a quote."""
    signer_name: Optional[str] = None
    signer_email: Optional[str] = None


class DeclineQuoteRequest(BaseModel):
    """Request to decline a quote."""
    reason: Optional[str] = None


class RevisionRequest(BaseModel):
    """Request to create a revision."""
    revision_notes: Optional[str] = None


class CreateTemplateRequest(BaseModel):
    """Request to create a template."""
    name: str
    description: str
    content: dict[str, Any] = {}
    items: list[dict[str, Any]] = []
    terms_and_conditions: str = ""


def quote_to_dict(quote) -> dict:
    """Convert quote to dictionary."""
    return {
        "id": quote.id,
        "quote_number": quote.quote_number,
        "title": quote.title,
        "deal_id": quote.deal_id,
        "contact_id": quote.contact_id,
        "company_id": quote.company_id,
        "owner_id": quote.owner_id,
        "status": quote.status.value,
        "items": [
            {
                "id": item.id,
                "product_id": item.product_id,
                "name": item.name,
                "description": item.description,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "discount_type": item.discount_type.value if item.discount_type else None,
                "discount_value": item.discount_value,
                "tax_rate": item.tax_rate,
                "subtotal": item.subtotal,
                "total": item.total,
                "sku": item.sku,
                "unit": item.unit,
                "is_optional": item.is_optional,
                "notes": item.notes,
            }
            for item in quote.items
        ],
        "introduction": quote.introduction,
        "terms_and_conditions": quote.terms_and_conditions,
        "notes": quote.notes,
        "currency": quote.currency.value,
        "subtotal": quote.subtotal,
        "discount_type": quote.discount_type.value if quote.discount_type else None,
        "discount_value": quote.discount_value,
        "discount_amount": quote.discount_amount,
        "tax_rate": quote.tax_rate,
        "tax_amount": quote.tax_amount,
        "shipping_amount": quote.shipping_amount,
        "total": quote.total,
        "payment_terms": quote.payment_terms.value,
        "deposit_required": quote.deposit_required,
        "deposit_percentage": quote.deposit_percentage,
        "deposit_amount": quote.deposit_amount,
        "valid_until": quote.valid_until.isoformat() if quote.valid_until else None,
        "sent_at": quote.sent_at.isoformat() if quote.sent_at else None,
        "viewed_at": quote.viewed_at.isoformat() if quote.viewed_at else None,
        "accepted_at": quote.accepted_at.isoformat() if quote.accepted_at else None,
        "declined_at": quote.declined_at.isoformat() if quote.declined_at else None,
        "requires_approval": quote.requires_approval,
        "approved_by": quote.approved_by,
        "approved_at": quote.approved_at.isoformat() if quote.approved_at else None,
        "signature_required": quote.signature_required,
        "signed_at": quote.signed_at.isoformat() if quote.signed_at else None,
        "signer_name": quote.signer_name,
        "version": quote.version,
        "parent_quote_id": quote.parent_quote_id,
        "created_at": quote.created_at.isoformat(),
        "updated_at": quote.updated_at.isoformat(),
    }


@router.post("")
async def create_quote(request: CreateQuoteRequest):
    """Create a new quote."""
    service = get_quote_service()
    
    quote = await service.create_quote(
        title=request.title,
        owner_id=request.owner_id,
        deal_id=request.deal_id,
        contact_id=request.contact_id,
        company_id=request.company_id,
        template_id=request.template_id,
        valid_days=request.valid_days,
        introduction=request.introduction or "",
        terms_and_conditions=request.terms_and_conditions or "",
        notes=request.notes or "",
        currency=Currency(request.currency),
        payment_terms=PaymentTerms(request.payment_terms),
        requires_approval=request.requires_approval,
        signature_required=request.signature_required,
    )
    
    return {"quote": quote_to_dict(quote)}


@router.get("")
async def list_quotes(
    owner_id: Optional[str] = None,
    deal_id: Optional[str] = None,
    company_id: Optional[str] = None,
    contact_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0)
):
    """List quotes with filters."""
    service = get_quote_service()
    
    status_enum = QuoteStatus(status) if status else None
    
    quotes = await service.list_quotes(
        owner_id=owner_id,
        deal_id=deal_id,
        company_id=company_id,
        contact_id=contact_id,
        status=status_enum,
        limit=limit,
        offset=offset
    )
    
    return {
        "quotes": [quote_to_dict(q) for q in quotes],
        "count": len(quotes)
    }


@router.get("/stats")
async def get_quote_stats(
    owner_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get quote statistics."""
    service = get_quote_service()
    
    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None
    
    stats = await service.get_quote_stats(
        owner_id=owner_id,
        start_date=start,
        end_date=end
    )
    
    return stats


@router.get("/templates")
async def list_templates(active_only: bool = True):
    """List quote templates."""
    service = get_quote_service()
    
    templates = await service.list_templates(active_only=active_only)
    
    return {
        "templates": [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "is_default": t.is_default,
                "is_active": t.is_active,
            }
            for t in templates
        ]
    }


@router.post("/templates")
async def create_template(request: CreateTemplateRequest):
    """Create a quote template."""
    service = get_quote_service()
    
    template = await service.create_template(
        name=request.name,
        description=request.description,
        content=request.content,
        items=request.items,
        terms_and_conditions=request.terms_and_conditions,
    )
    
    return {
        "template": {
            "id": template.id,
            "name": template.name,
            "description": template.description,
        }
    }


@router.get("/{quote_id}")
async def get_quote(quote_id: str):
    """Get a quote by ID."""
    service = get_quote_service()
    
    quote = await service.get_quote(quote_id)
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    return {"quote": quote_to_dict(quote)}


@router.put("/{quote_id}")
async def update_quote(quote_id: str, request: UpdateQuoteRequest):
    """Update a quote."""
    service = get_quote_service()
    
    updates = request.model_dump(exclude_none=True)
    
    # Convert enum strings
    if "discount_type" in updates:
        updates["discount_type"] = DiscountType(updates["discount_type"])
    if "payment_terms" in updates:
        updates["payment_terms"] = PaymentTerms(updates["payment_terms"])
    
    quote = await service.update_quote(quote_id, updates)
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found or cannot be edited")
    
    return {"quote": quote_to_dict(quote)}


@router.delete("/{quote_id}")
async def delete_quote(quote_id: str):
    """Delete a quote."""
    service = get_quote_service()
    
    success = await service.delete_quote(quote_id)
    if not success:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    return {"success": True}


# Line items
@router.post("/{quote_id}/items")
async def add_item(quote_id: str, request: AddItemRequest):
    """Add a line item to a quote."""
    service = get_quote_service()
    
    kwargs = request.model_dump()
    if kwargs.get("discount_type"):
        kwargs["discount_type"] = DiscountType(kwargs["discount_type"])
    
    item = await service.add_item(
        quote_id=quote_id,
        **kwargs
    )
    
    if not item:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    # Get updated quote
    quote = await service.get_quote(quote_id)
    
    return {"quote": quote_to_dict(quote)}


@router.put("/{quote_id}/items/{item_id}")
async def update_item(quote_id: str, item_id: str, request: UpdateItemRequest):
    """Update a line item."""
    service = get_quote_service()
    
    updates = request.model_dump(exclude_none=True)
    if "discount_type" in updates:
        updates["discount_type"] = DiscountType(updates["discount_type"])
    
    item = await service.update_item(quote_id, item_id, updates)
    if not item:
        raise HTTPException(status_code=404, detail="Quote or item not found")
    
    quote = await service.get_quote(quote_id)
    
    return {"quote": quote_to_dict(quote)}


@router.delete("/{quote_id}/items/{item_id}")
async def remove_item(quote_id: str, item_id: str):
    """Remove a line item."""
    service = get_quote_service()
    
    success = await service.remove_item(quote_id, item_id)
    if not success:
        raise HTTPException(status_code=404, detail="Quote or item not found")
    
    quote = await service.get_quote(quote_id)
    
    return {"quote": quote_to_dict(quote)}


@router.post("/{quote_id}/items/reorder")
async def reorder_items(quote_id: str, request: ReorderItemsRequest):
    """Reorder line items."""
    service = get_quote_service()
    
    success = await service.reorder_items(quote_id, request.item_order)
    if not success:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    quote = await service.get_quote(quote_id)
    
    return {"quote": quote_to_dict(quote)}


# Approval workflow
@router.post("/{quote_id}/submit-approval")
async def submit_for_approval(quote_id: str, request: ApprovalRequest):
    """Submit quote for approval."""
    service = get_quote_service()
    
    success = await service.submit_for_approval(quote_id, request.notes)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot submit quote for approval")
    
    quote = await service.get_quote(quote_id)
    
    return {"quote": quote_to_dict(quote)}


@router.post("/{quote_id}/approve")
async def approve_quote(quote_id: str, request: ApproveRequest):
    """Approve a quote."""
    service = get_quote_service()
    
    success = await service.approve_quote(quote_id, request.approver_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot approve quote")
    
    quote = await service.get_quote(quote_id)
    
    return {"quote": quote_to_dict(quote)}


@router.post("/{quote_id}/reject")
async def reject_quote(quote_id: str, request: RejectRequest):
    """Reject a quote."""
    service = get_quote_service()
    
    success = await service.reject_quote(quote_id, request.reason)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot reject quote")
    
    quote = await service.get_quote(quote_id)
    
    return {"quote": quote_to_dict(quote)}


# Send and track
@router.post("/{quote_id}/send")
async def send_quote(quote_id: str):
    """Send a quote."""
    service = get_quote_service()
    
    success = await service.send_quote(quote_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot send quote")
    
    quote = await service.get_quote(quote_id)
    
    return {"quote": quote_to_dict(quote)}


@router.post("/{quote_id}/viewed")
async def mark_viewed(quote_id: str):
    """Mark quote as viewed (tracking pixel)."""
    service = get_quote_service()
    
    await service.mark_viewed(quote_id)
    
    return {"success": True}


@router.post("/{quote_id}/accept")
async def accept_quote(quote_id: str, request: AcceptQuoteRequest):
    """Accept/sign a quote."""
    service = get_quote_service()
    
    success = await service.accept_quote(
        quote_id,
        signer_name=request.signer_name,
        signer_email=request.signer_email
    )
    if not success:
        raise HTTPException(status_code=400, detail="Cannot accept quote (may be expired)")
    
    quote = await service.get_quote(quote_id)
    
    return {"quote": quote_to_dict(quote)}


@router.post("/{quote_id}/decline")
async def decline_quote(quote_id: str, request: DeclineQuoteRequest):
    """Decline a quote."""
    service = get_quote_service()
    
    success = await service.decline_quote(quote_id, request.reason)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot decline quote")
    
    quote = await service.get_quote(quote_id)
    
    return {"quote": quote_to_dict(quote)}


# Revisions
@router.post("/{quote_id}/revise")
async def create_revision(quote_id: str, request: RevisionRequest):
    """Create a new revision of a quote."""
    service = get_quote_service()
    
    quote = await service.create_revision(quote_id, request.revision_notes)
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    return {"quote": quote_to_dict(quote)}


@router.get("/{quote_id}/revisions")
async def get_revisions(quote_id: str):
    """Get all revisions of a quote."""
    service = get_quote_service()
    
    revisions = await service.get_quote_revisions(quote_id)
    
    return {
        "revisions": [quote_to_dict(q) for q in revisions]
    }


# Document generation
@router.get("/{quote_id}/pdf")
async def download_pdf(quote_id: str):
    """Download quote as PDF."""
    service = get_quote_service()
    
    pdf_content = await service.generate_pdf(quote_id)
    if not pdf_content:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    # In real implementation, return PDF file
    return {"message": "PDF generation placeholder"}


@router.get("/{quote_id}/view-url")
async def get_public_url(quote_id: str):
    """Get public viewing URL for quote."""
    service = get_quote_service()
    
    url = await service.get_public_view_url(quote_id)
    if not url:
        raise HTTPException(status_code=404, detail="Quote not found")
    
    return {"url": url}
