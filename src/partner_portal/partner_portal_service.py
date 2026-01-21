"""
Partner Portal Service - Channel partner and reseller management
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from uuid import uuid4
import structlog

logger = structlog.get_logger()


class PartnerType(str, Enum):
    RESELLER = "reseller"
    REFERRAL = "referral"
    AFFILIATE = "affiliate"
    DISTRIBUTOR = "distributor"
    TECHNOLOGY = "technology"
    CONSULTING = "consulting"
    IMPLEMENTATION = "implementation"
    MSP = "msp"
    VAR = "var"
    ISV = "isv"


class PartnerTier(str, Enum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    DIAMOND = "diamond"


class PartnerStatus(str, Enum):
    PROSPECT = "prospect"
    PENDING = "pending"
    APPROVED = "approved"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    INACTIVE = "inactive"
    TERMINATED = "terminated"


class DealRegistrationStatus(str, Enum):
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    WON = "won"
    LOST = "lost"


@dataclass
class Partner:
    """Partner entity"""
    id: str
    name: str
    company: str
    partner_type: PartnerType
    tier: PartnerTier
    status: PartnerStatus
    contact_name: str
    contact_email: str
    contact_phone: Optional[str]
    address: Dict[str, str]
    website: Optional[str]
    specializations: List[str]
    certifications: List[Dict[str, Any]]
    commission_rate: float
    deal_registration_enabled: bool
    portal_access: bool
    onboarding_completed: bool
    contract_start: Optional[datetime]
    contract_end: Optional[datetime]
    total_revenue: float = 0.0
    total_deals: int = 0
    active_deals: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    tenant_id: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DealRegistration:
    """Partner deal registration"""
    id: str
    partner_id: str
    partner_name: str
    customer_name: str
    customer_contact: str
    customer_email: str
    customer_phone: Optional[str]
    opportunity_name: str
    opportunity_value: float
    product_interest: List[str]
    expected_close_date: datetime
    description: str
    status: DealRegistrationStatus
    expiration_date: datetime
    reviewer_id: Optional[str]
    review_notes: Optional[str]
    approved_at: Optional[datetime]
    rejected_at: Optional[datetime]
    rejection_reason: Optional[str]
    deal_id: Optional[str]  # Linked CRM deal
    commission_earned: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    tenant_id: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PartnerProgram:
    """Partner program configuration"""
    id: str
    name: str
    description: str
    partner_types: List[PartnerType]
    tiers: List[Dict[str, Any]]  # Tier requirements and benefits
    commission_structure: Dict[str, Any]
    deal_registration_rules: Dict[str, Any]
    training_requirements: List[Dict[str, Any]]
    certification_requirements: List[Dict[str, Any]]
    is_active: bool = True
    tenant_id: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PartnerResource:
    """Resource available to partners"""
    id: str
    title: str
    description: str
    resource_type: str  # document, video, training, template, etc.
    category: str
    file_url: Optional[str]
    external_url: Optional[str]
    access_tiers: List[PartnerTier]
    is_featured: bool
    view_count: int = 0
    download_count: int = 0
    tenant_id: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)


class PartnerPortalService:
    """Service for managing partner portal"""

    def __init__(self):
        self.partners: Dict[str, Partner] = {}
        self.deal_registrations: Dict[str, DealRegistration] = {}
        self.programs: Dict[str, PartnerProgram] = {}
        self.resources: Dict[str, PartnerResource] = {}
        self.partner_users: Dict[str, List[Dict[str, Any]]] = {}

    async def create_partner(
        self,
        tenant_id: str,
        name: str,
        company: str,
        partner_type: PartnerType,
        contact_name: str,
        contact_email: str,
        **kwargs
    ) -> Partner:
        """Create a new partner"""
        partner = Partner(
            id=str(uuid4()),
            name=name,
            company=company,
            partner_type=partner_type,
            tier=kwargs.get("tier", PartnerTier.BRONZE),
            status=PartnerStatus.PENDING,
            contact_name=contact_name,
            contact_email=contact_email,
            contact_phone=kwargs.get("contact_phone"),
            address=kwargs.get("address", {}),
            website=kwargs.get("website"),
            specializations=kwargs.get("specializations", []),
            certifications=kwargs.get("certifications", []),
            commission_rate=kwargs.get("commission_rate", 10.0),
            deal_registration_enabled=kwargs.get("deal_registration_enabled", True),
            portal_access=kwargs.get("portal_access", True),
            onboarding_completed=False,
            contract_start=kwargs.get("contract_start"),
            contract_end=kwargs.get("contract_end"),
            tenant_id=tenant_id
        )
        
        self.partners[partner.id] = partner
        self.partner_users[partner.id] = []
        
        logger.info("partner_created", partner_id=partner.id, company=company)
        return partner

    async def get_partner(self, partner_id: str) -> Optional[Partner]:
        """Get partner by ID"""
        return self.partners.get(partner_id)

    async def list_partners(
        self,
        tenant_id: str,
        partner_type: Optional[PartnerType] = None,
        tier: Optional[PartnerTier] = None,
        status: Optional[PartnerStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Partner]:
        """List partners"""
        partners = [p for p in self.partners.values() if p.tenant_id == tenant_id]
        
        if partner_type:
            partners = [p for p in partners if p.partner_type == partner_type]
        if tier:
            partners = [p for p in partners if p.tier == tier]
        if status:
            partners = [p for p in partners if p.status == status]
        
        partners.sort(key=lambda x: x.total_revenue, reverse=True)
        return partners[offset:offset + limit]

    async def update_partner(self, partner_id: str, **updates) -> Optional[Partner]:
        """Update partner"""
        partner = self.partners.get(partner_id)
        if not partner:
            return None
        
        for key, value in updates.items():
            if hasattr(partner, key):
                setattr(partner, key, value)
        
        partner.updated_at = datetime.utcnow()
        logger.info("partner_updated", partner_id=partner_id)
        return partner

    async def approve_partner(self, partner_id: str, reviewer_id: str) -> Optional[Partner]:
        """Approve a pending partner"""
        partner = self.partners.get(partner_id)
        if not partner:
            return None
        
        partner.status = PartnerStatus.ACTIVE
        partner.updated_at = datetime.utcnow()
        
        logger.info("partner_approved", partner_id=partner_id, reviewer=reviewer_id)
        return partner

    async def create_deal_registration(
        self,
        tenant_id: str,
        partner_id: str,
        customer_name: str,
        customer_email: str,
        opportunity_name: str,
        opportunity_value: float,
        expected_close_date: datetime,
        **kwargs
    ) -> DealRegistration:
        """Create a deal registration"""
        partner = self.partners.get(partner_id)
        if not partner:
            raise ValueError(f"Partner {partner_id} not found")
        
        registration = DealRegistration(
            id=str(uuid4()),
            partner_id=partner_id,
            partner_name=partner.name,
            customer_name=customer_name,
            customer_contact=kwargs.get("customer_contact", ""),
            customer_email=customer_email,
            customer_phone=kwargs.get("customer_phone"),
            opportunity_name=opportunity_name,
            opportunity_value=opportunity_value,
            product_interest=kwargs.get("product_interest", []),
            expected_close_date=expected_close_date,
            description=kwargs.get("description", ""),
            status=DealRegistrationStatus.SUBMITTED,
            expiration_date=datetime.utcnow(),  # Would calculate based on rules
            reviewer_id=None,
            review_notes=None,
            approved_at=None,
            rejected_at=None,
            rejection_reason=None,
            deal_id=None,
            tenant_id=tenant_id
        )
        
        self.deal_registrations[registration.id] = registration
        logger.info("deal_registration_created", registration_id=registration.id, partner_id=partner_id)
        return registration

    async def get_deal_registration(self, registration_id: str) -> Optional[DealRegistration]:
        """Get deal registration by ID"""
        return self.deal_registrations.get(registration_id)

    async def list_deal_registrations(
        self,
        tenant_id: str,
        partner_id: Optional[str] = None,
        status: Optional[DealRegistrationStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[DealRegistration]:
        """List deal registrations"""
        registrations = [r for r in self.deal_registrations.values() if r.tenant_id == tenant_id]
        
        if partner_id:
            registrations = [r for r in registrations if r.partner_id == partner_id]
        if status:
            registrations = [r for r in registrations if r.status == status]
        
        registrations.sort(key=lambda x: x.created_at, reverse=True)
        return registrations[offset:offset + limit]

    async def review_deal_registration(
        self,
        registration_id: str,
        reviewer_id: str,
        approved: bool,
        notes: str = "",
        rejection_reason: Optional[str] = None
    ) -> Optional[DealRegistration]:
        """Review and approve/reject deal registration"""
        registration = self.deal_registrations.get(registration_id)
        if not registration:
            return None
        
        now = datetime.utcnow()
        registration.reviewer_id = reviewer_id
        registration.review_notes = notes
        
        if approved:
            registration.status = DealRegistrationStatus.APPROVED
            registration.approved_at = now
        else:
            registration.status = DealRegistrationStatus.REJECTED
            registration.rejected_at = now
            registration.rejection_reason = rejection_reason
        
        registration.updated_at = now
        
        logger.info(
            "deal_registration_reviewed",
            registration_id=registration_id,
            approved=approved
        )
        return registration

    async def create_resource(
        self,
        tenant_id: str,
        title: str,
        description: str,
        resource_type: str,
        category: str,
        **kwargs
    ) -> PartnerResource:
        """Create a partner resource"""
        resource = PartnerResource(
            id=str(uuid4()),
            title=title,
            description=description,
            resource_type=resource_type,
            category=category,
            file_url=kwargs.get("file_url"),
            external_url=kwargs.get("external_url"),
            access_tiers=kwargs.get("access_tiers", list(PartnerTier)),
            is_featured=kwargs.get("is_featured", False),
            tenant_id=tenant_id
        )
        
        self.resources[resource.id] = resource
        logger.info("partner_resource_created", resource_id=resource.id, title=title)
        return resource

    async def list_resources(
        self,
        tenant_id: str,
        partner_tier: Optional[PartnerTier] = None,
        resource_type: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[PartnerResource]:
        """List partner resources"""
        resources = [r for r in self.resources.values() if r.tenant_id == tenant_id]
        
        if partner_tier:
            resources = [r for r in resources if partner_tier in r.access_tiers]
        if resource_type:
            resources = [r for r in resources if r.resource_type == resource_type]
        if category:
            resources = [r for r in resources if r.category == category]
        
        return sorted(resources, key=lambda x: x.is_featured, reverse=True)

    async def get_partner_stats(self, partner_id: str) -> Dict[str, Any]:
        """Get statistics for a partner"""
        partner = self.partners.get(partner_id)
        if not partner:
            return {}
        
        registrations = [
            r for r in self.deal_registrations.values()
            if r.partner_id == partner_id
        ]
        
        return {
            "partner_id": partner_id,
            "tier": partner.tier.value,
            "total_revenue": partner.total_revenue,
            "total_deals": partner.total_deals,
            "active_deals": partner.active_deals,
            "deal_registrations": {
                "total": len(registrations),
                "submitted": len([r for r in registrations if r.status == DealRegistrationStatus.SUBMITTED]),
                "approved": len([r for r in registrations if r.status == DealRegistrationStatus.APPROVED]),
                "won": len([r for r in registrations if r.status == DealRegistrationStatus.WON]),
                "total_value": sum(r.opportunity_value for r in registrations)
            },
            "commission_earned": sum(r.commission_earned for r in registrations)
        }

    async def get_portal_stats(self, tenant_id: str) -> Dict[str, Any]:
        """Get overall partner portal statistics"""
        partners = [p for p in self.partners.values() if p.tenant_id == tenant_id]
        registrations = [r for r in self.deal_registrations.values() if r.tenant_id == tenant_id]
        
        return {
            "total_partners": len(partners),
            "active_partners": len([p for p in partners if p.status == PartnerStatus.ACTIVE]),
            "by_tier": {
                tier.value: len([p for p in partners if p.tier == tier])
                for tier in PartnerTier
            },
            "by_type": {
                ptype.value: len([p for p in partners if p.partner_type == ptype])
                for ptype in PartnerType
            },
            "deal_registrations": {
                "total": len(registrations),
                "pending_review": len([r for r in registrations if r.status == DealRegistrationStatus.SUBMITTED]),
                "approved": len([r for r in registrations if r.status == DealRegistrationStatus.APPROVED]),
                "total_value": sum(r.opportunity_value for r in registrations)
            },
            "total_partner_revenue": sum(p.total_revenue for p in partners)
        }


# Global service instance
partner_portal_service = PartnerPortalService()
