"""
Contract Routes - Contract API Endpoints
=========================================
RESTful API for contract lifecycle management.
"""

from datetime import datetime
from typing import Any, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.contracts import ContractService, get_contract_service


router = APIRouter(prefix="/contracts", tags=["Contracts"])


# Request/Response Models
class CreateClauseRequest(BaseModel):
    name: str
    title: str
    content: str
    clause_type: str = "standard"
    category: str = "general"


class CreateTemplateRequest(BaseModel):
    name: str
    description: str
    contract_type: str
    content: str = ""
    clauses: list[str] = []
    variables: list[str] = []
    requires_countersign: bool = True
    expiration_days: int = 30


class UpdateTemplateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    clauses: Optional[list[str]] = None
    is_active: Optional[bool] = None


class CreateContractRequest(BaseModel):
    name: str
    contract_type: str
    template_id: Optional[str] = None
    account_id: Optional[str] = None
    deal_id: Optional[str] = None
    quote_id: Optional[str] = None
    owner_id: Optional[str] = None
    variables: dict[str, Any] = {}
    content: str = ""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    value: float = 0.0
    currency: str = "USD"
    auto_renew: bool = False
    renewal_term_months: int = 12
    requires_countersign: bool = True


class UpdateContractRequest(BaseModel):
    name: Optional[str] = None
    content: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    value: Optional[float] = None
    notes: Optional[str] = None


class AddSignatoryRequest(BaseModel):
    name: str
    email: str
    title: Optional[str] = None
    company: Optional[str] = None
    order: int = 1


class SignContractRequest(BaseModel):
    signature_data: str
    ip_address: Optional[str] = None


class RenewContractRequest(BaseModel):
    new_end_date: datetime
    new_value: Optional[float] = None


# Helper
def get_service() -> ContractService:
    return get_contract_service()


# Clause endpoints
@router.post("/clauses")
async def create_clause(request: CreateClauseRequest):
    """Create a contract clause."""
    service = get_service()
    from src.contracts.contract_service import ClauseType
    
    clause = await service.create_clause(
        name=request.name,
        title=request.title,
        content=request.content,
        clause_type=ClauseType(request.clause_type),
        category=request.category,
    )
    
    return {"clause": clause}


@router.get("/clauses")
async def list_clauses(
    category: Optional[str] = Query(None),
    clause_type: Optional[str] = Query(None)
):
    """List contract clauses."""
    service = get_service()
    from src.contracts.contract_service import ClauseType
    
    type_enum = ClauseType(clause_type) if clause_type else None
    clauses = await service.list_clauses(category=category, clause_type=type_enum)
    
    return {"clauses": clauses, "count": len(clauses)}


@router.get("/clauses/{clause_id}")
async def get_clause(clause_id: str):
    """Get a clause."""
    service = get_service()
    clause = await service.get_clause(clause_id)
    
    if not clause:
        raise HTTPException(status_code=404, detail="Clause not found")
    
    return {"clause": clause}


# Template endpoints
@router.post("/templates")
async def create_template(request: CreateTemplateRequest):
    """Create a contract template."""
    service = get_service()
    from src.contracts.contract_service import ContractType
    
    template = await service.create_template(
        name=request.name,
        description=request.description,
        contract_type=ContractType(request.contract_type),
        content=request.content,
        clauses=request.clauses,
        variables=request.variables,
        requires_countersign=request.requires_countersign,
        expiration_days=request.expiration_days,
    )
    
    return {"template": template}


@router.get("/templates")
async def list_templates(
    contract_type: Optional[str] = Query(None),
    active_only: bool = Query(True)
):
    """List contract templates."""
    service = get_service()
    from src.contracts.contract_service import ContractType
    
    type_enum = ContractType(contract_type) if contract_type else None
    templates = await service.list_templates(contract_type=type_enum, active_only=active_only)
    
    return {"templates": templates, "count": len(templates)}


@router.get("/templates/{template_id}")
async def get_template(template_id: str):
    """Get a template."""
    service = get_service()
    template = await service.get_template(template_id)
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {"template": template}


@router.put("/templates/{template_id}")
async def update_template(template_id: str, request: UpdateTemplateRequest):
    """Update a template."""
    service = get_service()
    
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    template = await service.update_template(template_id, updates)
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {"template": template}


# Contract endpoints
@router.post("")
async def create_contract(request: CreateContractRequest):
    """Create a contract."""
    service = get_service()
    from src.contracts.contract_service import ContractType
    
    contract = await service.create_contract(
        name=request.name,
        contract_type=ContractType(request.contract_type),
        template_id=request.template_id,
        account_id=request.account_id,
        deal_id=request.deal_id,
        owner_id=request.owner_id,
        variables=request.variables,
        content=request.content,
        start_date=request.start_date,
        end_date=request.end_date,
        value=request.value,
        currency=request.currency,
        auto_renew=request.auto_renew,
        renewal_term_months=request.renewal_term_months,
        requires_countersign=request.requires_countersign,
    )
    
    return {"contract": contract}


@router.get("")
async def list_contracts(
    account_id: Optional[str] = Query(None),
    deal_id: Optional[str] = Query(None),
    owner_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    contract_type: Optional[str] = Query(None),
    expiring_within_days: Optional[int] = Query(None),
    limit: int = Query(100, le=1000)
):
    """List contracts."""
    service = get_service()
    from src.contracts.contract_service import ContractStatus, ContractType
    
    status_enum = ContractStatus(status) if status else None
    type_enum = ContractType(contract_type) if contract_type else None
    
    contracts = await service.list_contracts(
        account_id=account_id,
        deal_id=deal_id,
        owner_id=owner_id,
        status=status_enum,
        contract_type=type_enum,
        expiring_within_days=expiring_within_days,
        limit=limit,
    )
    
    return {"contracts": contracts, "count": len(contracts)}


