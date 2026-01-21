"""
Contract Lifecycle Routes - Contract management, renewals, and e-signatures
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from enum import Enum
import structlog
import uuid
import random

logger = structlog.get_logger()

router = APIRouter(prefix="/contracts-v2", tags=["Contract Lifecycle V2"])


class ContractStatus(str, Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    IN_NEGOTIATION = "in_negotiation"
    PENDING_SIGNATURE = "pending_signature"
    EXECUTED = "executed"
    ACTIVE = "active"
    EXPIRED = "expired"
    TERMINATED = "terminated"


class ContractType(str, Enum):
    MSA = "msa"
    ORDER_FORM = "order_form"
    SOW = "sow"
    NDA = "nda"
    AMENDMENT = "amendment"
    RENEWAL = "renewal"


class SignatureStatus(str, Enum):
    NOT_SENT = "not_sent"
    SENT = "sent"
    VIEWED = "viewed"
    SIGNED = "signed"
    DECLINED = "declined"
    EXPIRED = "expired"


class RenewalStatus(str, Enum):
    NOT_DUE = "not_due"
    UPCOMING = "upcoming"
    IN_PROGRESS = "in_progress"
    RENEWED = "renewed"
    CHURNED = "churned"


# In-memory storage
contracts = {}
contract_templates = {}
signatories = {}
renewals = {}


class SignatoryCreate(BaseModel):
    name: str
    email: str
    title: str
    order: int = 1


class ContractCreate(BaseModel):
    contract_type: ContractType
    account_id: str
    account_name: str
    deal_id: Optional[str] = None
    title: str
    value: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    auto_renew: bool = False
    payment_terms: str = "Net 30"
    signatories: List[SignatoryCreate] = []


class ClauseCreate(BaseModel):
    clause_type: str
    title: str
    content: str
    is_negotiable: bool = True


# Contract CRUD
@router.post("/")
async def create_contract(
    request: ContractCreate,
    tenant_id: str = Query(default="default")
):
    """Create a new contract"""
    contract_id = str(uuid.uuid4())
    contract_number = f"C-{datetime.utcnow().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
    now = datetime.utcnow()
    
    contract = {
        "id": contract_id,
        "contract_number": contract_number,
        "contract_type": request.contract_type.value,
        "account_id": request.account_id,
        "account_name": request.account_name,
        "deal_id": request.deal_id,
        "title": request.title,
        "value": request.value,
        "status": ContractStatus.DRAFT.value,
        "start_date": request.start_date.isoformat() if request.start_date else None,
        "end_date": request.end_date.isoformat() if request.end_date else None,
        "auto_renew": request.auto_renew,
        "payment_terms": request.payment_terms,
        "signatories": [
            {
                "id": str(uuid.uuid4()),
                "name": s.name,
                "email": s.email,
                "title": s.title,
                "order": s.order,
                "signature_status": SignatureStatus.NOT_SENT.value
            }
            for s in request.signatories
        ],
        "clauses": [],
        "versions": [{"version": 1, "created_at": now.isoformat(), "changes": "Initial draft"}],
        "current_version": 1,
        "tenant_id": tenant_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    contracts[contract_id] = contract
    
    return contract


@router.get("/{contract_id}")
async def get_contract(
    contract_id: str,
    tenant_id: str = Query(default="default")
):
    """Get contract by ID"""
    contract = contracts.get(contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return contract


@router.get("/")
async def list_contracts(
    account_id: Optional[str] = None,
    status: Optional[ContractStatus] = None,
    contract_type: Optional[ContractType] = None,
    expiring_within_days: Optional[int] = None,
    limit: int = Query(default=50, le=100),
    tenant_id: str = Query(default="default")
):
    """List contracts"""
    result = [c for c in contracts.values() if c.get("tenant_id") == tenant_id]
    
    if account_id:
        result = [c for c in result if c.get("account_id") == account_id]
    if status:
        result = [c for c in result if c.get("status") == status.value]
    if contract_type:
        result = [c for c in result if c.get("contract_type") == contract_type.value]
    
    return {"contracts": result[:limit], "total": len(result)}


# Signature Management
@router.post("/{contract_id}/send-for-signature")
async def send_for_signature(
    contract_id: str,
    message: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Send contract for e-signature"""
    contract = contracts.get(contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    now = datetime.utcnow()
    
    for signatory in contract.get("signatories", []):
        signatory["signature_status"] = SignatureStatus.SENT.value
        signatory["sent_at"] = now.isoformat()
    
    contract["status"] = ContractStatus.PENDING_SIGNATURE.value
    contract["signature_request_sent_at"] = now.isoformat()
    
    return {
        "contract_id": contract_id,
        "status": "sent_for_signature",
        "sent_to": [s["email"] for s in contract.get("signatories", [])],
        "sent_at": now.isoformat()
    }


@router.post("/{contract_id}/signatories/{signatory_id}/sign")
async def record_signature(
    contract_id: str,
    signatory_id: str,
    ip_address: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Record a signature from a signatory"""
    contract = contracts.get(contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    now = datetime.utcnow()
    
    for signatory in contract.get("signatories", []):
        if signatory["id"] == signatory_id:
            signatory["signature_status"] = SignatureStatus.SIGNED.value
            signatory["signed_at"] = now.isoformat()
            signatory["ip_address"] = ip_address
            break
    
    # Check if all signed
    all_signed = all(
        s["signature_status"] == SignatureStatus.SIGNED.value 
        for s in contract.get("signatories", [])
    )
    
    if all_signed:
        contract["status"] = ContractStatus.EXECUTED.value
        contract["executed_at"] = now.isoformat()
    
    return {
        "contract_id": contract_id,
        "signatory_id": signatory_id,
        "status": "signed",
        "all_signed": all_signed,
        "contract_status": contract["status"]
    }


@router.get("/{contract_id}/signature-status")
async def get_signature_status(
    contract_id: str,
    tenant_id: str = Query(default="default")
):
    """Get signature status for a contract"""
    contract = contracts.get(contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    return {
        "contract_id": contract_id,
        "contract_status": contract.get("status"),
        "signatories": contract.get("signatories", []),
        "all_signed": all(
            s["signature_status"] == SignatureStatus.SIGNED.value 
            for s in contract.get("signatories", [])
        ),
        "signatures_received": sum(
            1 for s in contract.get("signatories", []) 
            if s["signature_status"] == SignatureStatus.SIGNED.value
        ),
        "signatures_pending": sum(
            1 for s in contract.get("signatories", []) 
            if s["signature_status"] in [SignatureStatus.SENT.value, SignatureStatus.VIEWED.value]
        )
    }


# Renewals
@router.get("/renewals/upcoming")
async def get_upcoming_renewals(
    days_ahead: int = Query(default=90),
    tenant_id: str = Query(default="default")
):
    """Get contracts due for renewal"""
    now = datetime.utcnow()
    upcoming = []
    
    for contract in contracts.values():
        if contract.get("tenant_id") != tenant_id:
            continue
        if contract.get("status") not in [ContractStatus.ACTIVE.value, ContractStatus.EXECUTED.value]:
            continue
        if contract.get("end_date"):
            end_date = datetime.fromisoformat(contract["end_date"].replace("Z", "+00:00").replace("+00:00", ""))
            days_until = (end_date - now).days
            if 0 < days_until <= days_ahead:
                upcoming.append({
                    "contract_id": contract["id"],
                    "contract_number": contract["contract_number"],
                    "account_name": contract["account_name"],
                    "value": contract.get("value"),
                    "end_date": contract["end_date"],
                    "days_until_expiry": days_until,
                    "auto_renew": contract.get("auto_renew", False),
                    "renewal_status": RenewalStatus.UPCOMING.value
                })
    
    # Add mock data if empty
    if not upcoming:
        for i in range(5):
            days = random.randint(10, days_ahead)
            upcoming.append({
                "contract_id": str(uuid.uuid4()),
                "contract_number": f"C-2024-{random.randint(1000, 9999)}",
                "account_name": f"Account {i + 1}",
                "value": random.randint(30000, 200000),
                "end_date": (now + timedelta(days=days)).isoformat(),
                "days_until_expiry": days,
                "auto_renew": random.choice([True, False]),
                "renewal_status": RenewalStatus.UPCOMING.value
            })
    
    upcoming.sort(key=lambda x: x["days_until_expiry"])
    
    return {
        "upcoming_renewals": upcoming,
        "total": len(upcoming),
        "total_value_at_risk": sum(r.get("value", 0) or 0 for r in upcoming)
    }


@router.post("/{contract_id}/initiate-renewal")
async def initiate_renewal(
    contract_id: str,
    new_value: Optional[float] = None,
    new_term_months: int = 12,
    tenant_id: str = Query(default="default")
):
    """Initiate renewal process for a contract"""
    contract = contracts.get(contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    renewal_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    renewal = {
        "id": renewal_id,
        "original_contract_id": contract_id,
        "account_id": contract["account_id"],
        "account_name": contract["account_name"],
        "original_value": contract.get("value"),
        "proposed_value": new_value or contract.get("value"),
        "new_term_months": new_term_months,
        "status": RenewalStatus.IN_PROGRESS.value,
        "initiated_at": now.isoformat()
    }
    
    renewals[renewal_id] = renewal
    
    return renewal


# Clauses
@router.post("/{contract_id}/clauses")
async def add_clause(
    contract_id: str,
    request: ClauseCreate,
    tenant_id: str = Query(default="default")
):
    """Add a clause to a contract"""
    contract = contracts.get(contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    clause = {
        "id": str(uuid.uuid4()),
        "clause_type": request.clause_type,
        "title": request.title,
        "content": request.content,
        "is_negotiable": request.is_negotiable,
        "added_at": datetime.utcnow().isoformat()
    }
    
    contract["clauses"].append(clause)
    contract["updated_at"] = datetime.utcnow().isoformat()
    
    return clause


@router.get("/{contract_id}/clauses")
async def get_clauses(
    contract_id: str,
    tenant_id: str = Query(default="default")
):
    """Get clauses for a contract"""
    contract = contracts.get(contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    return {"clauses": contract.get("clauses", [])}


# Templates
@router.post("/templates")
async def create_template(
    name: str,
    contract_type: ContractType,
    content: str,
    default_clauses: List[Dict[str, Any]] = [],
    tenant_id: str = Query(default="default")
):
    """Create a contract template"""
    template_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    template = {
        "id": template_id,
        "name": name,
        "contract_type": contract_type.value,
        "content": content,
        "default_clauses": default_clauses,
        "usage_count": 0,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    contract_templates[template_id] = template
    
    return template


@router.get("/templates")
async def list_templates(
    contract_type: Optional[ContractType] = None,
    tenant_id: str = Query(default="default")
):
    """List contract templates"""
    result = [t for t in contract_templates.values() if t.get("tenant_id") == tenant_id]
    
    if contract_type:
        result = [t for t in result if t.get("contract_type") == contract_type.value]
    
    return {"templates": result, "total": len(result)}


# Versioning
@router.post("/{contract_id}/versions")
async def create_version(
    contract_id: str,
    changes: str,
    tenant_id: str = Query(default="default")
):
    """Create a new version of a contract"""
    contract = contracts.get(contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    new_version = contract["current_version"] + 1
    now = datetime.utcnow()
    
    contract["versions"].append({
        "version": new_version,
        "created_at": now.isoformat(),
        "changes": changes
    })
    contract["current_version"] = new_version
    contract["updated_at"] = now.isoformat()
    
    return {
        "contract_id": contract_id,
        "version": new_version,
        "created_at": now.isoformat()
    }


@router.get("/{contract_id}/versions")
async def get_versions(
    contract_id: str,
    tenant_id: str = Query(default="default")
):
    """Get version history for a contract"""
    contract = contracts.get(contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    return {
        "contract_id": contract_id,
        "current_version": contract["current_version"],
        "versions": contract.get("versions", [])
    }


# Analytics
@router.get("/analytics")
async def get_contract_analytics(
    period: str = Query(default="quarter"),
    tenant_id: str = Query(default="default")
):
    """Get contract analytics"""
    return {
        "period": period,
        "generated_at": datetime.utcnow().isoformat(),
        "summary": {
            "total_contracts": random.randint(100, 300),
            "active_contracts": random.randint(80, 200),
            "total_contract_value": random.randint(5000000, 20000000),
            "avg_contract_value": random.randint(50000, 150000),
            "contracts_executed_this_period": random.randint(15, 50),
            "contracts_expired": random.randint(5, 20)
        },
        "signature_metrics": {
            "avg_time_to_signature_hours": round(random.uniform(12, 72), 1),
            "signature_completion_rate": round(random.uniform(0.85, 0.98), 2),
            "pending_signatures": random.randint(5, 25)
        },
        "renewal_metrics": {
            "renewal_rate": round(random.uniform(0.80, 0.95), 2),
            "upcoming_renewals_30d": random.randint(5, 20),
            "upcoming_renewal_value_30d": random.randint(200000, 1000000),
            "at_risk_renewals": random.randint(2, 10)
        },
        "type_breakdown": [
            {"type": ContractType.MSA.value, "count": random.randint(20, 50), "value": random.randint(1000000, 5000000)},
            {"type": ContractType.ORDER_FORM.value, "count": random.randint(50, 150), "value": random.randint(2000000, 8000000)},
            {"type": ContractType.SOW.value, "count": random.randint(15, 40), "value": random.randint(500000, 2000000)},
            {"type": ContractType.NDA.value, "count": random.randint(30, 80), "value": 0}
        ]
    }
