"""
Contact Enrichment Routes - Enrich contact and company data
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from enum import Enum
import structlog
import uuid
import random
import hashlib

logger = structlog.get_logger()

router = APIRouter(prefix="/enrichment", tags=["Contact Enrichment"])


class EnrichmentType(str, Enum):
    CONTACT = "contact"
    COMPANY = "company"
    EMAIL = "email"
    DOMAIN = "domain"


class EnrichmentProvider(str, Enum):
    INTERNAL = "internal"
    CLEARBIT = "clearbit"
    ZOOMINFO = "zoominfo"
    APOLLO = "apollo"
    HUNTER = "hunter"
    LUSHA = "lusha"
    COGNISM = "cognism"


class EnrichmentStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    NOT_FOUND = "not_found"


class ContactEnrichmentRequest(BaseModel):
    email: Optional[str] = None
    linkedin_url: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company_name: Optional[str] = None
    company_domain: Optional[str] = None


class CompanyEnrichmentRequest(BaseModel):
    domain: Optional[str] = None
    company_name: Optional[str] = None


class BulkEnrichmentRequest(BaseModel):
    enrichment_type: EnrichmentType
    record_ids: List[str]
    fields_to_enrich: Optional[List[str]] = None
    provider: Optional[EnrichmentProvider] = None


class EnrichmentSettingsUpdate(BaseModel):
    providers_priority: Optional[List[EnrichmentProvider]] = None
    auto_enrich_new_contacts: Optional[bool] = None
    auto_enrich_new_companies: Optional[bool] = None
    enrichment_frequency_days: Optional[int] = None
    fields_to_enrich: Optional[Dict[str, List[str]]] = None


# In-memory storage
enrichment_jobs = {}
enrichment_history = {}
enrichment_settings = {}
provider_credits = {}
enrichment_queue = []
cached_enrichments = {}


# Contact Enrichment
@router.post("/contact")
async def enrich_contact(
    request: ContactEnrichmentRequest,
    providers: Optional[List[EnrichmentProvider]] = None,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Enrich a contact with additional data"""
    enrichment_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    # Check cache
    cache_key = generate_cache_key(request.email or request.linkedin_url or f"{request.first_name}_{request.last_name}")
    if cache_key in cached_enrichments:
        cached = cached_enrichments[cache_key]
        if cached.get("expires_at", "") > now.isoformat():
            return {**cached["data"], "from_cache": True}
    
    # Perform enrichment
    enriched_data = generate_contact_enrichment(request)
    
    result = {
        "enrichment_id": enrichment_id,
        "type": EnrichmentType.CONTACT.value,
        "status": EnrichmentStatus.COMPLETED.value if enriched_data else EnrichmentStatus.NOT_FOUND.value,
        "input": {
            "email": request.email,
            "linkedin_url": request.linkedin_url,
            "name": f"{request.first_name or ''} {request.last_name or ''}".strip(),
            "company": request.company_name
        },
        "enriched_data": enriched_data,
        "fields_enriched": list(enriched_data.keys()) if enriched_data else [],
        "provider_used": random.choice(list(EnrichmentProvider)).value if enriched_data else None,
        "credits_used": 1 if enriched_data else 0,
        "enriched_at": now.isoformat()
    }
    
    # Cache result
    cached_enrichments[cache_key] = {
        "data": result,
        "expires_at": (now + timedelta(days=30)).isoformat()
    }
    
    # Store history
    enrichment_history[enrichment_id] = {**result, "tenant_id": tenant_id, "user_id": user_id}
    
    logger.info("contact_enriched", enrichment_id=enrichment_id, status=result["status"])
    return result