@router.get("/{contract_id}")
async def get_contract(contract_id: str):
    """Get a contract."""
    service = get_service()
    contract = await service.get_contract(contract_id)
    
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    return {"contract": contract}


@router.put("/{contract_id}")
async def update_contract(contract_id: str, request: UpdateContractRequest):
    """Update a contract."""
    service = get_service()
    
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    contract = await service.update_contract(contract_id, updates)
    
    if not contract:
        raise HTTPException(status_code=400, detail="Cannot update contract")
    
    return {"contract": contract}


@router.delete("/{contract_id}")
async def delete_contract(contract_id: str):
    """Delete a contract (draft only)."""
    service = get_service()
    success = await service.delete_contract(contract_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="Cannot delete contract")
    
    return {"deleted": True}


# Signatory endpoints
@router.post("/{contract_id}/signatories")
async def add_signatory(contract_id: str, request: AddSignatoryRequest):
    """Add a signatory to a contract."""
    service = get_service()
    signatory = await service.add_signatory(
        contract_id=contract_id,
        name=request.name,
        email=request.email,
        title=request.title,
        company=request.company,
        order=request.order,
    )
    
    if not signatory:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    return {"signatory": signatory}


@router.delete("/{contract_id}/signatories/{signatory_id}")
async def remove_signatory(contract_id: str, signatory_id: str):
    """Remove a signatory."""
    service = get_service()
    success = await service.remove_signatory(contract_id, signatory_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Not found")
    
    return {"deleted": True}


# Workflow endpoints
@router.post("/{contract_id}/submit")
async def submit_for_review(contract_id: str):
    """Submit contract for review."""
    service = get_service()
    success = await service.submit_for_review(contract_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="Cannot submit contract")
    
    contract = await service.get_contract(contract_id)
    return {"contract": contract}


@router.post("/{contract_id}/approve")
async def approve_contract(contract_id: str, approver_id: str = Query(...)):
    """Approve a contract."""
    service = get_service()
    success = await service.approve_contract(contract_id, approver_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="Cannot approve contract")
    
    contract = await service.get_contract(contract_id)
    return {"contract": contract}


@router.post("/{contract_id}/send")
async def send_for_signature(contract_id: str):
    """Send contract for signature."""
    service = get_service()
    success = await service.send_for_signature(contract_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="Cannot send contract")
    
    contract = await service.get_contract(contract_id)
    return {"contract": contract}


@router.post("/{contract_id}/view")
async def record_view(contract_id: str, signatory_id: str = Query(...)):
    """Record that a signatory viewed the contract."""
    service = get_service()
    success = await service.record_view(contract_id, signatory_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    return {"viewed": True}


@router.post("/{contract_id}/sign/{signatory_id}")
async def sign_contract(
    contract_id: str,
    signatory_id: str,
    request: SignContractRequest
):
    """Sign a contract."""
    service = get_service()
    success = await service.sign_contract(
        contract_id=contract_id,
        signatory_id=signatory_id,
        signature_data=request.signature_data,
        ip_address=request.ip_address,
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Cannot sign contract")
    
    contract = await service.get_contract(contract_id)
    return {"contract": contract}


@router.post("/{contract_id}/countersign")
async def countersign_contract(
    contract_id: str,
    signer_id: str = Query(...),
    signature_data: str = Query(...)
):
    """Countersign a contract."""
    service = get_service()
    success = await service.countersign_contract(contract_id, signer_id, signature_data)
    
    if not success:
        raise HTTPException(status_code=400, detail="Cannot countersign contract")
    
    contract = await service.get_contract(contract_id)
    return {"contract": contract}


@router.post("/{contract_id}/terminate")
async def terminate_contract(contract_id: str, reason: str = Query(...)):
    """Terminate a contract."""
    service = get_service()
    success = await service.terminate_contract(contract_id, reason)
    
    if not success:
        raise HTTPException(status_code=400, detail="Cannot terminate contract")
    
    contract = await service.get_contract(contract_id)
    return {"contract": contract}


@router.post("/{contract_id}/renew")
async def renew_contract(contract_id: str, request: RenewContractRequest):
    """Renew a contract."""
    service = get_service()
    renewal = await service.renew_contract(
        contract_id=contract_id,
        new_end_date=request.new_end_date,
        new_value=request.new_value,
    )
    
    if not renewal:
        raise HTTPException(status_code=400, detail="Cannot renew contract")
    
    return {"renewal": renewal}


# Events
@router.get("/{contract_id}/events")
async def get_events(contract_id: str):
    """Get contract events."""
    service = get_service()
    
    contract = await service.get_contract(contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    events = await service.get_events(contract_id)
    return {"events": events, "count": len(events)}


# Analytics
@router.get("/analytics/summary")
async def get_contract_analytics(
    owner_id: Optional[str] = Query(None),
    period_start: Optional[datetime] = Query(None),
    period_end: Optional[datetime] = Query(None)
):
    """Get contract analytics."""
    service = get_service()
    analytics = await service.get_contract_analytics(
        owner_id=owner_id,
        period_start=period_start,
        period_end=period_end,
    )
    return analytics
