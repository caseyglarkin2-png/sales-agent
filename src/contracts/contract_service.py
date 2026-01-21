"""
Contract Service - Contract Lifecycle Management
================================================
Handles contracts, templates, clauses, and signatures.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
import uuid


class ContractStatus(str, Enum):
    """Contract status."""
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    SENT = "sent"
    VIEWED = "viewed"
    SIGNED = "signed"
    COUNTERSIGNED = "countersigned"
    ACTIVE = "active"
    EXPIRED = "expired"
    TERMINATED = "terminated"
    RENEWED = "renewed"


class ContractType(str, Enum):
    """Contract type."""
    MSA = "msa"  # Master Service Agreement
    SOW = "sow"  # Statement of Work
    NDA = "nda"  # Non-Disclosure Agreement
    SLA = "sla"  # Service Level Agreement
    SUBSCRIPTION = "subscription"
    LICENSE = "license"
    AMENDMENT = "amendment"
    ADDENDUM = "addendum"
    CUSTOM = "custom"


class ClauseType(str, Enum):
    """Clause type."""
    STANDARD = "standard"
    OPTIONAL = "optional"
    NEGOTIABLE = "negotiable"
    REQUIRED = "required"


@dataclass
class ContractClause:
    """A contract clause."""
    id: str
    name: str
    title: str
    content: str
    clause_type: ClauseType = ClauseType.STANDARD
    category: str = "general"
    is_active: bool = True
    version: int = 1
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ContractTemplate:
    """A contract template."""
    id: str
    name: str
    description: str
    contract_type: ContractType
    
    # Content
    content: str = ""  # HTML/Markdown template
    clauses: list[str] = field(default_factory=list)  # Clause IDs
    
    # Variables
    variables: list[str] = field(default_factory=list)  # {{variable}} placeholders
    
    # Settings
    requires_countersign: bool = True
    expiration_days: int = 30  # Days until signature link expires
    
    # Metadata
    is_active: bool = True
    version: int = 1
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Signatory:
    """A contract signatory."""
    id: str
    name: str
    email: str
    title: Optional[str] = None
    company: Optional[str] = None
    order: int = 1  # Signing order
    
    # Signature
    signed: bool = False
    signed_at: Optional[datetime] = None
    signature_ip: Optional[str] = None
    signature_data: Optional[str] = None  # Base64 signature image


@dataclass
class Contract:
    """A contract."""
    id: str
    name: str
    contract_type: ContractType
    
    # Related entities
    account_id: Optional[str] = None
    deal_id: Optional[str] = None
    quote_id: Optional[str] = None
    owner_id: Optional[str] = None
    
    # Template
    template_id: Optional[str] = None
    
    # Content
    content: str = ""
    variables: dict[str, Any] = field(default_factory=dict)
    
    # Terms
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    value: float = 0.0
    currency: str = "USD"
    
    # Auto-renewal
    auto_renew: bool = False
    renewal_term_months: int = 12
    renewal_notice_days: int = 30
    
    # Signatories
    signatories: list[Signatory] = field(default_factory=list)
    requires_countersign: bool = True
    
    # Status
    status: ContractStatus = ContractStatus.DRAFT
    
    # Timestamps
    sent_at: Optional[datetime] = None
    viewed_at: Optional[datetime] = None
    fully_signed_at: Optional[datetime] = None
    activated_at: Optional[datetime] = None
    terminated_at: Optional[datetime] = None
    
    # Approval
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    
    # Versioning
    version: int = 1
    parent_id: Optional[str] = None  # For amendments/renewals
    
    # Notes
    notes: str = ""
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ContractEvent:
    """A contract lifecycle event."""
    id: str
    contract_id: str
    event_type: str
    description: str
    user_id: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


class ContractService:
    """Service for contract management."""
    
    def __init__(self):
        self.contracts: dict[str, Contract] = {}
        self.templates: dict[str, ContractTemplate] = {}
        self.clauses: dict[str, ContractClause] = {}
        self.events: dict[str, list[ContractEvent]] = {}
        self._init_sample_data()
    
    def _init_sample_data(self) -> None:
        """Initialize sample templates and clauses."""
        # Standard clauses
        clauses = [
            ContractClause(
                id="clause-payment",
                name="payment_terms",
                title="Payment Terms",
                content="Payment is due within {{payment_days}} days of invoice date.",
                clause_type=ClauseType.STANDARD,
                category="financial",
            ),
            ContractClause(
                id="clause-termination",
                name="termination",
                title="Termination",
                content="Either party may terminate this agreement with {{notice_days}} days written notice.",
                clause_type=ClauseType.NEGOTIABLE,
                category="legal",
            ),
            ContractClause(
                id="clause-confidentiality",
                name="confidentiality",
                title="Confidentiality",
                content="Both parties agree to keep all proprietary information confidential for a period of {{confidentiality_years}} years.",
                clause_type=ClauseType.REQUIRED,
                category="legal",
            ),
        ]
        
        for clause in clauses:
            self.clauses[clause.id] = clause
        
        # Standard templates
        msa = ContractTemplate(
            id="tpl-msa",
            name="Master Service Agreement",
            description="Standard MSA for enterprise customers",
            contract_type=ContractType.MSA,
            content="<h1>Master Service Agreement</h1><p>This agreement...</p>",
            clauses=["clause-payment", "clause-termination", "clause-confidentiality"],
            variables=["company_name", "address", "payment_days", "notice_days"],
        )
        
        nda = ContractTemplate(
            id="tpl-nda",
            name="Non-Disclosure Agreement",
            description="Standard mutual NDA",
            contract_type=ContractType.NDA,
            content="<h1>Non-Disclosure Agreement</h1><p>This NDA...</p>",
            clauses=["clause-confidentiality"],
            variables=["company_name", "confidentiality_years"],
        )
        
        self.templates[msa.id] = msa
        self.templates[nda.id] = nda
    
    # Clause CRUD
    async def create_clause(
        self,
        name: str,
        title: str,
        content: str,
        clause_type: ClauseType = ClauseType.STANDARD,
        category: str = "general"
    ) -> ContractClause:
        """Create a clause."""
        clause = ContractClause(
            id=str(uuid.uuid4()),
            name=name,
            title=title,
            content=content,
            clause_type=clause_type,
            category=category,
        )
        self.clauses[clause.id] = clause
        return clause
    
    async def get_clause(self, clause_id: str) -> Optional[ContractClause]:
        """Get a clause by ID."""
        return self.clauses.get(clause_id)
    
    async def list_clauses(
        self,
        category: Optional[str] = None,
        clause_type: Optional[ClauseType] = None
    ) -> list[ContractClause]:
        """List clauses."""
        clauses = list(self.clauses.values())
        
        if category:
            clauses = [c for c in clauses if c.category == category]
        if clause_type:
            clauses = [c for c in clauses if c.clause_type == clause_type]
        
        return [c for c in clauses if c.is_active]
    
    # Template CRUD
    async def create_template(
        self,
        name: str,
        description: str,
        contract_type: ContractType,
        content: str = "",
        clauses: list[str] = None,
        variables: list[str] = None,
        **kwargs
    ) -> ContractTemplate:
        """Create a template."""
        template = ContractTemplate(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            contract_type=contract_type,
            content=content,
            clauses=clauses or [],
            variables=variables or [],
            **kwargs
        )
        self.templates[template.id] = template
        return template
    
    async def get_template(self, template_id: str) -> Optional[ContractTemplate]:
        """Get a template by ID."""
        return self.templates.get(template_id)
    
    async def update_template(
        self,
        template_id: str,
        updates: dict[str, Any]
    ) -> Optional[ContractTemplate]:
        """Update a template."""
        template = self.templates.get(template_id)
        if not template:
            return None
        
        for key, value in updates.items():
            if hasattr(template, key):
                setattr(template, key, value)
        
        template.version += 1
        template.updated_at = datetime.utcnow()
        return template
    
    async def list_templates(
        self,
        contract_type: Optional[ContractType] = None,
        active_only: bool = True
    ) -> list[ContractTemplate]:
        """List templates."""
        templates = list(self.templates.values())
        
        if contract_type:
            templates = [t for t in templates if t.contract_type == contract_type]
        if active_only:
            templates = [t for t in templates if t.is_active]
        
        templates.sort(key=lambda t: t.name)
        return templates
    
    # Contract CRUD
    async def create_contract(
        self,
        name: str,
        contract_type: ContractType,
        template_id: Optional[str] = None,
        account_id: Optional[str] = None,
        deal_id: Optional[str] = None,
        owner_id: Optional[str] = None,
        variables: dict[str, Any] = None,
        **kwargs
    ) -> Contract:
        """Create a contract."""
        contract_id = str(uuid.uuid4())
        
        content = ""
        if template_id:
            template = self.templates.get(template_id)
            if template:
                content = template.content
                # Substitute variables
                if variables:
                    for var, value in variables.items():
                        content = content.replace(f"{{{{{var}}}}}", str(value))
        
        contract = Contract(
            id=contract_id,
            name=name,
            contract_type=contract_type,
            template_id=template_id,
            account_id=account_id,
            deal_id=deal_id,
            owner_id=owner_id,
            content=content,
            variables=variables or {},
            **kwargs
        )
        
        self.contracts[contract_id] = contract
        self.events[contract_id] = []
        
        await self._log_event(contract_id, "created", "Contract created")
        
        return contract
    
    async def get_contract(self, contract_id: str) -> Optional[Contract]:
        """Get a contract by ID."""
        return self.contracts.get(contract_id)
    
    async def update_contract(
        self,
        contract_id: str,
        updates: dict[str, Any]
    ) -> Optional[Contract]:
        """Update a contract."""
        contract = self.contracts.get(contract_id)
        if not contract:
            return None
        
        # Only allow updates in draft status
        if contract.status not in [ContractStatus.DRAFT, ContractStatus.PENDING_REVIEW]:
            return None
        
        for key, value in updates.items():
            if hasattr(contract, key):
                setattr(contract, key, value)
        
        contract.updated_at = datetime.utcnow()
        await self._log_event(contract_id, "updated", "Contract updated")
        
        return contract
    
    async def delete_contract(self, contract_id: str) -> bool:
        """Delete a contract (only if draft)."""
        contract = self.contracts.get(contract_id)
        if not contract or contract.status != ContractStatus.DRAFT:
            return False
        
        del self.contracts[contract_id]
        return True
    
    async def list_contracts(
        self,
        account_id: Optional[str] = None,
        deal_id: Optional[str] = None,
        owner_id: Optional[str] = None,
        status: Optional[ContractStatus] = None,
        contract_type: Optional[ContractType] = None,
        expiring_within_days: Optional[int] = None,
        limit: int = 100
    ) -> list[Contract]:
        """List contracts with filters."""
        contracts = list(self.contracts.values())
        
        if account_id:
            contracts = [c for c in contracts if c.account_id == account_id]
        if deal_id:
            contracts = [c for c in contracts if c.deal_id == deal_id]
        if owner_id:
            contracts = [c for c in contracts if c.owner_id == owner_id]
        if status:
            contracts = [c for c in contracts if c.status == status]
        if contract_type:
            contracts = [c for c in contracts if c.contract_type == contract_type]
        if expiring_within_days:
            cutoff = datetime.utcnow()
            from datetime import timedelta
            contracts = [
                c for c in contracts
                if c.end_date and c.end_date <= cutoff + timedelta(days=expiring_within_days)
            ]
        
        contracts.sort(key=lambda c: c.created_at, reverse=True)
        return contracts[:limit]
    
    # Signatory management
    async def add_signatory(
        self,
        contract_id: str,
        name: str,
        email: str,
        title: Optional[str] = None,
        company: Optional[str] = None,
        order: int = 1
    ) -> Optional[Signatory]:
        """Add a signatory to a contract."""
        contract = self.contracts.get(contract_id)
        if not contract:
            return None
        
        signatory = Signatory(
            id=str(uuid.uuid4()),
            name=name,
            email=email,
            title=title,
            company=company,
            order=order,
        )
        
        contract.signatories.append(signatory)
        contract.signatories.sort(key=lambda s: s.order)
        contract.updated_at = datetime.utcnow()
        
        return signatory
    
    async def remove_signatory(
        self,
        contract_id: str,
        signatory_id: str
    ) -> bool:
        """Remove a signatory."""
        contract = self.contracts.get(contract_id)
        if not contract:
            return False
        
        original = len(contract.signatories)
        contract.signatories = [s for s in contract.signatories if s.id != signatory_id]
        
        return len(contract.signatories) < original
    
    # Workflow
    async def submit_for_review(self, contract_id: str) -> bool:
        """Submit contract for review."""
        contract = self.contracts.get(contract_id)
        if not contract or contract.status != ContractStatus.DRAFT:
            return False
        
        contract.status = ContractStatus.PENDING_REVIEW
        contract.updated_at = datetime.utcnow()
        await self._log_event(contract_id, "submitted", "Contract submitted for review")
        
        return True
    
    async def approve_contract(
        self,
        contract_id: str,
        approver_id: str
    ) -> bool:
        """Approve a contract."""
        contract = self.contracts.get(contract_id)
        if not contract or contract.status != ContractStatus.PENDING_REVIEW:
            return False
        
        contract.status = ContractStatus.APPROVED
        contract.approved_by = approver_id
        contract.approved_at = datetime.utcnow()
        contract.updated_at = datetime.utcnow()
        await self._log_event(contract_id, "approved", f"Contract approved by {approver_id}")
        
        return True
    
    async def send_for_signature(self, contract_id: str) -> bool:
        """Send contract for signature."""
        contract = self.contracts.get(contract_id)
        if not contract or contract.status != ContractStatus.APPROVED:
            return False
        
        if not contract.signatories:
            return False
        
        contract.status = ContractStatus.SENT
        contract.sent_at = datetime.utcnow()
        contract.updated_at = datetime.utcnow()
        await self._log_event(contract_id, "sent", "Contract sent for signature")
        
        # In real implementation, send email to first signatory
        return True
    
    async def record_view(self, contract_id: str, signatory_id: str) -> bool:
        """Record that a signatory viewed the contract."""
        contract = self.contracts.get(contract_id)
        if not contract:
            return False
        
        if contract.status == ContractStatus.SENT:
            contract.status = ContractStatus.VIEWED
            contract.viewed_at = datetime.utcnow()
        
        await self._log_event(contract_id, "viewed", f"Contract viewed by {signatory_id}")
        return True
    
    async def sign_contract(
        self,
        contract_id: str,
        signatory_id: str,
        signature_data: str,
        ip_address: Optional[str] = None
    ) -> bool:
        """Sign a contract."""
        contract = self.contracts.get(contract_id)
        if not contract or contract.status not in [ContractStatus.SENT, ContractStatus.VIEWED, ContractStatus.SIGNED]:
            return False
        
        # Find signatory
        signatory = None
        for s in contract.signatories:
            if s.id == signatory_id:
                signatory = s
                break
        
        if not signatory or signatory.signed:
            return False
        
        # Record signature
        signatory.signed = True
        signatory.signed_at = datetime.utcnow()
        signatory.signature_ip = ip_address
        signatory.signature_data = signature_data
        
        await self._log_event(contract_id, "signed", f"Contract signed by {signatory.name}")
        
        # Check if all signatories have signed
        all_signed = all(s.signed for s in contract.signatories)
        
        if all_signed:
            if contract.requires_countersign:
                contract.status = ContractStatus.SIGNED
            else:
                contract.status = ContractStatus.ACTIVE
                contract.fully_signed_at = datetime.utcnow()
                contract.activated_at = datetime.utcnow()
        else:
            contract.status = ContractStatus.SIGNED
        
        contract.updated_at = datetime.utcnow()
        return True
    
    async def countersign_contract(
        self,
        contract_id: str,
        signer_id: str,
        signature_data: str
    ) -> bool:
        """Countersign a contract (internal signature)."""
        contract = self.contracts.get(contract_id)
        if not contract or contract.status != ContractStatus.SIGNED:
            return False
        
        contract.status = ContractStatus.ACTIVE
        contract.fully_signed_at = datetime.utcnow()
        contract.activated_at = datetime.utcnow()
        contract.updated_at = datetime.utcnow()
        await self._log_event(contract_id, "countersigned", f"Contract countersigned by {signer_id}")
        
        return True
    
    async def terminate_contract(
        self,
        contract_id: str,
        reason: str
    ) -> bool:
        """Terminate a contract."""
        contract = self.contracts.get(contract_id)
        if not contract or contract.status != ContractStatus.ACTIVE:
            return False
        
        contract.status = ContractStatus.TERMINATED
        contract.terminated_at = datetime.utcnow()
        contract.notes = reason
        contract.updated_at = datetime.utcnow()
        await self._log_event(contract_id, "terminated", f"Contract terminated: {reason}")
        
        return True
    
    async def renew_contract(
        self,
        contract_id: str,
        new_end_date: datetime,
        new_value: Optional[float] = None
    ) -> Optional[Contract]:
        """Renew a contract."""
        contract = self.contracts.get(contract_id)
        if not contract or contract.status not in [ContractStatus.ACTIVE, ContractStatus.EXPIRED]:
            return None
        
        # Create renewal contract
        renewal = await self.create_contract(
            name=f"{contract.name} - Renewal",
            contract_type=contract.contract_type,
            template_id=contract.template_id,
            account_id=contract.account_id,
            deal_id=contract.deal_id,
            owner_id=contract.owner_id,
            variables=contract.variables,
            start_date=contract.end_date or datetime.utcnow(),
            end_date=new_end_date,
            value=new_value or contract.value,
            auto_renew=contract.auto_renew,
        )
        
        renewal.parent_id = contract.id
        
        # Mark original as renewed
        contract.status = ContractStatus.RENEWED
        contract.updated_at = datetime.utcnow()
        await self._log_event(contract_id, "renewed", f"Contract renewed: {renewal.id}")
        
        return renewal
    
    # Events
    async def _log_event(
        self,
        contract_id: str,
        event_type: str,
        description: str,
        user_id: Optional[str] = None,
        metadata: dict[str, Any] = None
    ) -> None:
        """Log a contract event."""
        event = ContractEvent(
            id=str(uuid.uuid4()),
            contract_id=contract_id,
            event_type=event_type,
            description=description,
            user_id=user_id,
            metadata=metadata or {},
        )
        
        if contract_id not in self.events:
            self.events[contract_id] = []
        
        self.events[contract_id].append(event)
    
    async def get_events(self, contract_id: str) -> list[ContractEvent]:
        """Get events for a contract."""
        return self.events.get(contract_id, [])
    
    # Analytics
    async def get_contract_analytics(
        self,
        owner_id: Optional[str] = None,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None
    ) -> dict[str, Any]:
        """Get contract analytics."""
        contracts = await self.list_contracts(owner_id=owner_id, limit=1000)
        
        if period_start:
            contracts = [c for c in contracts if c.created_at >= period_start]
        if period_end:
            contracts = [c for c in contracts if c.created_at <= period_end]
        
        by_status = {}
        by_type = {}
        total_value = 0
        active_value = 0
        
        for c in contracts:
            by_status[c.status.value] = by_status.get(c.status.value, 0) + 1
            by_type[c.contract_type.value] = by_type.get(c.contract_type.value, 0) + 1
            total_value += c.value
            if c.status == ContractStatus.ACTIVE:
                active_value += c.value
        
        return {
            "total_contracts": len(contracts),
            "by_status": by_status,
            "by_type": by_type,
            "total_value": total_value,
            "active_value": active_value,
            "avg_value": total_value / len(contracts) if contracts else 0,
        }


# Singleton instance
_contract_service: Optional[ContractService] = None


def get_contract_service() -> ContractService:
    """Get contract service singleton."""
    global _contract_service
    if _contract_service is None:
        _contract_service = ContractService()
    return _contract_service
