"""
Data Quality Routes - Deduplication and data hygiene
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

router = APIRouter(prefix="/data-quality", tags=["Data Quality"])


class RecordType(str, Enum):
    CONTACT = "contact"
    ACCOUNT = "account"
    LEAD = "lead"
    OPPORTUNITY = "opportunity"


class MatchConfidence(str, Enum):
    EXACT = "exact"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class MergeStrategy(str, Enum):
    KEEP_MASTER = "keep_master"
    KEEP_NEWEST = "keep_newest"
    KEEP_OLDEST = "keep_oldest"
    MERGE_FIELDS = "merge_fields"
    MANUAL = "manual"


class ValidationRule(str, Enum):
    REQUIRED = "required"
    EMAIL_FORMAT = "email_format"
    PHONE_FORMAT = "phone_format"
    URL_FORMAT = "url_format"
    DOMAIN_MATCH = "domain_match"
    NO_PERSONAL_EMAIL = "no_personal_email"
    COMPLETENESS = "completeness"


class DuplicateSearchRequest(BaseModel):
    record_type: RecordType
    field_weights: Optional[Dict[str, float]] = None
    min_confidence: MatchConfidence = MatchConfidence.MEDIUM
    include_merged: bool = False


class MergeRequest(BaseModel):
    master_id: str
    duplicate_ids: List[str]
    record_type: RecordType
    strategy: MergeStrategy = MergeStrategy.KEEP_MASTER
    field_overrides: Optional[Dict[str, str]] = None


class ValidationRuleCreate(BaseModel):
    name: str
    record_type: RecordType
    field: str
    rule_type: ValidationRule
    parameters: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    is_blocking: bool = False


# In-memory storage
duplicate_sets = {}
merge_history = {}
validation_rules = {}
validation_results = {}
data_quality_scores = {}
enrichment_jobs = {}
field_completeness = {}


# Duplicate Detection
@router.post("/duplicates/search")
async def search_duplicates(
    request: DuplicateSearchRequest,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Search for duplicates"""
    job_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    # Mock duplicate detection
    duplicates = generate_mock_duplicates(request.record_type, request.min_confidence)
    
    result = {
        "job_id": job_id,
        "record_type": request.record_type.value,
        "min_confidence": request.min_confidence.value,
        "duplicate_sets": duplicates,
        "total_sets": len(duplicates),
        "total_duplicates": sum(len(d["records"]) for d in duplicates),
        "searched_at": now.isoformat()
    }
    
    # Store for later retrieval
    duplicate_sets[job_id] = result
    
    logger.info("duplicate_search_completed", job_id=job_id, sets_found=len(duplicates))
    return result


@router.get("/duplicates/jobs/{job_id}")
async def get_duplicate_job_results(job_id: str):
    """Get results of a duplicate search job"""
    if job_id not in duplicate_sets:
        raise HTTPException(status_code=404, detail="Job not found")
    return duplicate_sets[job_id]


@router.get("/duplicates/sets")
async def list_duplicate_sets(
    record_type: Optional[RecordType] = None,
    status: Optional[str] = None,
    min_confidence: Optional[MatchConfidence] = None,
    limit: int = Query(default=50, le=100),
    tenant_id: str = Query(default="default")
):
    """List unresolved duplicate sets"""
    result = []
    
    for job in duplicate_sets.values():
        for dup_set in job.get("duplicate_sets", []):
            if record_type and dup_set.get("record_type") != record_type.value:
                continue
            if status and dup_set.get("status") != status:
                continue
            result.append(dup_set)
    
    return {"duplicate_sets": result[:limit], "total": len(result)}


