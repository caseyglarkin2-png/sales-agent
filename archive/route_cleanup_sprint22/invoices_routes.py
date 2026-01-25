"""
Invoices Routes - Invoice Management API
=========================================
REST API endpoints for invoice management.
"""

from decimal import Decimal
from fastapi import APIRouter, HTTPException, Query
from typing import Any, Optional
from pydantic import BaseModel
from datetime import datetime

from ..invoices import (
    InvoiceService,
    InvoiceStatus,
    InvoiceType,
    PaymentMethod,
    get_invoice_service,
)


router = APIRouter(prefix="/invoices", tags=["Invoices"])


# Request/Response models
class CreateInvoiceRequest(BaseModel):
    """Create invoice request."""
    customer_id: str
    customer_name: str
    customer_email: Optional[str] = None
    invoice_type: Optional[str] = "standard"
    payment_terms: str = "Net 30"
    due_days: int = 30
    billing_address: Optional[dict[str, str]] = None
    shipping_address: Optional[dict[str, str]] = None
    notes: Optional[str] = None
    deal_id: Optional[str] = None
    quote_id: Optional[str] = None


class UpdateInvoiceRequest(BaseModel):
    """Update invoice request."""
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    billing_address: Optional[dict[str, str]] = None
    shipping_address: Optional[dict[str, str]] = None
    notes: Optional[str] = None
    footer: Optional[str] = None


class AddItemRequest(BaseModel):
    """Add invoice item request."""
    description: str
    quantity: float = 1
    unit_price: float = 0
    discount_percent: float = 0
    tax_rate: float = 0
    product_id: Optional[str] = None


class UpdateItemRequest(BaseModel):
    """Update invoice item request."""
    description: Optional[str] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    discount_percent: Optional[float] = None
    tax_rate: Optional[float] = None


class RecordPaymentRequest(BaseModel):
    """Record payment request."""
    amount: float
    method: Optional[str] = "credit_card"
    reference_number: Optional[str] = None
    transaction_id: Optional[str] = None
    notes: Optional[str] = None


class RefundPaymentRequest(BaseModel):
    """Refund payment request."""
    payment_id: str
    amount: Optional[float] = None


class CancelInvoiceRequest(BaseModel):
    """Cancel invoice request."""
    reason: Optional[str] = None


class CreateTemplateRequest(BaseModel):
    """Create template request."""
    name: str
    header_html: Optional[str] = None
    footer_html: Optional[str] = None
    terms_text: Optional[str] = None
    default_payment_terms: str = "Net 30"
    default_tax_rate: float = 0


def get_service() -> InvoiceService:
    """Get invoice service instance."""
    return get_invoice_service()


# Invoice CRUD
@router.post("")
async def create_invoice(request: CreateInvoiceRequest):
    """Create a new invoice."""
    service = get_service()
    
    try:
        invoice_type = InvoiceType(request.invoice_type) if request.invoice_type else InvoiceType.STANDARD
    except ValueError:
        invoice_type = InvoiceType.STANDARD
    
    invoice = await service.create_invoice(
        customer_id=request.customer_id,
        customer_name=request.customer_name,
        customer_email=request.customer_email,
        invoice_type=invoice_type,
        payment_terms=request.payment_terms,
        due_days=request.due_days,
        billing_address=request.billing_address,
        shipping_address=request.shipping_address,
        notes=request.notes,
        deal_id=request.deal_id,
        quote_id=request.quote_id,
    )
    
    return {
        "id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "customer_name": invoice.customer_name,
        "status": invoice.status.value,
        "total": float(invoice.total),
        "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
        "created_at": invoice.created_at.isoformat(),
    }


@router.get("")
async def list_invoices(
    customer_id: Optional[str] = None,
    status: Optional[str] = None,
    overdue_only: bool = False,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    limit: int = Query(default=100, le=500)
):
    """List invoices."""
    service = get_service()
    
    status_enum = None
    if status:
        try:
            status_enum = InvoiceStatus(status)
        except ValueError:
            pass
    
    invoices = await service.list_invoices(
        customer_id=customer_id,
        status=status_enum,
        overdue_only=overdue_only,
        from_date=from_date,
        to_date=to_date,
        limit=limit
    )
    
    return {
        "invoices": [
            {
                "id": i.id,
                "invoice_number": i.invoice_number,
                "customer_id": i.customer_id,
                "customer_name": i.customer_name,
                "status": i.status.value,
                "total": float(i.total),
                "amount_paid": float(i.amount_paid),
                "balance_due": float(i.balance_due),
                "issue_date": i.issue_date.isoformat(),
                "due_date": i.due_date.isoformat() if i.due_date else None,
                "is_overdue": i.is_overdue,
            }
            for i in invoices
        ],
        "total": len(invoices)
    }


