"""
Company Service - Company/Account Management
=============================================
Full company data management with hierarchy support.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class CompanySize(str, Enum):
    """Company size categories."""
    STARTUP = "startup"           # 1-10 employees
    SMALL = "small"               # 11-50 employees
    MEDIUM = "medium"             # 51-200 employees
    LARGE = "large"               # 201-1000 employees
    ENTERPRISE = "enterprise"     # 1000+ employees


class CompanyType(str, Enum):
    """Company types."""
    PROSPECT = "prospect"
    CUSTOMER = "customer"
    PARTNER = "partner"
    COMPETITOR = "competitor"
    VENDOR = "vendor"
    OTHER = "other"


class Industry(str, Enum):
    """Industry categories."""
    TECHNOLOGY = "technology"
    FINANCE = "finance"
    HEALTHCARE = "healthcare"
    MANUFACTURING = "manufacturing"
    RETAIL = "retail"
    EDUCATION = "education"
    GOVERNMENT = "government"
    REAL_ESTATE = "real_estate"
    MEDIA = "media"
    CONSULTING = "consulting"
    LEGAL = "legal"
    ENERGY = "energy"
    TRANSPORTATION = "transportation"
    HOSPITALITY = "hospitality"
    NON_PROFIT = "non_profit"
    OTHER = "other"


@dataclass
class CompanyContact:
    """Contact associated with a company."""
    contact_id: str
    role: str
    is_primary: bool = False
    is_decision_maker: bool = False
    added_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CompanyDeal:
    """Deal associated with a company."""
    deal_id: str
    name: str
    value: float
    stage: str
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CompanyNote:
    """Note on a company."""
    id: str
    content: str
    author_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    is_pinned: bool = False


@dataclass
class CompanyActivity:
    """Activity record for a company."""
    id: str
    activity_type: str
    description: str
    contact_id: Optional[str]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict = field(default_factory=dict)


@dataclass
class Company:
    """Company/Account entity."""
    id: str
    name: str
    domain: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[Industry] = None
    size: Optional[CompanySize] = None
    company_type: CompanyType = CompanyType.PROSPECT
    
    # Location
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    
    # Financials
    annual_revenue: Optional[float] = None
    employee_count: Optional[int] = None
    funding_raised: Optional[float] = None
    
    # Social/Online
    linkedin_url: Optional[str] = None
    twitter_url: Optional[str] = None
    facebook_url: Optional[str] = None
    crunchbase_url: Optional[str] = None
    
    # Hierarchy
    parent_company_id: Optional[str] = None
    subsidiary_ids: list[str] = field(default_factory=list)
    
    # Relationships
    contacts: list[CompanyContact] = field(default_factory=list)
    deals: list[CompanyDeal] = field(default_factory=list)
    notes: list[CompanyNote] = field(default_factory=list)
    activities: list[CompanyActivity] = field(default_factory=list)
    
    # Tags and custom fields
    tags: list[str] = field(default_factory=list)
    custom_fields: dict = field(default_factory=dict)
    
    # CRM sync
    hubspot_id: Optional[str] = None
    salesforce_id: Optional[str] = None
    
    # Enrichment
    is_enriched: bool = False
    enriched_at: Optional[datetime] = None
    enrichment_source: Optional[str] = None
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_contacted_at: Optional[datetime] = None
    
    # Scoring
    health_score: int = 50  # 0-100
    engagement_score: int = 0
    
    # Owner
    owner_id: Optional[str] = None


@dataclass
class CompanySearchResult:
    """Search result with match info."""
    company: Company
    match_score: float
    matched_fields: list[str]


class CompanyService:
    """Service for company/account management."""
    
    def __init__(self):
        self.companies: dict[str, Company] = {}
        self._create_sample_companies()
    
    def _create_sample_companies(self):
        """Create sample companies for demo."""
        samples = [
            Company(
                id="comp_1",
                name="TechCorp Inc",
                domain="techcorp.com",
                website="https://www.techcorp.com",
                industry=Industry.TECHNOLOGY,
                size=CompanySize.MEDIUM,
                company_type=CompanyType.CUSTOMER,
                city="San Francisco",
                state="CA",
                country="United States",
                annual_revenue=25000000,
                employee_count=150,
                linkedin_url="https://linkedin.com/company/techcorp",
                is_enriched=True,
                enriched_at=datetime.utcnow(),
                health_score=85,
                engagement_score=72,
                tags=["technology", "saas", "key-account"]
            ),
            Company(
                id="comp_2",
                name="Global Finance Ltd",
                domain="globalfinance.com",
                website="https://www.globalfinance.com",
                industry=Industry.FINANCE,
                size=CompanySize.ENTERPRISE,
                company_type=CompanyType.PROSPECT,
                city="New York",
                state="NY",
                country="United States",
                annual_revenue=500000000,
                employee_count=2500,
                linkedin_url="https://linkedin.com/company/globalfinance",
                is_enriched=True,
                enriched_at=datetime.utcnow(),
                health_score=60,
                engagement_score=35,
                tags=["finance", "enterprise", "high-value"]
            ),
            Company(
                id="comp_3",
                name="HealthPlus Systems",
                domain="healthplus.io",
                website="https://www.healthplus.io",
                industry=Industry.HEALTHCARE,
                size=CompanySize.SMALL,
                company_type=CompanyType.PROSPECT,
                city="Boston",
                state="MA",
                country="United States",
                annual_revenue=5000000,
                employee_count=45,
                is_enriched=False,
                health_score=50,
                engagement_score=20,
                tags=["healthcare", "startup"]
            )
        ]
        
        for company in samples:
            self.companies[company.id] = company
    
    async def create_company(
        self,
        name: str,
        domain: Optional[str] = None,
        **kwargs
    ) -> Company:
        """Create a new company."""
        company_id = f"comp_{uuid4().hex[:8]}"
        
        company = Company(
            id=company_id,
            name=name,
            domain=domain,
            **kwargs
        )
        
        self.companies[company_id] = company
        
        logger.info(f"Created company: {name} ({company_id})")
        
        return company
    
    async def get_company(self, company_id: str) -> Optional[Company]:
        """Get a company by ID."""
        return self.companies.get(company_id)
    
    async def get_company_by_domain(self, domain: str) -> Optional[Company]:
        """Get a company by domain."""
        domain = domain.lower().strip()
        
        for company in self.companies.values():
            if company.domain and company.domain.lower() == domain:
                return company
        
        return None
    
    async def update_company(
        self,
        company_id: str,
        updates: dict[str, Any]
    ) -> Optional[Company]:
        """Update a company."""
        company = self.companies.get(company_id)
        if not company:
            return None
        
        for key, value in updates.items():
            if hasattr(company, key):
                setattr(company, key, value)
        
        company.updated_at = datetime.utcnow()
        
        logger.info(f"Updated company: {company_id}")
        
        return company
    
    async def delete_company(self, company_id: str) -> bool:
        """Delete a company."""
        if company_id in self.companies:
            del self.companies[company_id]
            logger.info(f"Deleted company: {company_id}")
            return True
        return False
    
    async def list_companies(
        self,
        company_type: Optional[CompanyType] = None,
        industry: Optional[Industry] = None,
        size: Optional[CompanySize] = None,
        tags: Optional[list[str]] = None,
        owner_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> list[Company]:
        """List companies with filters."""
        results = list(self.companies.values())
        
        if company_type:
            results = [c for c in results if c.company_type == company_type]
        
        if industry:
            results = [c for c in results if c.industry == industry]
        
        if size:
            results = [c for c in results if c.size == size]
        
        if tags:
            results = [
                c for c in results
                if any(tag in c.tags for tag in tags)
            ]
        
        if owner_id:
            results = [c for c in results if c.owner_id == owner_id]
        
        # Sort by name
        results.sort(key=lambda c: c.name)
        
        return results[offset:offset + limit]
    
    async def search_companies(
        self,
        query: str,
        limit: int = 20
    ) -> list[CompanySearchResult]:
        """Search companies by name or domain."""
        query = query.lower()
        results = []
        
        for company in self.companies.values():
            matched_fields = []
            score = 0.0
            
            # Check name
            if query in company.name.lower():
                matched_fields.append("name")
                if company.name.lower().startswith(query):
                    score += 1.0
                else:
                    score += 0.5
            
            # Check domain
            if company.domain and query in company.domain.lower():
                matched_fields.append("domain")
                score += 0.8
            
            # Check tags
            for tag in company.tags:
                if query in tag.lower():
                    matched_fields.append(f"tag:{tag}")
                    score += 0.3
            
            # Check city
            if company.city and query in company.city.lower():
                matched_fields.append("city")
                score += 0.2
            
            if matched_fields:
                results.append(CompanySearchResult(
                    company=company,
                    match_score=score,
                    matched_fields=matched_fields
                ))
        
        # Sort by score
        results.sort(key=lambda r: r.match_score, reverse=True)
        
        return results[:limit]
    
    async def add_contact_to_company(
        self,
        company_id: str,
        contact_id: str,
        role: str,
        is_primary: bool = False,
        is_decision_maker: bool = False
    ) -> Optional[CompanyContact]:
        """Add a contact to a company."""
        company = self.companies.get(company_id)
        if not company:
            return None
        
        # Check if contact already associated
        for existing in company.contacts:
            if existing.contact_id == contact_id:
                # Update existing
                existing.role = role
                existing.is_primary = is_primary
                existing.is_decision_maker = is_decision_maker
                return existing
        
        # Create new association
        contact = CompanyContact(
            contact_id=contact_id,
            role=role,
            is_primary=is_primary,
            is_decision_maker=is_decision_maker
        )
        
        # If this is primary, unset other primaries
        if is_primary:
            for existing in company.contacts:
                existing.is_primary = False
        
        company.contacts.append(contact)
        company.updated_at = datetime.utcnow()
        
        logger.info(f"Added contact {contact_id} to company {company_id}")
        
        return contact
    
    async def remove_contact_from_company(
        self,
        company_id: str,
        contact_id: str
    ) -> bool:
        """Remove a contact from a company."""
        company = self.companies.get(company_id)
        if not company:
            return False
        
        original_len = len(company.contacts)
        company.contacts = [
            c for c in company.contacts
            if c.contact_id != contact_id
        ]
        
        if len(company.contacts) < original_len:
            company.updated_at = datetime.utcnow()
            logger.info(f"Removed contact {contact_id} from company {company_id}")
            return True
        
        return False
    
    async def get_company_contacts(
        self,
        company_id: str
    ) -> list[CompanyContact]:
        """Get all contacts for a company."""
        company = self.companies.get(company_id)
        if not company:
            return []
        return company.contacts
    
    async def add_note_to_company(
        self,
        company_id: str,
        content: str,
        author_id: str,
        is_pinned: bool = False
    ) -> Optional[CompanyNote]:
        """Add a note to a company."""
        company = self.companies.get(company_id)
        if not company:
            return None
        
        note = CompanyNote(
            id=f"note_{uuid4().hex[:8]}",
            content=content,
            author_id=author_id,
            is_pinned=is_pinned
        )
        
        company.notes.append(note)
        company.updated_at = datetime.utcnow()
        
        logger.info(f"Added note to company {company_id}")
        
        return note
    
    async def log_activity(
        self,
        company_id: str,
        activity_type: str,
        description: str,
        contact_id: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> Optional[CompanyActivity]:
        """Log an activity for a company."""
        company = self.companies.get(company_id)
        if not company:
            return None
        
        activity = CompanyActivity(
            id=f"act_{uuid4().hex[:8]}",
            activity_type=activity_type,
            description=description,
            contact_id=contact_id,
            metadata=metadata or {}
        )
        
        company.activities.append(activity)
        company.updated_at = datetime.utcnow()
        
        # Update last contacted if relevant
        if activity_type in ["email", "call", "meeting"]:
            company.last_contacted_at = datetime.utcnow()
        
        return activity
    
    async def get_company_activities(
        self,
        company_id: str,
        activity_type: Optional[str] = None,
        limit: int = 50
    ) -> list[CompanyActivity]:
        """Get activities for a company."""
        company = self.companies.get(company_id)
        if not company:
            return []
        
        activities = company.activities
        
        if activity_type:
            activities = [a for a in activities if a.activity_type == activity_type]
        
        # Sort by timestamp descending
        activities.sort(key=lambda a: a.timestamp, reverse=True)
        
        return activities[:limit]
    
    async def enrich_company(
        self,
        company_id: str,
        source: str = "clearbit"
    ) -> Optional[Company]:
        """Enrich company data from external source."""
        company = self.companies.get(company_id)
        if not company:
            return None
        
        # Simulate enrichment with mock data
        logger.info(f"Enriching company {company_id} from {source}")
        
        await asyncio.sleep(0.1)  # Simulate API call
        
        # Mock enrichment based on domain
        if company.domain:
            if not company.linkedin_url:
                company.linkedin_url = f"https://linkedin.com/company/{company.domain.split('.')[0]}"
            
            if not company.employee_count:
                company.employee_count = 100
            
            if not company.industry:
                company.industry = Industry.TECHNOLOGY
        
        company.is_enriched = True
        company.enriched_at = datetime.utcnow()
        company.enrichment_source = source
        company.updated_at = datetime.utcnow()
        
        logger.info(f"Enriched company {company_id}")
        
        return company
    
    async def calculate_health_score(
        self,
        company_id: str
    ) -> Optional[dict]:
        """Calculate health score for a company."""
        company = self.companies.get(company_id)
        if not company:
            return None
        
        score = 50  # Base score
        factors = {}
        
        # Enrichment factor
        if company.is_enriched:
            score += 10
            factors["enrichment"] = 10
        
        # Contact count factor
        contact_count = len(company.contacts)
        if contact_count > 0:
            contact_points = min(contact_count * 5, 20)
            score += contact_points
            factors["contacts"] = contact_points
        
        # Decision maker factor
        has_decision_maker = any(c.is_decision_maker for c in company.contacts)
        if has_decision_maker:
            score += 10
            factors["decision_maker"] = 10
        
        # Recent activity factor
        recent_activities = [
            a for a in company.activities
            if (datetime.utcnow() - a.timestamp).days <= 30
        ]
        if recent_activities:
            activity_points = min(len(recent_activities) * 2, 10)
            score += activity_points
            factors["recent_activity"] = activity_points
        
        # Deal factor
        if company.deals:
            deal_points = min(len(company.deals) * 5, 15)
            score += deal_points
            factors["deals"] = deal_points
        
        # Cap at 100
        score = min(score, 100)
        
        company.health_score = score
        company.updated_at = datetime.utcnow()
        
        return {
            "company_id": company_id,
            "health_score": score,
            "factors": factors
        }
    
    async def get_company_hierarchy(
        self,
        company_id: str
    ) -> dict:
        """Get company hierarchy (parent/subsidiaries)."""
        company = self.companies.get(company_id)
        if not company:
            return {}
        
        result = {
            "company": company,
            "parent": None,
            "subsidiaries": []
        }
        
        # Get parent
        if company.parent_company_id:
            result["parent"] = self.companies.get(company.parent_company_id)
        
        # Get subsidiaries
        for sub_id in company.subsidiary_ids:
            sub = self.companies.get(sub_id)
            if sub:
                result["subsidiaries"].append(sub)
        
        return result
    
    async def set_parent_company(
        self,
        company_id: str,
        parent_id: str
    ) -> bool:
        """Set parent company relationship."""
        company = self.companies.get(company_id)
        parent = self.companies.get(parent_id)
        
        if not company or not parent:
            return False
        
        # Remove from old parent if exists
        if company.parent_company_id:
            old_parent = self.companies.get(company.parent_company_id)
            if old_parent and company_id in old_parent.subsidiary_ids:
                old_parent.subsidiary_ids.remove(company_id)
        
        # Set new parent
        company.parent_company_id = parent_id
        if company_id not in parent.subsidiary_ids:
            parent.subsidiary_ids.append(company_id)
        
        company.updated_at = datetime.utcnow()
        parent.updated_at = datetime.utcnow()
        
        logger.info(f"Set parent {parent_id} for company {company_id}")
        
        return True
    
    async def merge_companies(
        self,
        primary_id: str,
        duplicate_id: str
    ) -> Optional[Company]:
        """Merge duplicate company into primary."""
        primary = self.companies.get(primary_id)
        duplicate = self.companies.get(duplicate_id)
        
        if not primary or not duplicate:
            return None
        
        # Merge contacts
        existing_contact_ids = {c.contact_id for c in primary.contacts}
        for contact in duplicate.contacts:
            if contact.contact_id not in existing_contact_ids:
                primary.contacts.append(contact)
        
        # Merge deals
        existing_deal_ids = {d.deal_id for d in primary.deals}
        for deal in duplicate.deals:
            if deal.deal_id not in existing_deal_ids:
                primary.deals.append(deal)
        
        # Merge notes
        for note in duplicate.notes:
            primary.notes.append(note)
        
        # Merge activities
        for activity in duplicate.activities:
            primary.activities.append(activity)
        
        # Merge tags
        for tag in duplicate.tags:
            if tag not in primary.tags:
                primary.tags.append(tag)
        
        # Merge custom fields (don't overwrite)
        for key, value in duplicate.custom_fields.items():
            if key not in primary.custom_fields:
                primary.custom_fields[key] = value
        
        # Fill in missing data
        if not primary.industry and duplicate.industry:
            primary.industry = duplicate.industry
        if not primary.size and duplicate.size:
            primary.size = duplicate.size
        if not primary.linkedin_url and duplicate.linkedin_url:
            primary.linkedin_url = duplicate.linkedin_url
        
        primary.updated_at = datetime.utcnow()
        
        # Delete duplicate
        del self.companies[duplicate_id]
        
        logger.info(f"Merged company {duplicate_id} into {primary_id}")
        
        return primary
    
    async def get_company_stats(self) -> dict:
        """Get overall company statistics."""
        companies = list(self.companies.values())
        
        # Type distribution
        type_dist = {}
        for t in CompanyType:
            type_dist[t.value] = len([c for c in companies if c.company_type == t])
        
        # Size distribution
        size_dist = {}
        for s in CompanySize:
            size_dist[s.value] = len([c for c in companies if c.size == s])
        
        # Industry distribution
        industry_dist = {}
        for i in Industry:
            count = len([c for c in companies if c.industry == i])
            if count > 0:
                industry_dist[i.value] = count
        
        return {
            "total_companies": len(companies),
            "enriched_count": len([c for c in companies if c.is_enriched]),
            "with_contacts": len([c for c in companies if c.contacts]),
            "with_deals": len([c for c in companies if c.deals]),
            "type_distribution": type_dist,
            "size_distribution": size_dist,
            "industry_distribution": industry_dist,
            "average_health_score": sum(c.health_score for c in companies) / len(companies) if companies else 0
        }


# Global service instance
_company_service: Optional[CompanyService] = None


def get_company_service() -> CompanyService:
    """Get or create the company service singleton."""
    global _company_service
    if _company_service is None:
        _company_service = CompanyService()
    return _company_service