@router.post("/duplicates/merge")
async def merge_duplicates(
    request: MergeRequest,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Merge duplicate records"""
    merge_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    # Record merge
    merge_record = {
        "id": merge_id,
        "master_id": request.master_id,
        "merged_ids": request.duplicate_ids,
        "record_type": request.record_type.value,
        "strategy": request.strategy.value,
        "field_overrides": request.field_overrides,
        "merged_by": user_id,
        "tenant_id": tenant_id,
        "merged_at": now.isoformat()
    }
    
    merge_history[merge_id] = merge_record
    
    logger.info("records_merged", merge_id=merge_id, master_id=request.master_id)
    
    return {
        "status": "merged",
        "merge_id": merge_id,
        "master_record_id": request.master_id,
        "records_merged": len(request.duplicate_ids)
    }


@router.post("/duplicates/sets/{set_id}/dismiss")
async def dismiss_duplicate_set(set_id: str, reason: Optional[str] = None, user_id: str = Query(default="default")):
    """Dismiss a duplicate set as not duplicates"""
    # Find and update the set
    for job in duplicate_sets.values():
        for dup_set in job.get("duplicate_sets", []):
            if dup_set.get("id") == set_id:
                dup_set["status"] = "dismissed"
                dup_set["dismissed_by"] = user_id
                dup_set["dismiss_reason"] = reason
                dup_set["dismissed_at"] = datetime.utcnow().isoformat()
                return dup_set
    
    raise HTTPException(status_code=404, detail="Duplicate set not found")


@router.get("/merge-history")
async def get_merge_history(
    record_type: Optional[RecordType] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    tenant_id: str = Query(default="default")
):
    """Get merge history"""
    result = [m for m in merge_history.values() if m.get("tenant_id") == tenant_id]
    
    if record_type:
        result = [m for m in result if m.get("record_type") == record_type.value]
    if start_date:
        result = [m for m in result if m.get("merged_at", "") >= start_date]
    if end_date:
        result = [m for m in result if m.get("merged_at", "") <= end_date]
    
    result.sort(key=lambda x: x.get("merged_at", ""), reverse=True)
    
    return {"merges": result[:limit], "total": len(result)}


# Data Validation
@router.post("/validation/rules")
async def create_validation_rule(
    request: ValidationRuleCreate,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Create a data validation rule"""
    rule_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    rule = {
        "id": rule_id,
        "name": request.name,
        "record_type": request.record_type.value,
        "field": request.field,
        "rule_type": request.rule_type.value,
        "parameters": request.parameters or {},
        "error_message": request.error_message,
        "is_blocking": request.is_blocking,
        "is_active": True,
        "violations_count": 0,
        "created_by": user_id,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    validation_rules[rule_id] = rule
    
    return rule


@router.get("/validation/rules")
async def list_validation_rules(
    record_type: Optional[RecordType] = None,
    is_active: Optional[bool] = None,
    tenant_id: str = Query(default="default")
):
    """List validation rules"""
    result = [r for r in validation_rules.values() if r.get("tenant_id") == tenant_id]
    
    if record_type:
        result = [r for r in result if r.get("record_type") == record_type.value]
    if is_active is not None:
        result = [r for r in result if r.get("is_active") == is_active]
    
    return {"rules": result, "total": len(result)}


@router.post("/validation/run")
async def run_validation(
    record_type: RecordType,
    tenant_id: str = Query(default="default")
):
    """Run validation rules on records"""
    job_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    # Mock validation results
    rules = [r for r in validation_rules.values() if r.get("record_type") == record_type.value and r.get("is_active")]
    
    violations = []
    for rule in rules:
        rule_violations = random.randint(0, 50)
        for _ in range(min(5, rule_violations)):
            violations.append({
                "id": str(uuid.uuid4()),
                "rule_id": rule["id"],
                "rule_name": rule["name"],
                "record_id": str(uuid.uuid4()),
                "field": rule["field"],
                "current_value": "invalid_value",
                "error_message": rule.get("error_message", f"Validation failed for {rule['field']}"),
                "is_blocking": rule.get("is_blocking", False)
            })
    
    result = {
        "job_id": job_id,
        "record_type": record_type.value,
        "rules_evaluated": len(rules),
        "total_violations": len(violations),
        "violations": violations[:50],
        "run_at": now.isoformat()
    }
    
    validation_results[job_id] = result
    
    logger.info("validation_completed", job_id=job_id, violations=len(violations))
    return result


@router.get("/validation/results/{job_id}")
async def get_validation_results(job_id: str):
    """Get validation job results"""
    if job_id not in validation_results:
        raise HTTPException(status_code=404, detail="Job not found")
    return validation_results[job_id]


# Field Completeness
@router.get("/completeness/{record_type}")
async def get_field_completeness(record_type: RecordType, tenant_id: str = Query(default="default")):
    """Get field completeness analysis"""
    fields = get_record_type_fields(record_type)
    
    completeness = {
        "record_type": record_type.value,
        "total_records": random.randint(1000, 10000),
        "fields": {
            field: {
                "completed_count": random.randint(500, 9000),
                "completion_rate": round(random.uniform(0.4, 0.99), 2),
                "empty_count": random.randint(100, 2000),
                "invalid_count": random.randint(0, 500)
            }
            for field in fields
        },
        "overall_completeness": round(random.uniform(0.65, 0.95), 2),
        "analyzed_at": datetime.utcnow().isoformat()
    }
    
    field_completeness[f"{tenant_id}_{record_type.value}"] = completeness
    
    return completeness


@router.get("/completeness/{record_type}/records")
async def get_incomplete_records(
    record_type: RecordType,
    field: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    tenant_id: str = Query(default="default")
):
    """Get records with missing data"""
    incomplete = [
        {
            "record_id": str(uuid.uuid4()),
            "name": f"Record {i}",
            "missing_fields": random.sample(get_record_type_fields(record_type), k=random.randint(1, 3)),
            "completeness_score": round(random.uniform(0.3, 0.7), 2),
            "created_at": (datetime.utcnow() - timedelta(days=random.randint(1, 90))).isoformat()
        }
        for i in range(limit)
    ]
    
    if field:
        incomplete = [r for r in incomplete if field in r.get("missing_fields", [])]
    
    return {"records": incomplete[:limit], "total": len(incomplete)}


# Data Quality Score
@router.get("/score/{record_type}")
async def get_data_quality_score(record_type: RecordType, tenant_id: str = Query(default="default")):
    """Get overall data quality score"""
    score = {
        "record_type": record_type.value,
        "overall_score": random.randint(60, 95),
        "dimensions": {
            "completeness": random.randint(55, 95),
            "accuracy": random.randint(70, 98),
            "consistency": random.randint(65, 95),
            "uniqueness": random.randint(80, 99),
            "timeliness": random.randint(60, 90),
            "validity": random.randint(70, 95)
        },
        "trend": random.choice(["improving", "stable", "declining"]),
        "change_from_last_month": random.randint(-5, 10),
        "calculated_at": datetime.utcnow().isoformat()
    }
    
    data_quality_scores[f"{tenant_id}_{record_type.value}"] = score
    
    return score


@router.get("/score/trends")
async def get_quality_score_trends(
    record_type: RecordType,
    days: int = Query(default=30, ge=7, le=90),
    tenant_id: str = Query(default="default")
):
    """Get data quality score trends"""
    trend_data = []
    base_score = random.randint(60, 80)
    
    for i in range(days, 0, -7):
        date = (datetime.utcnow() - timedelta(days=i)).isoformat()[:10]
        trend_data.append({
            "date": date,
            "overall_score": min(100, max(0, base_score + random.randint(-3, 5))),
            "completeness": min(100, max(0, base_score - 5 + random.randint(-3, 5))),
            "accuracy": min(100, max(0, base_score + 5 + random.randint(-2, 3)))
        })
        base_score = trend_data[-1]["overall_score"]
    
    return {
        "record_type": record_type.value,
        "period_days": days,
        "trends": trend_data
    }


# Bulk Operations
@router.post("/bulk/normalize")
async def normalize_records(
    record_type: RecordType,
    normalizations: List[str],  # phone, email, address, name, company_name
    tenant_id: str = Query(default="default"),
    user_id: str = Query(default="default")
):
    """Normalize record fields"""
    job_id = str(uuid.uuid4())
    
    result = {
        "job_id": job_id,
        "record_type": record_type.value,
        "normalizations_applied": normalizations,
        "records_processed": random.randint(500, 5000),
        "records_updated": random.randint(100, 1000),
        "status": "completed",
        "completed_at": datetime.utcnow().isoformat()
    }
    
    logger.info("normalization_completed", job_id=job_id)
    return result


@router.post("/bulk/cleanup")
async def cleanup_records(
    record_type: RecordType,
    operations: List[str],  # remove_junk, fix_casing, trim_whitespace, remove_duplicates
    dry_run: bool = True,
    tenant_id: str = Query(default="default"),
    user_id: str = Query(default="default")
):
    """Clean up record data"""
    job_id = str(uuid.uuid4())
    
    affected_records = random.randint(100, 2000)
    
    result = {
        "job_id": job_id,
        "record_type": record_type.value,
        "operations": operations,
        "dry_run": dry_run,
        "affected_records": affected_records,
        "status": "preview" if dry_run else "completed",
        "preview": [
            {
                "record_id": str(uuid.uuid4()),
                "field": random.choice(["name", "email", "phone", "company"]),
                "before": "Old Value  ",
                "after": "Old Value"
            }
            for _ in range(min(10, affected_records))
        ] if dry_run else None,
        "processed_at": datetime.utcnow().isoformat()
    }
    
    return result


# Analytics
@router.get("/analytics/overview")
async def get_data_quality_overview(tenant_id: str = Query(default="default")):
    """Get data quality overview"""
    return {
        "overall_health": random.randint(70, 90),
        "by_record_type": {
            rt.value: {
                "total_records": random.randint(1000, 50000),
                "quality_score": random.randint(60, 95),
                "duplicate_rate": round(random.uniform(0.01, 0.15), 3),
                "completeness_rate": round(random.uniform(0.65, 0.95), 2)
            }
            for rt in RecordType
        },
        "recent_merges": random.randint(10, 100),
        "validation_violations": random.randint(50, 500),
        "incomplete_records": random.randint(200, 2000),
        "last_scan": datetime.utcnow().isoformat()
    }


@router.get("/analytics/duplicate-trends")
async def get_duplicate_trends(
    days: int = Query(default=30, ge=7, le=90),
    tenant_id: str = Query(default="default")
):
    """Get duplicate detection trends"""
    trend_data = []
    
    for i in range(days, 0, -7):
        date = (datetime.utcnow() - timedelta(days=i)).isoformat()[:10]
        trend_data.append({
            "date": date,
            "duplicates_found": random.randint(10, 100),
            "duplicates_merged": random.randint(5, 80),
            "duplicates_dismissed": random.randint(1, 20)
        })
    
    return {
        "period_days": days,
        "trends": trend_data,
        "total_found": sum(t["duplicates_found"] for t in trend_data),
        "total_resolved": sum(t["duplicates_merged"] + t["duplicates_dismissed"] for t in trend_data)
    }


# Helper functions
def generate_mock_duplicates(record_type: RecordType, min_confidence: MatchConfidence) -> List[Dict]:
    """Generate mock duplicate sets"""
    num_sets = random.randint(5, 20)
    
    confidence_scores = {
        MatchConfidence.EXACT: (0.95, 1.0),
        MatchConfidence.HIGH: (0.85, 0.95),
        MatchConfidence.MEDIUM: (0.70, 0.85),
        MatchConfidence.LOW: (0.50, 0.70)
    }
    
    min_score = confidence_scores[min_confidence][0]
    
    duplicates = []
    for _ in range(num_sets):
        score = round(random.uniform(min_score, 1.0), 2)
        confidence = (
            MatchConfidence.EXACT.value if score >= 0.95
            else MatchConfidence.HIGH.value if score >= 0.85
            else MatchConfidence.MEDIUM.value if score >= 0.70
            else MatchConfidence.LOW.value
        )
        
        num_records = random.randint(2, 4)
        duplicates.append({
            "id": str(uuid.uuid4()),
            "record_type": record_type.value,
            "confidence": confidence,
            "score": score,
            "match_fields": random.sample(["email", "name", "phone", "company", "domain"], k=random.randint(1, 3)),
            "status": "pending",
            "records": [
                {
                    "id": str(uuid.uuid4()),
                    "name": f"Record {i}",
                    "email": f"user{random.randint(1,100)}@company.com",
                    "created_at": (datetime.utcnow() - timedelta(days=random.randint(1, 365))).isoformat()
                }
                for i in range(num_records)
            ]
        })
    
    return duplicates


def get_record_type_fields(record_type: RecordType) -> List[str]:
    """Get fields for a record type"""
    fields = {
        RecordType.CONTACT: ["email", "first_name", "last_name", "phone", "title", "company", "linkedin_url"],
        RecordType.ACCOUNT: ["name", "website", "industry", "employees", "revenue", "address", "phone"],
        RecordType.LEAD: ["email", "name", "company", "phone", "source", "status", "score"],
        RecordType.OPPORTUNITY: ["name", "amount", "stage", "close_date", "probability", "owner", "account"]
    }
    return fields.get(record_type, [])