@router.post("/company")
async def enrich_company(
    request: CompanyEnrichmentRequest,
    providers: Optional[List[EnrichmentProvider]] = None,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Enrich a company with additional data"""
    enrichment_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    # Check cache
    cache_key = generate_cache_key(request.domain or request.company_name)
    if cache_key in cached_enrichments:
        cached = cached_enrichments[cache_key]
        if cached.get("expires_at", "") > now.isoformat():
            return {**cached["data"], "from_cache": True}
    
    # Perform enrichment
    enriched_data = generate_company_enrichment(request)
    
    result = {
        "enrichment_id": enrichment_id,
        "type": EnrichmentType.COMPANY.value,
        "status": EnrichmentStatus.COMPLETED.value if enriched_data else EnrichmentStatus.NOT_FOUND.value,
        "input": {
            "domain": request.domain,
            "company_name": request.company_name
        },
        "enriched_data": enriched_data,
        "fields_enriched": list(enriched_data.keys()) if enriched_data else [],
        "provider_used": random.choice(list(EnrichmentProvider)).value if enriched_data else None,
        "credits_used": 1 if enriched_data else 0,
        "enriched_at": now.isoformat()
    }
    
    # Cache result
    cached_enrichments[cache_key] = {
        "data": result,
        "expires_at": (now + timedelta(days=30)).isoformat()
    }
    
    # Store history
    enrichment_history[enrichment_id] = {**result, "tenant_id": tenant_id, "user_id": user_id}
    
    logger.info("company_enriched", enrichment_id=enrichment_id, status=result["status"])
    return result


@router.post("/email/verify")
async def verify_email(
    email: str,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Verify email address validity and deliverability"""
    verification_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    # Mock email verification
    is_valid = "@" in email and "." in email.split("@")[-1]
    is_deliverable = is_valid and random.random() > 0.1
    is_disposable = any(d in email.lower() for d in ["temp", "disposable", "guerrilla", "mailinator"])
    is_role_based = any(r in email.lower() for r in ["info@", "admin@", "support@", "sales@", "contact@"])
    
    result = {
        "verification_id": verification_id,
        "email": email,
        "is_valid": is_valid,
        "is_deliverable": is_deliverable,
        "is_disposable": is_disposable,
        "is_role_based": is_role_based,
        "is_catch_all": random.random() > 0.8 if is_valid else False,
        "quality_score": random.randint(60, 100) if is_deliverable else random.randint(0, 40),
        "mx_records_found": is_valid,
        "smtp_check_passed": is_deliverable,
        "domain": email.split("@")[-1] if "@" in email else None,
        "verified_at": now.isoformat()
    }
    
    return result


@router.post("/domain/find-emails")
async def find_emails_by_domain(
    domain: str,
    limit: int = Query(default=10, le=50),
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Find email addresses for a domain"""
    job_id = str(uuid.uuid4())
    
    # Mock email discovery
    emails = []
    patterns = ["firstname.lastname", "firstname", "f.lastname", "firstnamelastname"]
    for i in range(min(limit, random.randint(3, 15))):
        name = random.choice(["john.smith", "jane.doe", "mike.wilson", "sarah.jones", "alex.chen"])
        emails.append({
            "email": f"{name}@{domain}",
            "confidence": random.randint(60, 100),
            "source": random.choice(["web", "social", "database"]),
            "verified": random.random() > 0.3,
            "first_name": name.split(".")[0].title() if "." in name else None,
            "last_name": name.split(".")[-1].title() if "." in name else None,
            "position": random.choice(["CEO", "CTO", "VP Sales", "Director", "Manager", None])
        })
    
    return {
        "job_id": job_id,
        "domain": domain,
        "emails_found": len(emails),
        "emails": emails,
        "email_pattern": random.choice(patterns),
        "domain_type": random.choice(["business", "personal"]),
        "credits_used": len(emails),
        "searched_at": datetime.utcnow().isoformat()
    }


# Bulk Enrichment
@router.post("/bulk")
async def start_bulk_enrichment(
    request: BulkEnrichmentRequest,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Start bulk enrichment job"""
    job_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    job = {
        "job_id": job_id,
        "enrichment_type": request.enrichment_type.value,
        "total_records": len(request.record_ids),
        "record_ids": request.record_ids,
        "fields_to_enrich": request.fields_to_enrich,
        "provider": request.provider.value if request.provider else None,
        "status": "queued",
        "processed": 0,
        "enriched": 0,
        "failed": 0,
        "not_found": 0,
        "created_by": user_id,
        "tenant_id": tenant_id,
        "created_at": now.isoformat(),
        "started_at": None,
        "completed_at": None
    }
    
    enrichment_jobs[job_id] = job
    enrichment_queue.append(job_id)
    
    logger.info("bulk_enrichment_started", job_id=job_id, records=len(request.record_ids))
    return job


@router.get("/bulk/{job_id}")
async def get_bulk_enrichment_status(job_id: str):
    """Get bulk enrichment job status"""
    if job_id not in enrichment_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = enrichment_jobs[job_id]
    
    # Simulate progress
    if job["status"] == "queued":
        job["status"] = "in_progress"
        job["started_at"] = datetime.utcnow().isoformat()
    
    if job["status"] == "in_progress":
        progress = min(job["total_records"], job["processed"] + random.randint(5, 20))
        job["processed"] = progress
        job["enriched"] = int(progress * random.uniform(0.7, 0.9))
        job["failed"] = int(progress * random.uniform(0.01, 0.1))
        job["not_found"] = progress - job["enriched"] - job["failed"]
        
        if job["processed"] >= job["total_records"]:
            job["status"] = "completed"
            job["completed_at"] = datetime.utcnow().isoformat()
    
    return job


@router.get("/bulk/{job_id}/results")
async def get_bulk_enrichment_results(
    job_id: str,
    status: Optional[EnrichmentStatus] = None,
    limit: int = Query(default=50, le=100),
    offset: int = 0
):
    """Get bulk enrichment results"""
    if job_id not in enrichment_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = enrichment_jobs[job_id]
    
    # Mock results
    results = [
        {
            "record_id": job["record_ids"][i] if i < len(job["record_ids"]) else str(uuid.uuid4()),
            "status": random.choice([s.value for s in EnrichmentStatus if s != EnrichmentStatus.PENDING]),
            "fields_enriched": random.sample(["phone", "title", "linkedin", "email", "company_size"], k=random.randint(0, 3)),
            "enriched_at": datetime.utcnow().isoformat()
        }
        for i in range(job.get("processed", 0))
    ]
    
    if status:
        results = [r for r in results if r["status"] == status.value]
    
    return {
        "job_id": job_id,
        "results": results[offset:offset + limit],
        "total": len(results),
        "limit": limit,
        "offset": offset
    }


# Enrichment History
@router.get("/history")
async def get_enrichment_history(
    enrichment_type: Optional[EnrichmentType] = None,
    status: Optional[EnrichmentStatus] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    offset: int = 0,
    tenant_id: str = Query(default="default")
):
    """Get enrichment history"""
    result = [e for e in enrichment_history.values() if e.get("tenant_id") == tenant_id]
    
    if enrichment_type:
        result = [e for e in result if e.get("type") == enrichment_type.value]
    if status:
        result = [e for e in result if e.get("status") == status.value]
    if start_date:
        result = [e for e in result if e.get("enriched_at", "") >= start_date]
    if end_date:
        result = [e for e in result if e.get("enriched_at", "") <= end_date]
    
    result.sort(key=lambda x: x.get("enriched_at", ""), reverse=True)
    
    return {
        "enrichments": result[offset:offset + limit],
        "total": len(result),
        "limit": limit,
        "offset": offset
    }


# Settings
@router.get("/settings")
async def get_enrichment_settings(tenant_id: str = Query(default="default")):
    """Get enrichment settings"""
    if tenant_id not in enrichment_settings:
        enrichment_settings[tenant_id] = {
            "providers_priority": [p.value for p in [EnrichmentProvider.CLEARBIT, EnrichmentProvider.APOLLO, EnrichmentProvider.ZOOMINFO]],
            "auto_enrich_new_contacts": True,
            "auto_enrich_new_companies": True,
            "enrichment_frequency_days": 90,
            "fields_to_enrich": {
                "contact": ["phone", "title", "linkedin_url", "location"],
                "company": ["industry", "employees", "revenue", "technologies"]
            }
        }
    return enrichment_settings[tenant_id]


@router.put("/settings")
async def update_enrichment_settings(
    request: EnrichmentSettingsUpdate,
    tenant_id: str = Query(default="default")
):
    """Update enrichment settings"""
    if tenant_id not in enrichment_settings:
        await get_enrichment_settings(tenant_id)
    
    settings = enrichment_settings[tenant_id]
    
    if request.providers_priority is not None:
        settings["providers_priority"] = [p.value for p in request.providers_priority]
    if request.auto_enrich_new_contacts is not None:
        settings["auto_enrich_new_contacts"] = request.auto_enrich_new_contacts
    if request.auto_enrich_new_companies is not None:
        settings["auto_enrich_new_companies"] = request.auto_enrich_new_companies
    if request.enrichment_frequency_days is not None:
        settings["enrichment_frequency_days"] = request.enrichment_frequency_days
    if request.fields_to_enrich is not None:
        settings["fields_to_enrich"] = request.fields_to_enrich
    
    settings["updated_at"] = datetime.utcnow().isoformat()
    
    return settings


# Credits Management
@router.get("/credits")
async def get_provider_credits(tenant_id: str = Query(default="default")):
    """Get enrichment credits balance"""
    if tenant_id not in provider_credits:
        provider_credits[tenant_id] = {
            provider.value: {
                "total_credits": random.randint(5000, 50000),
                "used_credits": random.randint(500, 4000),
                "remaining_credits": 0,
                "resets_at": (datetime.utcnow() + timedelta(days=random.randint(10, 30))).isoformat()
            }
            for provider in EnrichmentProvider
            if provider != EnrichmentProvider.INTERNAL
        }
        
        for p, data in provider_credits[tenant_id].items():
            data["remaining_credits"] = data["total_credits"] - data["used_credits"]
    
    return {
        "tenant_id": tenant_id,
        "providers": provider_credits[tenant_id],
        "total_remaining": sum(p["remaining_credits"] for p in provider_credits[tenant_id].values())
    }


# Analytics
@router.get("/analytics/overview")
async def get_enrichment_analytics(
    days: int = Query(default=30, ge=7, le=90),
    tenant_id: str = Query(default="default")
):
    """Get enrichment analytics"""
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    
    history = [
        e for e in enrichment_history.values()
        if e.get("tenant_id") == tenant_id and e.get("enriched_at", "") >= cutoff
    ]
    
    completed = [e for e in history if e.get("status") == EnrichmentStatus.COMPLETED.value]
    failed = [e for e in history if e.get("status") == EnrichmentStatus.FAILED.value]
    not_found = [e for e in history if e.get("status") == EnrichmentStatus.NOT_FOUND.value]
    
    return {
        "period_days": days,
        "total_enrichments": len(history),
        "successful": len(completed),
        "failed": len(failed),
        "not_found": len(not_found),
        "success_rate": round(len(completed) / max(1, len(history)), 2),
        "by_type": {
            EnrichmentType.CONTACT.value: len([e for e in history if e.get("type") == EnrichmentType.CONTACT.value]),
            EnrichmentType.COMPANY.value: len([e for e in history if e.get("type") == EnrichmentType.COMPANY.value])
        },
        "credits_used": sum(e.get("credits_used", 0) for e in history),
        "avg_fields_enriched": round(sum(len(e.get("fields_enriched", [])) for e in completed) / max(1, len(completed)), 1)
    }


@router.get("/analytics/field-coverage")
async def get_field_coverage_analytics(
    enrichment_type: EnrichmentType,
    days: int = Query(default=30, ge=7, le=90),
    tenant_id: str = Query(default="default")
):
    """Get field coverage analytics"""
    fields = {
        EnrichmentType.CONTACT: ["email", "phone", "title", "linkedin_url", "location", "department"],
        EnrichmentType.COMPANY: ["industry", "employees", "revenue", "technologies", "location", "description"]
    }
    
    field_stats = {
        field: {
            "enriched_count": random.randint(100, 1000),
            "coverage_rate": round(random.uniform(0.4, 0.95), 2),
            "avg_confidence": random.randint(70, 98)
        }
        for field in fields.get(enrichment_type, [])
    }
    
    return {
        "enrichment_type": enrichment_type.value,
        "period_days": days,
        "fields": field_stats,
        "overall_coverage": round(sum(f["coverage_rate"] for f in field_stats.values()) / max(1, len(field_stats)), 2)
    }


# Helper functions
def generate_cache_key(identifier: str) -> str:
    """Generate cache key from identifier"""
    return hashlib.md5(identifier.encode()).hexdigest() if identifier else ""


def generate_contact_enrichment(request: ContactEnrichmentRequest) -> Dict[str, Any]:
    """Generate mock contact enrichment data"""
    if random.random() < 0.1:  # 10% not found
        return {}
    
    first_name = request.first_name or random.choice(["John", "Jane", "Michael", "Sarah", "David"])
    last_name = request.last_name or random.choice(["Smith", "Johnson", "Williams", "Brown", "Jones"])
    
    return {
        "first_name": first_name,
        "last_name": last_name,
        "full_name": f"{first_name} {last_name}",
        "email": request.email or f"{first_name.lower()}.{last_name.lower()}@company.com",
        "phone": f"+1-{random.randint(200,999)}-{random.randint(200,999)}-{random.randint(1000,9999)}",
        "title": random.choice(["VP of Sales", "Director", "Manager", "Senior Account Executive", "CEO"]),
        "department": random.choice(["Sales", "Marketing", "Engineering", "Executive", "Operations"]),
        "seniority": random.choice(["executive", "director", "manager", "individual_contributor"]),
        "linkedin_url": f"https://linkedin.com/in/{first_name.lower()}-{last_name.lower()}-{random.randint(100,999)}",
        "twitter_url": f"https://twitter.com/{first_name.lower()}{last_name.lower()}" if random.random() > 0.5 else None,
        "location": {
            "city": random.choice(["San Francisco", "New York", "Austin", "Seattle", "Boston"]),
            "state": random.choice(["CA", "NY", "TX", "WA", "MA"]),
            "country": "United States"
        },
        "company": {
            "name": request.company_name or f"{last_name} Corp",
            "domain": request.company_domain or f"{last_name.lower()}corp.com"
        },
        "confidence_score": random.randint(75, 99)
    }


def generate_company_enrichment(request: CompanyEnrichmentRequest) -> Dict[str, Any]:
    """Generate mock company enrichment data"""
    if random.random() < 0.1:  # 10% not found
        return {}
    
    company_name = request.company_name or "Example Corp"
    domain = request.domain or f"{company_name.lower().replace(' ', '')}.com"
    
    return {
        "name": company_name,
        "legal_name": f"{company_name}, Inc.",
        "domain": domain,
        "website": f"https://www.{domain}",
        "description": f"{company_name} is a leading provider of innovative solutions.",
        "industry": random.choice(["Technology", "Healthcare", "Finance", "Manufacturing", "Retail"]),
        "sub_industry": random.choice(["SaaS", "Enterprise Software", "Fintech", "E-commerce"]),
        "employees": random.choice([50, 100, 250, 500, 1000, 5000, 10000]),
        "employees_range": random.choice(["11-50", "51-200", "201-500", "501-1000", "1001-5000", "5001-10000"]),
        "revenue": random.choice([1000000, 5000000, 10000000, 50000000, 100000000, 500000000]),
        "revenue_range": random.choice(["$1M-$5M", "$5M-$10M", "$10M-$50M", "$50M-$100M", "$100M-$500M"]),
        "founded_year": random.randint(1990, 2022),
        "type": random.choice(["private", "public", "subsidiary"]),
        "location": {
            "street": f"{random.randint(100,999)} Main Street",
            "city": random.choice(["San Francisco", "New York", "Austin", "Seattle", "Boston"]),
            "state": random.choice(["CA", "NY", "TX", "WA", "MA"]),
            "country": "United States",
            "postal_code": str(random.randint(10000, 99999))
        },
        "technologies": random.sample([
            "AWS", "Google Cloud", "Salesforce", "HubSpot", "Slack", "Zoom",
            "React", "Python", "Node.js", "PostgreSQL", "MongoDB", "Kubernetes"
        ], k=random.randint(3, 8)),
        "social_profiles": {
            "linkedin": f"https://linkedin.com/company/{company_name.lower().replace(' ', '-')}",
            "twitter": f"https://twitter.com/{company_name.lower().replace(' ', '')}",
            "facebook": f"https://facebook.com/{company_name.lower().replace(' ', '')}" if random.random() > 0.5 else None
        },
        "funding": {
            "total_raised": random.choice([0, 5000000, 10000000, 25000000, 50000000, 100000000]),
            "last_round": random.choice(["Seed", "Series A", "Series B", "Series C", None]),
            "last_round_date": (datetime.utcnow() - timedelta(days=random.randint(90, 730))).isoformat()[:10] if random.random() > 0.4 else None
        },
        "confidence_score": random.randint(75, 99)
    }
