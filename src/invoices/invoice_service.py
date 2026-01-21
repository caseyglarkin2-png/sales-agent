"""
Invoice Service - Invoice Management
=====================================
Handles invoice generation, payments, and tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Optional
import uuid


class InvoiceStatus(str, Enum):
    """Invoice status."""
    DRAFT = "draft"
    SENT = "sent"
    VIEWED = "viewed"
    PARTIAL = "partial"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentMethod(str, Enum):
    """Payment method."""
    CREDIT_CARD = "credit_card"
    BANK_TRANSFER = "bank_transfer"
    CHECK = "check"
    CASH = "cash"
    WIRE = "wire"
    ACH = "ach"
    PAYPAL = "paypal"
    OTHER = "other"


class InvoiceType(str, Enum):
    """Invoice type."""
    STANDARD = "standard"
    RECURRING = "recurring"
    CREDIT = "credit"
    PROFORMA = "proforma"


@dataclass
class InvoiceItem:
    """A line item on an invoice."""
    id: str
    description: str
    quantity: Decimal = Decimal("1")
    unit_price: Decimal = Decimal("0")
    discount_percent: Decimal = Decimal("0")
    tax_rate: Decimal = Decimal("0")
    
    # Linked entities
    product_id: Optional[str] = None
    quote_item_id: Optional[str] = None
    
    @property
    def subtotal(self) -> Decimal:
        """Calculate subtotal."""
        return self.quantity * self.unit_price
    
    @property
    def discount_amount(self) -> Decimal:
        """Calculate discount."""
        return self.subtotal * (self.discount_percent / Decimal("100"))
    
    @property
    def taxable_amount(self) -> Decimal:
        """Calculate taxable amount."""
        return self.subtotal - self.discount_amount
    
    @property
    def tax_amount(self) -> Decimal:
        """Calculate tax."""
        return self.taxable_amount * (self.tax_rate / Decimal("100"))
    
    @property
    def total(self) -> Decimal:
        """Calculate total."""
        return self.taxable_amount + self.tax_amount


@dataclass
class Payment:
    """A payment record."""
    id: str
    invoice_id: str
    amount: Decimal
    method: PaymentMethod = PaymentMethod.CREDIT_CARD
    
    # Details
    reference_number: Optional[str] = None
    notes: Optional[str] = None
    
    # External reference
    transaction_id: Optional[str] = None
    gateway: Optional[str] = None
    
    # State
    is_refunded: bool = False
    refund_amount: Decimal = Decimal("0")
    refund_date: Optional[datetime] = None
    
    received_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None


@dataclass
class Invoice:
    """An invoice."""
    id: str
    invoice_number: str
    
    # Customer
    customer_id: str
    customer_name: str
    customer_email: Optional[str] = None
    
    # Addresses
    billing_address: Optional[dict[str, str]] = None
    shipping_address: Optional[dict[str, str]] = None
    
    # Type and status
    invoice_type: InvoiceType = InvoiceType.STANDARD
    status: InvoiceStatus = InvoiceStatus.DRAFT
    
    # Items
    items: list[InvoiceItem] = field(default_factory=list)
    
    # Totals
    subtotal: Decimal = Decimal("0")
    discount_total: Decimal = Decimal("0")
    tax_total: Decimal = Decimal("0")
    total: Decimal = Decimal("0")
    amount_paid: Decimal = Decimal("0")
    
    # Currency
    currency: str = "USD"
    
    # Dates
    issue_date: datetime = field(default_factory=datetime.utcnow)
    due_date: Optional[datetime] = None
    paid_date: Optional[datetime] = None
    
    # Payments
    payments: list[Payment] = field(default_factory=list)
    
    # Terms
    payment_terms: str = "Net 30"
    notes: Optional[str] = None
    footer: Optional[str] = None
    
    # Links
    deal_id: Optional[str] = None
    quote_id: Optional[str] = None
    contract_id: Optional[str] = None
    subscription_id: Optional[str] = None
    
    # Recurring
    is_recurring: bool = False
    recurring_schedule: Optional[str] = None
    parent_invoice_id: Optional[str] = None
    
    # Tracking
    sent_at: Optional[datetime] = None
    viewed_at: Optional[datetime] = None
    reminder_count: int = 0
    last_reminder_at: Optional[datetime] = None
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    
    @property
    def balance_due(self) -> Decimal:
        """Calculate balance due."""
        return self.total - self.amount_paid
    
    @property
    def is_overdue(self) -> bool:
        """Check if overdue."""
        if self.status == InvoiceStatus.PAID:
            return False
        if self.due_date:
            return datetime.utcnow() > self.due_date
        return False


@dataclass
class InvoiceTemplate:
    """An invoice template."""
    id: str
    name: str
    
    # Content
    header_html: Optional[str] = None
    footer_html: Optional[str] = None
    terms_text: Optional[str] = None
    notes_text: Optional[str] = None
    
    # Styling
    logo_url: Optional[str] = None
    primary_color: str = "#2563eb"
    font_family: str = "Inter"
    
    # Default settings
    default_payment_terms: str = "Net 30"
    default_tax_rate: Decimal = Decimal("0")
    
    is_default: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)


class InvoiceService:
    """Service for invoice management."""
    
    def __init__(self):
        self.invoices: dict[str, Invoice] = {}
        self.templates: dict[str, InvoiceTemplate] = {}
        self.invoice_counter = 1000
    
    def _generate_invoice_number(self) -> str:
        """Generate invoice number."""
        self.invoice_counter += 1
        return f"INV-{self.invoice_counter:06d}"
    
    def _calculate_totals(self, invoice: Invoice) -> None:
        """Calculate invoice totals."""
        subtotal = Decimal("0")
        discount_total = Decimal("0")
        tax_total = Decimal("0")
        
        for item in invoice.items:
            subtotal += item.subtotal
            discount_total += item.discount_amount
            tax_total += item.tax_amount
        
        invoice.subtotal = subtotal
        invoice.discount_total = discount_total
        invoice.tax_total = tax_total
        invoice.total = subtotal - discount_total + tax_total
    
    # Invoice CRUD
    async def create_invoice(
        self,
        customer_id: str,
        customer_name: str,
        customer_email: Optional[str] = None,
        invoice_type: InvoiceType = InvoiceType.STANDARD,
        payment_terms: str = "Net 30",
        due_days: int = 30,
        created_by: Optional[str] = None,
        **kwargs
    ) -> Invoice:
        """Create a new invoice."""
        invoice = Invoice(
            id=str(uuid.uuid4()),
            invoice_number=self._generate_invoice_number(),
            customer_id=customer_id,
            customer_name=customer_name,
            customer_email=customer_email,
            invoice_type=invoice_type,
            payment_terms=payment_terms,
            due_date=datetime.utcnow() + timedelta(days=due_days),
            created_by=created_by,
            **kwargs
        )
        
        self.invoices[invoice.id] = invoice
        return invoice
    
    async def get_invoice(self, invoice_id: str) -> Optional[Invoice]:
        """Get an invoice by ID."""
        return self.invoices.get(invoice_id)
    
    async def get_invoice_by_number(self, invoice_number: str) -> Optional[Invoice]:
        """Get an invoice by number."""
        for invoice in self.invoices.values():
            if invoice.invoice_number == invoice_number:
                return invoice
        return None
    
    async def update_invoice(
        self,
        invoice_id: str,
        updates: dict[str, Any]
    ) -> Optional[Invoice]:
        """Update an invoice."""
        invoice = self.invoices.get(invoice_id)
        if not invoice:
            return None
        
        if invoice.status not in [InvoiceStatus.DRAFT]:
            # Only draft invoices can be edited
            return None
        
        for key, value in updates.items():
            if hasattr(invoice, key) and key not in ["id", "invoice_number"]:
                setattr(invoice, key, value)
        
        invoice.updated_at = datetime.utcnow()
        return invoice
    
    async def delete_invoice(self, invoice_id: str) -> bool:
        """Delete an invoice (draft only)."""
        invoice = self.invoices.get(invoice_id)
        if not invoice or invoice.status != InvoiceStatus.DRAFT:
            return False
        
        del self.invoices[invoice_id]
        return True
    
    async def list_invoices(
        self,
        customer_id: Optional[str] = None,
        status: Optional[InvoiceStatus] = None,
        overdue_only: bool = False,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        limit: int = 100
    ) -> list[Invoice]:
        """List invoices."""
        invoices = list(self.invoices.values())
        
        if customer_id:
            invoices = [i for i in invoices if i.customer_id == customer_id]
        if status:
            invoices = [i for i in invoices if i.status == status]
        if overdue_only:
            invoices = [i for i in invoices if i.is_overdue]
        if from_date:
            invoices = [i for i in invoices if i.issue_date >= from_date]
        if to_date:
            invoices = [i for i in invoices if i.issue_date <= to_date]
        
        invoices.sort(key=lambda i: i.issue_date, reverse=True)
        return invoices[:limit]
    
    # Line items
    async def add_item(
        self,
        invoice_id: str,
        description: str,
        quantity: Decimal = Decimal("1"),
        unit_price: Decimal = Decimal("0"),
        discount_percent: Decimal = Decimal("0"),
        tax_rate: Decimal = Decimal("0"),
        product_id: Optional[str] = None
    ) -> Optional[InvoiceItem]:
        """Add a line item."""
        invoice = self.invoices.get(invoice_id)
        if not invoice or invoice.status != InvoiceStatus.DRAFT:
            return None
        
        item = InvoiceItem(
            id=str(uuid.uuid4()),
            description=description,
            quantity=quantity,
            unit_price=unit_price,
            discount_percent=discount_percent,
            tax_rate=tax_rate,
            product_id=product_id,
        )
        
        invoice.items.append(item)
        self._calculate_totals(invoice)
        invoice.updated_at = datetime.utcnow()
        
        return item
    
    async def update_item(
        self,
        invoice_id: str,
        item_id: str,
        updates: dict[str, Any]
    ) -> Optional[InvoiceItem]:
        """Update a line item."""
        invoice = self.invoices.get(invoice_id)
        if not invoice or invoice.status != InvoiceStatus.DRAFT:
            return None
        
        item = next((i for i in invoice.items if i.id == item_id), None)
        if not item:
            return None
        
        for key, value in updates.items():
            if hasattr(item, key) and key != "id":
                setattr(item, key, value)
        
        self._calculate_totals(invoice)
        invoice.updated_at = datetime.utcnow()
        
        return item
    
    async def remove_item(self, invoice_id: str, item_id: str) -> bool:
        """Remove a line item."""
        invoice = self.invoices.get(invoice_id)
        if not invoice or invoice.status != InvoiceStatus.DRAFT:
            return False
        
        original = len(invoice.items)
        invoice.items = [i for i in invoice.items if i.id != item_id]
        
        if len(invoice.items) < original:
            self._calculate_totals(invoice)
            invoice.updated_at = datetime.utcnow()
            return True
        
        return False
    
    # Invoice workflow
    async def send_invoice(
        self,
        invoice_id: str,
        send_email: bool = True
    ) -> bool:
        """Send an invoice."""
        invoice = self.invoices.get(invoice_id)
        if not invoice or invoice.status not in [InvoiceStatus.DRAFT]:
            return False
        
        invoice.status = InvoiceStatus.SENT
        invoice.sent_at = datetime.utcnow()
        invoice.updated_at = datetime.utcnow()
        
        # In real implementation, send email
        return True
    
    async def mark_as_viewed(self, invoice_id: str) -> bool:
        """Mark invoice as viewed."""
        invoice = self.invoices.get(invoice_id)
        if not invoice:
            return False
        
        if not invoice.viewed_at:
            invoice.viewed_at = datetime.utcnow()
            if invoice.status == InvoiceStatus.SENT:
                invoice.status = InvoiceStatus.VIEWED
            invoice.updated_at = datetime.utcnow()
        
        return True
    
    async def cancel_invoice(
        self,
        invoice_id: str,
        reason: Optional[str] = None
    ) -> bool:
        """Cancel an invoice."""
        invoice = self.invoices.get(invoice_id)
        if not invoice or invoice.status in [InvoiceStatus.PAID, InvoiceStatus.CANCELLED]:
            return False
        
        invoice.status = InvoiceStatus.CANCELLED
        if reason:
            invoice.notes = f"Cancelled: {reason}"
        invoice.updated_at = datetime.utcnow()
        
        return True
    
    # Payments
    async def record_payment(
        self,
        invoice_id: str,
        amount: Decimal,
        method: PaymentMethod = PaymentMethod.CREDIT_CARD,
        reference_number: Optional[str] = None,
        transaction_id: Optional[str] = None,
        notes: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> Optional[Payment]:
        """Record a payment."""
        invoice = self.invoices.get(invoice_id)
        if not invoice or invoice.status in [InvoiceStatus.PAID, InvoiceStatus.CANCELLED]:
            return None
        
        payment = Payment(
            id=str(uuid.uuid4()),
            invoice_id=invoice_id,
            amount=amount,
            method=method,
            reference_number=reference_number,
            transaction_id=transaction_id,
            notes=notes,
            created_by=created_by,
        )
        
        invoice.payments.append(payment)
        invoice.amount_paid += amount
        
        if invoice.amount_paid >= invoice.total:
            invoice.status = InvoiceStatus.PAID
            invoice.paid_date = datetime.utcnow()
        else:
            invoice.status = InvoiceStatus.PARTIAL
        
        invoice.updated_at = datetime.utcnow()
        
        return payment
    
    async def refund_payment(
        self,
        invoice_id: str,
        payment_id: str,
        amount: Optional[Decimal] = None
    ) -> bool:
        """Refund a payment."""
        invoice = self.invoices.get(invoice_id)
        if not invoice:
            return False
        
        payment = next((p for p in invoice.payments if p.id == payment_id), None)
        if not payment or payment.is_refunded:
            return False
        
        refund_amount = amount or payment.amount
        payment.is_refunded = True
        payment.refund_amount = refund_amount
        payment.refund_date = datetime.utcnow()
        
        invoice.amount_paid -= refund_amount
        if invoice.amount_paid <= Decimal("0"):
            invoice.status = InvoiceStatus.REFUNDED
        else:
            invoice.status = InvoiceStatus.PARTIAL
        
        invoice.updated_at = datetime.utcnow()
        
        return True
    
    # Reminders
    async def send_reminder(self, invoice_id: str) -> bool:
        """Send payment reminder."""
        invoice = self.invoices.get(invoice_id)
        if not invoice or invoice.status in [InvoiceStatus.PAID, InvoiceStatus.CANCELLED]:
            return False
        
        invoice.reminder_count += 1
        invoice.last_reminder_at = datetime.utcnow()
        invoice.updated_at = datetime.utcnow()
        
        # In real implementation, send reminder email
        return True
    
    # Templates
    async def create_template(
        self,
        name: str,
        **kwargs
    ) -> InvoiceTemplate:
        """Create an invoice template."""
        template = InvoiceTemplate(
            id=str(uuid.uuid4()),
            name=name,
            **kwargs
        )
        
        self.templates[template.id] = template
        return template
    
    async def list_templates(self) -> list[InvoiceTemplate]:
        """List templates."""
        return list(self.templates.values())
    
    # Analytics
    async def get_invoice_stats(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> dict[str, Any]:
        """Get invoice statistics."""
        invoices = list(self.invoices.values())
        
        if from_date:
            invoices = [i for i in invoices if i.issue_date >= from_date]
        if to_date:
            invoices = [i for i in invoices if i.issue_date <= to_date]
        
        total_invoiced = sum(i.total for i in invoices)
        total_collected = sum(i.amount_paid for i in invoices)
        total_outstanding = total_invoiced - total_collected
        
        status_counts = {}
        for invoice in invoices:
            status_counts[invoice.status.value] = status_counts.get(invoice.status.value, 0) + 1
        
        overdue = [i for i in invoices if i.is_overdue]
        overdue_amount = sum(i.balance_due for i in overdue)
        
        return {
            "total_invoices": len(invoices),
            "total_invoiced": float(total_invoiced),
            "total_collected": float(total_collected),
            "total_outstanding": float(total_outstanding),
            "overdue_count": len(overdue),
            "overdue_amount": float(overdue_amount),
            "status_breakdown": status_counts,
            "collection_rate": float(total_collected / total_invoiced * 100) if total_invoiced > 0 else 0,
        }
    
    # Create from quote
    async def create_from_quote(
        self,
        quote_id: str,
        quote_data: dict[str, Any]
    ) -> Invoice:
        """Create invoice from a quote."""
        invoice = await self.create_invoice(
            customer_id=quote_data.get("customer_id", ""),
            customer_name=quote_data.get("customer_name", ""),
            customer_email=quote_data.get("customer_email"),
            quote_id=quote_id,
        )
        
        # Copy items
        for item_data in quote_data.get("items", []):
            await self.add_item(
                invoice_id=invoice.id,
                description=item_data.get("description", ""),
                quantity=Decimal(str(item_data.get("quantity", 1))),
                unit_price=Decimal(str(item_data.get("unit_price", 0))),
                discount_percent=Decimal(str(item_data.get("discount_percent", 0))),
                tax_rate=Decimal(str(item_data.get("tax_rate", 0))),
            )
        
        return invoice


# Singleton instance
_invoice_service: Optional[InvoiceService] = None


def get_invoice_service() -> InvoiceService:
    """Get invoice service singleton."""
    global _invoice_service
    if _invoice_service is None:
        _invoice_service = InvoiceService()
    return _invoice_service
