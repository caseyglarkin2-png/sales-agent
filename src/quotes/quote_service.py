"""
Quote Service - Quote and Proposal Management
==============================================
Handles quote creation, pricing, and approval workflows.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional
import uuid


class QuoteStatus(str, Enum):
    """Quote status values."""
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SENT = "sent"
    VIEWED = "viewed"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"
    REVISED = "revised"


class DiscountType(str, Enum):
    """Discount type values."""
    PERCENTAGE = "percentage"
    FIXED = "fixed"
    VOLUME = "volume"


class PaymentTerms(str, Enum):
    """Payment terms options."""
    DUE_ON_RECEIPT = "due_on_receipt"
    NET_15 = "net_15"
    NET_30 = "net_30"
    NET_45 = "net_45"
    NET_60 = "net_60"
    NET_90 = "net_90"
    CUSTOM = "custom"


class Currency(str, Enum):
    """Supported currencies."""
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    CAD = "CAD"
    AUD = "AUD"
    JPY = "JPY"


@dataclass
class QuoteItem:
    """A line item in a quote."""
    id: str
    product_id: Optional[str]
    name: str
    description: str
    quantity: int
    unit_price: float
    discount_type: Optional[DiscountType] = None
    discount_value: float = 0.0
    tax_rate: float = 0.0
    subtotal: float = 0.0
    total: float = 0.0
    sku: Optional[str] = None
    unit: str = "unit"
    is_optional: bool = False
    notes: Optional[str] = None
    
    def calculate_totals(self) -> None:
        """Calculate line item totals."""
        self.subtotal = self.quantity * self.unit_price
        
        # Apply discount
        if self.discount_type == DiscountType.PERCENTAGE:
            discount = self.subtotal * (self.discount_value / 100)
        elif self.discount_type == DiscountType.FIXED:
            discount = self.discount_value
        else:
            discount = 0.0
        
        after_discount = self.subtotal - discount
        
        # Apply tax
        tax = after_discount * (self.tax_rate / 100)
        
        self.total = after_discount + tax


@dataclass
class QuoteTemplate:
    """A reusable quote template."""
    id: str
    name: str
    description: str
    content: dict[str, Any]
    items: list[dict[str, Any]] = field(default_factory=list)
    terms_and_conditions: str = ""
    header_html: Optional[str] = None
    footer_html: Optional[str] = None
    css_styles: Optional[str] = None
    is_default: bool = False
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Quote:
    """A sales quote/proposal."""
    id: str
    quote_number: str
    title: str
    deal_id: Optional[str]
    contact_id: Optional[str]
    company_id: Optional[str]
    owner_id: str
    
    # Content
    items: list[QuoteItem] = field(default_factory=list)
    introduction: str = ""
    terms_and_conditions: str = ""
    notes: str = ""
    
    # Pricing
    currency: Currency = Currency.USD
    subtotal: float = 0.0
    discount_type: Optional[DiscountType] = None
    discount_value: float = 0.0
    discount_amount: float = 0.0
    tax_rate: float = 0.0
    tax_amount: float = 0.0
    shipping_amount: float = 0.0
    total: float = 0.0
    
    # Payment
    payment_terms: PaymentTerms = PaymentTerms.NET_30
    payment_terms_custom: Optional[str] = None
    deposit_required: bool = False
    deposit_percentage: float = 0.0
    deposit_amount: float = 0.0
    
    # Status
    status: QuoteStatus = QuoteStatus.DRAFT
    valid_until: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    viewed_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    declined_at: Optional[datetime] = None
    declined_reason: Optional[str] = None
    
    # Approval workflow
    requires_approval: bool = False
    approval_requested_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    
    # Template
    template_id: Optional[str] = None
    
    # Signature
    signature_required: bool = False
    signed_at: Optional[datetime] = None
    signer_name: Optional[str] = None
    signer_email: Optional[str] = None
    signature_ip: Optional[str] = None
    
    # Revisions
    version: int = 1
    parent_quote_id: Optional[str] = None
    revision_notes: Optional[str] = None
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def calculate_totals(self) -> None:
        """Calculate all quote totals."""
        # Calculate item totals
        for item in self.items:
            if not item.is_optional:
                item.calculate_totals()
        
        # Sum non-optional items
        self.subtotal = sum(item.total for item in self.items if not item.is_optional)
        
        # Apply quote-level discount
        if self.discount_type == DiscountType.PERCENTAGE:
            self.discount_amount = self.subtotal * (self.discount_value / 100)
        elif self.discount_type == DiscountType.FIXED:
            self.discount_amount = self.discount_value
        else:
            self.discount_amount = 0.0
        
        after_discount = self.subtotal - self.discount_amount
        
        # Apply tax
        self.tax_amount = after_discount * (self.tax_rate / 100)
        
        # Add shipping
        self.total = after_discount + self.tax_amount + self.shipping_amount
        
        # Calculate deposit
        if self.deposit_required:
            if self.deposit_percentage > 0:
                self.deposit_amount = self.total * (self.deposit_percentage / 100)


class QuoteService:
    """Service for managing quotes and proposals."""
    
    def __init__(self):
        self.quotes: dict[str, Quote] = {}
        self.templates: dict[str, QuoteTemplate] = {}
        self.quote_counter: int = 1000
        self._init_default_template()
    
    def _init_default_template(self) -> None:
        """Initialize default quote template."""
        template = QuoteTemplate(
            id="default",
            name="Standard Quote",
            description="Default quote template",
            content={
                "show_logo": True,
                "show_company_info": True,
                "show_contact_info": True,
                "show_item_descriptions": True,
                "show_optional_items": True,
                "show_terms": True,
            },
            terms_and_conditions="""