@router.get("/stats")
async def get_invoice_stats(
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None
):
    """Get invoice statistics."""
    service = get_service()
    return await service.get_invoice_stats(from_date=from_date, to_date=to_date)


@router.get("/{invoice_id}")
async def get_invoice(invoice_id: str):
    """Get an invoice by ID."""
    service = get_service()
    invoice = await service.get_invoice(invoice_id)
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    return {
        "id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "customer_id": invoice.customer_id,
        "customer_name": invoice.customer_name,
        "customer_email": invoice.customer_email,
        "billing_address": invoice.billing_address,
        "shipping_address": invoice.shipping_address,
        "invoice_type": invoice.invoice_type.value,
        "status": invoice.status.value,
        "items": [
            {
                "id": item.id,
                "description": item.description,
                "quantity": float(item.quantity),
                "unit_price": float(item.unit_price),
                "discount_percent": float(item.discount_percent),
                "tax_rate": float(item.tax_rate),
                "subtotal": float(item.subtotal),
                "total": float(item.total),
                "product_id": item.product_id,
            }
            for item in invoice.items
        ],
        "subtotal": float(invoice.subtotal),
        "discount_total": float(invoice.discount_total),
        "tax_total": float(invoice.tax_total),
        "total": float(invoice.total),
        "amount_paid": float(invoice.amount_paid),
        "balance_due": float(invoice.balance_due),
        "currency": invoice.currency,
        "issue_date": invoice.issue_date.isoformat(),
        "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
        "paid_date": invoice.paid_date.isoformat() if invoice.paid_date else None,
        "payment_terms": invoice.payment_terms,
        "notes": invoice.notes,
        "payments": [
            {
                "id": p.id,
                "amount": float(p.amount),
                "method": p.method.value,
                "reference_number": p.reference_number,
                "received_at": p.received_at.isoformat(),
                "is_refunded": p.is_refunded,
            }
            for p in invoice.payments
        ],
        "is_overdue": invoice.is_overdue,
        "sent_at": invoice.sent_at.isoformat() if invoice.sent_at else None,
        "viewed_at": invoice.viewed_at.isoformat() if invoice.viewed_at else None,
        "reminder_count": invoice.reminder_count,
        "deal_id": invoice.deal_id,
        "quote_id": invoice.quote_id,
        "created_at": invoice.created_at.isoformat(),
        "updated_at": invoice.updated_at.isoformat(),
    }


@router.patch("/{invoice_id}")
async def update_invoice(invoice_id: str, request: UpdateInvoiceRequest):
    """Update an invoice."""
    service = get_service()
    
    updates = request.model_dump(exclude_unset=True)
    invoice = await service.update_invoice(invoice_id, updates)
    
    if not invoice:
        raise HTTPException(status_code=400, detail="Cannot update invoice")
    
    return {"success": True, "invoice_id": invoice_id}


@router.delete("/{invoice_id}")
async def delete_invoice(invoice_id: str):
    """Delete a draft invoice."""
    service = get_service()
    
    if not await service.delete_invoice(invoice_id):
        raise HTTPException(status_code=400, detail="Cannot delete invoice")
    
    return {"success": True}


# Line items
@router.post("/{invoice_id}/items")
async def add_item(invoice_id: str, request: AddItemRequest):
    """Add a line item."""
    service = get_service()
    
    item = await service.add_item(
        invoice_id=invoice_id,
        description=request.description,
        quantity=Decimal(str(request.quantity)),
        unit_price=Decimal(str(request.unit_price)),
        discount_percent=Decimal(str(request.discount_percent)),
        tax_rate=Decimal(str(request.tax_rate)),
        product_id=request.product_id,
    )
    
    if not item:
        raise HTTPException(status_code=400, detail="Cannot add item")
    
    return {
        "id": item.id,
        "description": item.description,
        "total": float(item.total),
    }


@router.patch("/{invoice_id}/items/{item_id}")
async def update_item(invoice_id: str, item_id: str, request: UpdateItemRequest):
    """Update a line item."""
    service = get_service()
    
    updates = {}
    if request.description is not None:
        updates["description"] = request.description
    if request.quantity is not None:
        updates["quantity"] = Decimal(str(request.quantity))
    if request.unit_price is not None:
        updates["unit_price"] = Decimal(str(request.unit_price))
    if request.discount_percent is not None:
        updates["discount_percent"] = Decimal(str(request.discount_percent))
    if request.tax_rate is not None:
        updates["tax_rate"] = Decimal(str(request.tax_rate))
    
    item = await service.update_item(invoice_id, item_id, updates)
    
    if not item:
        raise HTTPException(status_code=400, detail="Cannot update item")
    
    return {"success": True, "item_id": item_id}


@router.delete("/{invoice_id}/items/{item_id}")
async def remove_item(invoice_id: str, item_id: str):
    """Remove a line item."""
    service = get_service()
    
    if not await service.remove_item(invoice_id, item_id):
        raise HTTPException(status_code=400, detail="Cannot remove item")
    
    return {"success": True}


# Workflow
@router.post("/{invoice_id}/send")
async def send_invoice(invoice_id: str, send_email: bool = True):
    """Send an invoice."""
    service = get_service()
    
    if not await service.send_invoice(invoice_id, send_email=send_email):
        raise HTTPException(status_code=400, detail="Cannot send invoice")
    
    return {"success": True, "status": "sent"}


@router.post("/{invoice_id}/viewed")
async def mark_viewed(invoice_id: str):
    """Mark invoice as viewed."""
    service = get_service()
    
    if not await service.mark_as_viewed(invoice_id):
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    return {"success": True}


@router.post("/{invoice_id}/cancel")
async def cancel_invoice(invoice_id: str, request: CancelInvoiceRequest):
    """Cancel an invoice."""
    service = get_service()
    
    if not await service.cancel_invoice(invoice_id, reason=request.reason):
        raise HTTPException(status_code=400, detail="Cannot cancel invoice")
    
    return {"success": True, "status": "cancelled"}


@router.post("/{invoice_id}/reminder")
async def send_reminder(invoice_id: str):
    """Send payment reminder."""
    service = get_service()
    
    if not await service.send_reminder(invoice_id):
        raise HTTPException(status_code=400, detail="Cannot send reminder")
    
    return {"success": True}


# Payments
@router.post("/{invoice_id}/payments")
async def record_payment(invoice_id: str, request: RecordPaymentRequest):
    """Record a payment."""
    service = get_service()
    
    try:
        method = PaymentMethod(request.method) if request.method else PaymentMethod.CREDIT_CARD
    except ValueError:
        method = PaymentMethod.CREDIT_CARD
    
    payment = await service.record_payment(
        invoice_id=invoice_id,
        amount=Decimal(str(request.amount)),
        method=method,
        reference_number=request.reference_number,
        transaction_id=request.transaction_id,
        notes=request.notes,
    )
    
    if not payment:
        raise HTTPException(status_code=400, detail="Cannot record payment")
    
    invoice = await service.get_invoice(invoice_id)
    
    return {
        "payment_id": payment.id,
        "amount": float(payment.amount),
        "invoice_status": invoice.status.value if invoice else None,
        "balance_due": float(invoice.balance_due) if invoice else None,
    }


@router.post("/{invoice_id}/refund")
async def refund_payment(invoice_id: str, request: RefundPaymentRequest):
    """Refund a payment."""
    service = get_service()
    
    amount = Decimal(str(request.amount)) if request.amount else None
    
    if not await service.refund_payment(invoice_id, request.payment_id, amount):
        raise HTTPException(status_code=400, detail="Cannot refund payment")
    
    return {"success": True}


# Templates
@router.get("/templates")
async def list_templates():
    """List invoice templates."""
    service = get_service()
    templates = await service.list_templates()
    
    return {
        "templates": [
            {
                "id": t.id,
                "name": t.name,
                "is_default": t.is_default,
                "default_payment_terms": t.default_payment_terms,
            }
            for t in templates
        ]
    }


@router.post("/templates")
async def create_template(request: CreateTemplateRequest):
    """Create an invoice template."""
    service = get_service()
    
    template = await service.create_template(
        name=request.name,
        header_html=request.header_html,
        footer_html=request.footer_html,
        terms_text=request.terms_text,
        default_payment_terms=request.default_payment_terms,
        default_tax_rate=Decimal(str(request.default_tax_rate)),
    )
    
    return {
        "id": template.id,
        "name": template.name,
    }