1. Quote valid for 30 days from issue date.
2. Prices are exclusive of applicable taxes unless stated.
3. Payment due per agreed payment terms.
4. Subject to our standard terms and conditions.
            """.strip(),
            is_default=True,
        )
        self.templates[template.id] = template
    
    def _generate_quote_number(self) -> str:
        """Generate unique quote number."""
        self.quote_counter += 1
        return f"Q-{self.quote_counter}"
    
    # Quote CRUD operations
    async def create_quote(
        self,
        title: str,
        owner_id: str,
        deal_id: Optional[str] = None,
        contact_id: Optional[str] = None,
        company_id: Optional[str] = None,
        template_id: Optional[str] = None,
        valid_days: int = 30,
        **kwargs
    ) -> Quote:
        """Create a new quote."""
        quote_id = str(uuid.uuid4())
        
        quote = Quote(
            id=quote_id,
            quote_number=self._generate_quote_number(),
            title=title,
            deal_id=deal_id,
            contact_id=contact_id,
            company_id=company_id,
            owner_id=owner_id,
            template_id=template_id or "default",
            valid_until=datetime.utcnow() + timedelta(days=valid_days),
            **kwargs
        )
        
        # Apply template if specified
        if template_id and template_id in self.templates:
            template = self.templates[template_id]
            quote.terms_and_conditions = template.terms_and_conditions
        
        self.quotes[quote_id] = quote
        return quote
    
    async def get_quote(self, quote_id: str) -> Optional[Quote]:
        """Get a quote by ID."""
        return self.quotes.get(quote_id)
    
    async def get_by_number(self, quote_number: str) -> Optional[Quote]:
        """Get quote by quote number."""
        for quote in self.quotes.values():
            if quote.quote_number == quote_number:
                return quote
        return None
    
    async def update_quote(
        self,
        quote_id: str,
        updates: dict[str, Any]
    ) -> Optional[Quote]:
        """Update a quote."""
        quote = self.quotes.get(quote_id)
        if not quote:
            return None
        
        # Don't allow editing accepted/declined quotes
        if quote.status in [QuoteStatus.ACCEPTED, QuoteStatus.DECLINED]:
            return None
        
        for key, value in updates.items():
            if hasattr(quote, key):
                setattr(quote, key, value)
        
        quote.updated_at = datetime.utcnow()
        quote.calculate_totals()
        
        return quote
    
    async def delete_quote(self, quote_id: str) -> bool:
        """Delete a quote."""
        if quote_id in self.quotes:
            del self.quotes[quote_id]
            return True
        return False
    
    # Line item management
    async def add_item(
        self,
        quote_id: str,
        name: str,
        quantity: int,
        unit_price: float,
        **kwargs
    ) -> Optional[QuoteItem]:
        """Add a line item to a quote."""
        quote = self.quotes.get(quote_id)
        if not quote:
            return None
        
        item = QuoteItem(
            id=str(uuid.uuid4()),
            name=name,
            description=kwargs.get("description", ""),
            quantity=quantity,
            unit_price=unit_price,
            **{k: v for k, v in kwargs.items() if k != "description"}
        )
        item.calculate_totals()
        
        quote.items.append(item)
        quote.calculate_totals()
        quote.updated_at = datetime.utcnow()
        
        return item
    
    async def update_item(
        self,
        quote_id: str,
        item_id: str,
        updates: dict[str, Any]
    ) -> Optional[QuoteItem]:
        """Update a line item."""
        quote = self.quotes.get(quote_id)
        if not quote:
            return None
        
        for item in quote.items:
            if item.id == item_id:
                for key, value in updates.items():
                    if hasattr(item, key):
                        setattr(item, key, value)
                item.calculate_totals()
                quote.calculate_totals()
                quote.updated_at = datetime.utcnow()
                return item
        
        return None
    
    async def remove_item(self, quote_id: str, item_id: str) -> bool:
        """Remove a line item."""
        quote = self.quotes.get(quote_id)
        if not quote:
            return False
        
        original_count = len(quote.items)
        quote.items = [item for item in quote.items if item.id != item_id]
        
        if len(quote.items) < original_count:
            quote.calculate_totals()
            quote.updated_at = datetime.utcnow()
            return True
        
        return False
    
    async def reorder_items(
        self,
        quote_id: str,
        item_order: list[str]
    ) -> bool:
        """Reorder line items."""
        quote = self.quotes.get(quote_id)
        if not quote:
            return False
        
        # Create item map
        item_map = {item.id: item for item in quote.items}
        
        # Reorder
        new_items = []
        for item_id in item_order:
            if item_id in item_map:
                new_items.append(item_map[item_id])
        
        # Add any items not in the order list
        for item in quote.items:
            if item.id not in item_order:
                new_items.append(item)
        
        quote.items = new_items
        quote.updated_at = datetime.utcnow()
        
        return True
    
    # Status workflows
    async def submit_for_approval(
        self,
        quote_id: str,
        notes: Optional[str] = None
    ) -> bool:
        """Submit quote for approval."""
        quote = self.quotes.get(quote_id)
        if not quote or quote.status != QuoteStatus.DRAFT:
            return False
        
        quote.status = QuoteStatus.PENDING_APPROVAL
        quote.approval_requested_at = datetime.utcnow()
        quote.revision_notes = notes
        quote.updated_at = datetime.utcnow()
        
        return True
    
    async def approve_quote(
        self,
        quote_id: str,
        approver_id: str
    ) -> bool:
        """Approve a quote."""
        quote = self.quotes.get(quote_id)
        if not quote or quote.status != QuoteStatus.PENDING_APPROVAL:
            return False
        
        quote.status = QuoteStatus.APPROVED
        quote.approved_by = approver_id
        quote.approved_at = datetime.utcnow()
        quote.updated_at = datetime.utcnow()
        
        return True
    
    async def reject_quote(
        self,
        quote_id: str,
        reason: str
    ) -> bool:
        """Reject a quote approval request."""
        quote = self.quotes.get(quote_id)
        if not quote or quote.status != QuoteStatus.PENDING_APPROVAL:
            return False
        
        quote.status = QuoteStatus.DRAFT
        quote.rejection_reason = reason
        quote.updated_at = datetime.utcnow()
        
        return True
    
    async def send_quote(
        self,
        quote_id: str,
        recipient_email: Optional[str] = None
    ) -> bool:
        """Mark quote as sent."""
        quote = self.quotes.get(quote_id)
        if not quote:
            return False
        
        # Must be approved if approval is required
        if quote.requires_approval and quote.status != QuoteStatus.APPROVED:
            return False
        
        quote.status = QuoteStatus.SENT
        quote.sent_at = datetime.utcnow()
        quote.updated_at = datetime.utcnow()
        
        return True
    
    async def mark_viewed(self, quote_id: str) -> bool:
        """Mark quote as viewed."""
        quote = self.quotes.get(quote_id)
        if not quote or quote.status not in [QuoteStatus.SENT, QuoteStatus.VIEWED]:
            return False
        
        quote.status = QuoteStatus.VIEWED
        if not quote.viewed_at:
            quote.viewed_at = datetime.utcnow()
        quote.updated_at = datetime.utcnow()
        
        return True
    
    async def accept_quote(
        self,
        quote_id: str,
        signer_name: Optional[str] = None,
        signer_email: Optional[str] = None,
        signature_ip: Optional[str] = None
    ) -> bool:
        """Accept/sign a quote."""
        quote = self.quotes.get(quote_id)
        if not quote or quote.status not in [QuoteStatus.SENT, QuoteStatus.VIEWED]:
            return False
        
        # Check if not expired
        if quote.valid_until and quote.valid_until < datetime.utcnow():
            quote.status = QuoteStatus.EXPIRED
            quote.updated_at = datetime.utcnow()
            return False
        
        quote.status = QuoteStatus.ACCEPTED
        quote.accepted_at = datetime.utcnow()
        
        if quote.signature_required:
            quote.signed_at = datetime.utcnow()
            quote.signer_name = signer_name
            quote.signer_email = signer_email
            quote.signature_ip = signature_ip
        
        quote.updated_at = datetime.utcnow()
        
        return True
    
    async def decline_quote(
        self,
        quote_id: str,
        reason: Optional[str] = None
    ) -> bool:
        """Decline a quote."""
        quote = self.quotes.get(quote_id)
        if not quote or quote.status not in [QuoteStatus.SENT, QuoteStatus.VIEWED]:
            return False
        
        quote.status = QuoteStatus.DECLINED
        quote.declined_at = datetime.utcnow()
        quote.declined_reason = reason
        quote.updated_at = datetime.utcnow()
        
        return True
    
    async def create_revision(
        self,
        quote_id: str,
        revision_notes: Optional[str] = None
    ) -> Optional[Quote]:
        """Create a new revision of a quote."""
        original = self.quotes.get(quote_id)
        if not original:
            return None
        
        # Create new quote based on original
        new_quote = Quote(
            id=str(uuid.uuid4()),
            quote_number=f"{original.quote_number}-R{original.version + 1}",
            title=original.title,
            deal_id=original.deal_id,
            contact_id=original.contact_id,
            company_id=original.company_id,
            owner_id=original.owner_id,
            items=original.items.copy(),
            introduction=original.introduction,
            terms_and_conditions=original.terms_and_conditions,
            notes=original.notes,
            currency=original.currency,
            payment_terms=original.payment_terms,
            requires_approval=original.requires_approval,
            signature_required=original.signature_required,
            template_id=original.template_id,
            version=original.version + 1,
            parent_quote_id=original.id,
            revision_notes=revision_notes,
            valid_until=datetime.utcnow() + timedelta(days=30),
        )
        
        new_quote.calculate_totals()
        
        # Mark original as revised
        original.status = QuoteStatus.REVISED
        original.updated_at = datetime.utcnow()
        
        self.quotes[new_quote.id] = new_quote
        
        return new_quote
    
    # List and search
    async def list_quotes(
        self,
        owner_id: Optional[str] = None,
        deal_id: Optional[str] = None,
        company_id: Optional[str] = None,
        contact_id: Optional[str] = None,
        status: Optional[QuoteStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> list[Quote]:
        """List quotes with filters."""
        quotes = list(self.quotes.values())
        
        if owner_id:
            quotes = [q for q in quotes if q.owner_id == owner_id]
        if deal_id:
            quotes = [q for q in quotes if q.deal_id == deal_id]
        if company_id:
            quotes = [q for q in quotes if q.company_id == company_id]
        if contact_id:
            quotes = [q for q in quotes if q.contact_id == contact_id]
        if status:
            quotes = [q for q in quotes if q.status == status]
        
        # Sort by created date
        quotes.sort(key=lambda q: q.created_at, reverse=True)
        
        return quotes[offset:offset + limit]
    
    async def get_quote_revisions(self, quote_id: str) -> list[Quote]:
        """Get all revisions of a quote."""
        quote = self.quotes.get(quote_id)
        if not quote:
            return []
        
        # Find root quote
        root_id = quote.parent_quote_id or quote.id
        while True:
            parent = self.quotes.get(root_id)
            if parent and parent.parent_quote_id:
                root_id = parent.parent_quote_id
            else:
                break
        
        # Find all quotes in chain
        revisions = [self.quotes[root_id]] if root_id in self.quotes else []
        
        for q in self.quotes.values():
            if q.parent_quote_id == root_id or (q.id != root_id and q.parent_quote_id and q.parent_quote_id in [r.id for r in revisions]):
                revisions.append(q)
        
        # Sort by version
        revisions.sort(key=lambda q: q.version)
        
        return revisions
    
    # Templates
    async def create_template(
        self,
        name: str,
        description: str,
        **kwargs
    ) -> QuoteTemplate:
        """Create a quote template."""
        template = QuoteTemplate(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            content=kwargs.get("content", {}),
            **{k: v for k, v in kwargs.items() if k != "content"}
        )
        self.templates[template.id] = template
        return template
    
    async def list_templates(self, active_only: bool = True) -> list[QuoteTemplate]:
        """List quote templates."""
        templates = list(self.templates.values())
        if active_only:
            templates = [t for t in templates if t.is_active]
        return templates
    
    async def get_template(self, template_id: str) -> Optional[QuoteTemplate]:
        """Get a template by ID."""
        return self.templates.get(template_id)
    
    # Analytics
    async def get_quote_stats(
        self,
        owner_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> dict[str, Any]:
        """Get quote statistics."""
        quotes = list(self.quotes.values())
        
        if owner_id:
            quotes = [q for q in quotes if q.owner_id == owner_id]
        if start_date:
            quotes = [q for q in quotes if q.created_at >= start_date]
        if end_date:
            quotes = [q for q in quotes if q.created_at <= end_date]
        
        total = len(quotes)
        by_status = {}
        for q in quotes:
            status = q.status.value
            by_status[status] = by_status.get(status, 0) + 1
        
        accepted = [q for q in quotes if q.status == QuoteStatus.ACCEPTED]
        declined = [q for q in quotes if q.status == QuoteStatus.DECLINED]
        
        total_value = sum(q.total for q in accepted)
        avg_value = total_value / len(accepted) if accepted else 0
        
        win_rate = len(accepted) / (len(accepted) + len(declined)) * 100 if (accepted or declined) else 0
        
        # Average time to accept
        accept_times = []
        for q in accepted:
            if q.sent_at and q.accepted_at:
                delta = (q.accepted_at - q.sent_at).total_seconds() / 3600  # hours
                accept_times.append(delta)
        
        avg_accept_time = sum(accept_times) / len(accept_times) if accept_times else 0
        
        return {
            "total_quotes": total,
            "by_status": by_status,
            "accepted_count": len(accepted),
            "declined_count": len(declined),
            "total_value": total_value,
            "average_value": avg_value,
            "win_rate": win_rate,
            "avg_time_to_accept_hours": avg_accept_time,
        }
    
    # PDF/Document generation (placeholder)
    async def generate_pdf(self, quote_id: str) -> Optional[bytes]:
        """Generate PDF for a quote."""
        quote = self.quotes.get(quote_id)
        if not quote:
            return None
        
        # In real implementation, use a PDF library
        # For now, return placeholder
        return b"PDF content placeholder"
    
    async def get_public_view_url(self, quote_id: str) -> Optional[str]:
        """Get public URL for quote viewing."""
        quote = self.quotes.get(quote_id)
        if not quote:
            return None
        
        # In real implementation, generate signed URL
        return f"/quotes/view/{quote_id}"


# Singleton instance
_quote_service: Optional[QuoteService] = None


def get_quote_service() -> QuoteService:
    """Get quote service singleton."""
    global _quote_service
    if _quote_service is None:
        _quote_service = QuoteService()
    return _quote_service
