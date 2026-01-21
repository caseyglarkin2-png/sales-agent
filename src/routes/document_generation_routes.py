"""
Document Generation Routes - Proposals, contracts, and document automation
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

router = APIRouter(prefix="/document-generation", tags=["Document Generation"])


class DocumentType(str, Enum):
    PROPOSAL = "proposal"
    QUOTE = "quote"
    CONTRACT = "contract"
    SOW = "sow"
    NDA = "nda"
    MSA = "msa"
    ORDER_FORM = "order_form"
    INVOICE = "invoice"
    PRESENTATION = "presentation"
    ONE_PAGER = "one_pager"


class DocumentStatus(str, Enum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    SENT = "sent"
    VIEWED = "viewed"
    SIGNED = "signed"
    REJECTED = "rejected"
    EXPIRED = "expired"


class TemplateCategory(str, Enum):
    SALES = "sales"
    LEGAL = "legal"
    FINANCE = "finance"
    MARKETING = "marketing"
    ONBOARDING = "onboarding"


class VariableType(str, Enum):
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    CURRENCY = "currency"
    LIST = "list"
    TABLE = "table"
    IMAGE = "image"
    SIGNATURE = "signature"


class OutputFormat(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    HTML = "html"
    PPTX = "pptx"
    XLSX = "xlsx"


# In-memory storage
templates = {}
documents = {}
document_versions = {}
content_blocks = {}
signatures = {}
document_analytics = {}
merge_fields = {}
approvals = {}


class TemplateCreate(BaseModel):
    name: str
    document_type: DocumentType
    category: TemplateCategory
    content: str
    variables: Optional[List[Dict[str, Any]]] = None
    styles: Optional[Dict[str, Any]] = None
    is_default: bool = False


class DocumentCreate(BaseModel):
    template_id: str
    name: str
    opportunity_id: Optional[str] = None
    account_id: Optional[str] = None
    contact_id: Optional[str] = None
    variables: Optional[Dict[str, Any]] = None
    output_format: OutputFormat = OutputFormat.PDF


# Templates
@router.post("/templates")
async def create_template(
    request: TemplateCreate,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Create a document template"""
    template_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    # Extract variables from content
    extracted_vars = extract_variables(request.content)
    
    template = {
        "id": template_id,
        "name": request.name,
        "document_type": request.document_type.value,
        "category": request.category.value,
        "content": request.content,
        "variables": request.variables or extracted_vars,
        "styles": request.styles or {},
        "is_default": request.is_default,
        "version": 1,
        "usage_count": 0,
        "created_by": user_id,
        "tenant_id": tenant_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    templates[template_id] = template
    
    logger.info("template_created", template_id=template_id, type=request.document_type.value)
    return template


@router.get("/templates")
async def list_templates(
    document_type: Optional[DocumentType] = None,
    category: Optional[TemplateCategory] = None,
    search: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """List document templates"""
    result = [t for t in templates.values() if t.get("tenant_id") == tenant_id]
    
    if document_type:
        result = [t for t in result if t.get("document_type") == document_type.value]
    if category:
        result = [t for t in result if t.get("category") == category.value]
    if search:
        search_lower = search.lower()
        result = [t for t in result if search_lower in t.get("name", "").lower()]
    
    result.sort(key=lambda x: x.get("usage_count", 0), reverse=True)
    
    return {"templates": result, "total": len(result)}


@router.get("/templates/{template_id}")
async def get_template(template_id: str):
    """Get template details"""
    if template_id not in templates:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return templates[template_id]


@router.put("/templates/{template_id}")
async def update_template(
    template_id: str,
    name: Optional[str] = None,
    content: Optional[str] = None,
    variables: Optional[List[Dict[str, Any]]] = None,
    styles: Optional[Dict[str, Any]] = None
):
    """Update a template"""
    if template_id not in templates:
        raise HTTPException(status_code=404, detail="Template not found")
    
    template = templates[template_id]
    
    if name is not None:
        template["name"] = name
    if content is not None:
        template["content"] = content
        template["version"] += 1
    if variables is not None:
        template["variables"] = variables
    if styles is not None:
        template["styles"] = styles
    
    template["updated_at"] = datetime.utcnow().isoformat()
    
    return template


@router.post("/templates/{template_id}/clone")
async def clone_template(
    template_id: str,
    new_name: str,
    user_id: str = Query(default="default")
):
    """Clone a template"""
    if template_id not in templates:
        raise HTTPException(status_code=404, detail="Template not found")
    
    source = templates[template_id]
    new_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    cloned = {
        **source,
        "id": new_id,
        "name": new_name,
        "is_default": False,
        "version": 1,
        "usage_count": 0,
        "cloned_from": template_id,
        "created_by": user_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    templates[new_id] = cloned
    
    return cloned


# Documents
@router.post("/documents")
async def create_document(
    request: DocumentCreate,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Create a document from template"""
    if request.template_id not in templates:
        raise HTTPException(status_code=404, detail="Template not found")
    
    template = templates[request.template_id]
    document_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    # Generate document content by merging variables
    content = merge_variables(template["content"], request.variables or {})
    
    document = {
        "id": document_id,
        "name": request.name,
        "template_id": request.template_id,
        "template_name": template["name"],
        "document_type": template["document_type"],
        "opportunity_id": request.opportunity_id,
        "account_id": request.account_id,
        "contact_id": request.contact_id,
        "variables": request.variables or {},
        "content": content,
        "output_format": request.output_format.value,
        "status": DocumentStatus.DRAFT.value,
        "version": 1,
        "views": 0,
        "download_url": f"/api/documents/{document_id}/download",
        "share_url": None,
        "expires_at": None,
        "created_by": user_id,
        "tenant_id": tenant_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    documents[document_id] = document
    
    # Track template usage
    template["usage_count"] = template.get("usage_count", 0) + 1
    
    logger.info("document_created", document_id=document_id, type=template["document_type"])
    return document


@router.get("/documents")
async def list_documents(
    status: Optional[DocumentStatus] = None,
    document_type: Optional[DocumentType] = None,
    opportunity_id: Optional[str] = None,
    account_id: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    offset: int = 0,
    tenant_id: str = Query(default="default")
):
    """List documents"""
    result = [d for d in documents.values() if d.get("tenant_id") == tenant_id]
    
    if status:
        result = [d for d in result if d.get("status") == status.value]
    if document_type:
        result = [d for d in result if d.get("document_type") == document_type.value]
    if opportunity_id:
        result = [d for d in result if d.get("opportunity_id") == opportunity_id]
    if account_id:
        result = [d for d in result if d.get("account_id") == account_id]
    
    result.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return {
        "documents": result[offset:offset + limit],
        "total": len(result),
        "limit": limit,
        "offset": offset
    }


@router.get("/documents/{document_id}")
async def get_document(document_id: str):
    """Get document details"""
    if document_id not in documents:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc = documents[document_id]
    versions = [v for v in document_versions.values() if v.get("document_id") == document_id]
    sigs = [s for s in signatures.values() if s.get("document_id") == document_id]
    
    return {
        **doc,
        "versions": sorted(versions, key=lambda x: x.get("version", 0), reverse=True),
        "signatures": sigs,
        "analytics": document_analytics.get(document_id, {})
    }


@router.put("/documents/{document_id}")
async def update_document(
    document_id: str,
    name: Optional[str] = None,
    variables: Optional[Dict[str, Any]] = None,
    status: Optional[DocumentStatus] = None
):
    """Update a document"""
    if document_id not in documents:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc = documents[document_id]
    now = datetime.utcnow()
    
    # Save version before updating
    version_id = str(uuid.uuid4())
    document_versions[version_id] = {
        "id": version_id,
        "document_id": document_id,
        "version": doc["version"],
        "content": doc["content"],
        "variables": doc["variables"],
        "saved_at": now.isoformat()
    }
    
    if name is not None:
        doc["name"] = name
    if variables is not None:
        doc["variables"] = variables
        # Re-merge content
        template = templates.get(doc["template_id"], {})
        doc["content"] = merge_variables(template.get("content", ""), variables)
    if status is not None:
        doc["status"] = status.value
    
    doc["version"] += 1
    doc["updated_at"] = now.isoformat()
    
    return doc


@router.post("/documents/{document_id}/send")
async def send_document(
    document_id: str,
    recipients: List[Dict[str, str]],
    subject: Optional[str] = None,
    message: Optional[str] = None,
    expires_days: int = 30
):
    """Send document to recipients"""
    if document_id not in documents:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc = documents[document_id]
    now = datetime.utcnow()
    
    # Generate share URL
    share_token = str(uuid.uuid4())[:8]
    doc["share_url"] = f"/documents/share/{share_token}"
    doc["share_token"] = share_token
    doc["expires_at"] = (now + timedelta(days=expires_days)).isoformat()
    doc["status"] = DocumentStatus.SENT.value
    doc["sent_at"] = now.isoformat()
    doc["recipients"] = recipients
    
    logger.info("document_sent", document_id=document_id, recipients=len(recipients))
    
    return {
        "document_id": document_id,
        "share_url": doc["share_url"],
        "sent_to": recipients,
        "expires_at": doc["expires_at"]
    }


@router.post("/documents/{document_id}/view")
async def record_document_view(
    document_id: str,
    viewer_email: Optional[str] = None,
    viewer_ip: Optional[str] = None
):
    """Record a document view"""
    if document_id not in documents:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc = documents[document_id]
    now = datetime.utcnow()
    
    doc["views"] = doc.get("views", 0) + 1
    
    if doc["status"] == DocumentStatus.SENT.value:
        doc["status"] = DocumentStatus.VIEWED.value
        doc["first_viewed_at"] = now.isoformat()
    
    # Track analytics
    if document_id not in document_analytics:
        document_analytics[document_id] = {"views": [], "time_spent": []}
    
    document_analytics[document_id]["views"].append({
        "timestamp": now.isoformat(),
        "viewer_email": viewer_email,
        "viewer_ip": viewer_ip
    })
    
    return {"message": "View recorded", "total_views": doc["views"]}


# E-Signatures
@router.post("/documents/{document_id}/signatures/request")
async def request_signature(
    document_id: str,
    signers: List[Dict[str, Any]],
    signing_order: bool = False,
    reminder_days: int = 3
):
    """Request signatures for a document"""
    if document_id not in documents:
        raise HTTPException(status_code=404, detail="Document not found")
    
    now = datetime.utcnow()
    signature_requests = []
    
    for i, signer in enumerate(signers):
        sig_id = str(uuid.uuid4())
        sig = {
            "id": sig_id,
            "document_id": document_id,
            "signer_name": signer.get("name"),
            "signer_email": signer.get("email"),
            "signer_role": signer.get("role"),
            "order": i + 1 if signing_order else None,
            "status": "pending",
            "sign_url": f"/documents/{document_id}/sign/{sig_id}",
            "reminder_days": reminder_days,
            "requested_at": now.isoformat(),
            "signed_at": None
        }
        
        signatures[sig_id] = sig
        signature_requests.append(sig)
    
    return {
        "document_id": document_id,
        "signature_requests": signature_requests,
        "signing_order": signing_order
    }


@router.post("/documents/{document_id}/signatures/{signature_id}/sign")
async def sign_document(
    document_id: str,
    signature_id: str,
    signature_data: str,
    ip_address: Optional[str] = None
):
    """Sign a document"""
    if signature_id not in signatures:
        raise HTTPException(status_code=404, detail="Signature request not found")
    
    sig = signatures[signature_id]
    if sig["document_id"] != document_id:
        raise HTTPException(status_code=400, detail="Signature mismatch")
    
    now = datetime.utcnow()
    
    sig["status"] = "signed"
    sig["signature_data"] = signature_data
    sig["signed_at"] = now.isoformat()
    sig["ip_address"] = ip_address
    
    # Check if all signatures complete
    doc_sigs = [s for s in signatures.values() if s.get("document_id") == document_id]
    all_signed = all(s.get("status") == "signed" for s in doc_sigs)
    
    if all_signed:
        documents[document_id]["status"] = DocumentStatus.SIGNED.value
        documents[document_id]["completed_at"] = now.isoformat()
    
    logger.info("document_signed", document_id=document_id, signature_id=signature_id)
    
    return {
        "signature_id": signature_id,
        "status": "signed",
        "document_complete": all_signed
    }


# Content Blocks
@router.post("/content-blocks")
async def create_content_block(
    name: str,
    content: str,
    category: str,
    tags: Optional[List[str]] = None,
    tenant_id: str = Query(default="default")
):
    """Create a reusable content block"""
    block_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    block = {
        "id": block_id,
        "name": name,
        "content": content,
        "category": category,
        "tags": tags or [],
        "usage_count": 0,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    content_blocks[block_id] = block
    
    return block


@router.get("/content-blocks")
async def list_content_blocks(
    category: Optional[str] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """List content blocks"""
    result = [b for b in content_blocks.values() if b.get("tenant_id") == tenant_id]
    
    if category:
        result = [b for b in result if b.get("category") == category]
    if tag:
        result = [b for b in result if tag in b.get("tags", [])]
    if search:
        search_lower = search.lower()
        result = [b for b in result if search_lower in b.get("name", "").lower() or search_lower in b.get("content", "").lower()]
    
    return {"content_blocks": result, "total": len(result)}


# Approvals
@router.post("/documents/{document_id}/approvals/request")
async def request_approval(
    document_id: str,
    approvers: List[Dict[str, str]],
    approval_type: str = "sequential"
):
    """Request approval for a document"""
    if document_id not in documents:
        raise HTTPException(status_code=404, detail="Document not found")
    
    now = datetime.utcnow()
    approval_requests = []
    
    for i, approver in enumerate(approvers):
        approval_id = str(uuid.uuid4())
        approval = {
            "id": approval_id,
            "document_id": document_id,
            "approver_id": approver.get("id"),
            "approver_name": approver.get("name"),
            "approver_email": approver.get("email"),
            "order": i + 1 if approval_type == "sequential" else None,
            "status": "pending" if i == 0 or approval_type != "sequential" else "waiting",
            "requested_at": now.isoformat(),
            "responded_at": None,
            "comments": None
        }
        
        approvals[approval_id] = approval
        approval_requests.append(approval)
    
    documents[document_id]["status"] = DocumentStatus.IN_REVIEW.value
    
    return {
        "document_id": document_id,
        "approval_requests": approval_requests,
        "approval_type": approval_type
    }


@router.post("/documents/{document_id}/approvals/{approval_id}/respond")
async def respond_to_approval(
    document_id: str,
    approval_id: str,
    approved: bool,
    comments: Optional[str] = None
):
    """Respond to an approval request"""
    if approval_id not in approvals:
        raise HTTPException(status_code=404, detail="Approval not found")
    
    approval = approvals[approval_id]
    now = datetime.utcnow()
    
    approval["status"] = "approved" if approved else "rejected"
    approval["responded_at"] = now.isoformat()
    approval["comments"] = comments
    
    # Check if all approvals complete
    doc_approvals = [a for a in approvals.values() if a.get("document_id") == document_id]
    
    if not approved:
        documents[document_id]["status"] = DocumentStatus.REJECTED.value
    elif all(a.get("status") == "approved" for a in doc_approvals):
        documents[document_id]["status"] = DocumentStatus.APPROVED.value
    else:
        # Activate next approver in sequence
        for a in sorted(doc_approvals, key=lambda x: x.get("order", 0)):
            if a.get("status") == "waiting":
                a["status"] = "pending"
                break
    
    return approval


# Analytics
@router.get("/analytics/documents")
async def get_document_analytics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Get document analytics"""
    tenant_docs = [d for d in documents.values() if d.get("tenant_id") == tenant_id]
    
    return {
        "total_documents": len(tenant_docs),
        "by_status": {
            status.value: len([d for d in tenant_docs if d.get("status") == status.value])
            for status in DocumentStatus
        },
        "by_type": {
            dtype.value: len([d for d in tenant_docs if d.get("document_type") == dtype.value])
            for dtype in DocumentType
        },
        "avg_time_to_sign_days": round(random.uniform(2, 7), 1),
        "completion_rate": round(random.uniform(0.6, 0.9), 2),
        "avg_views_before_sign": round(random.uniform(3, 8), 1),
        "most_used_templates": sorted(
            [{"id": t["id"], "name": t["name"], "usage": t.get("usage_count", 0)} 
             for t in templates.values() if t.get("tenant_id") == tenant_id],
            key=lambda x: x["usage"], reverse=True
        )[:5]
    }


@router.get("/analytics/templates/{template_id}")
async def get_template_analytics(template_id: str):
    """Get analytics for a specific template"""
    if template_id not in templates:
        raise HTTPException(status_code=404, detail="Template not found")
    
    template = templates[template_id]
    template_docs = [d for d in documents.values() if d.get("template_id") == template_id]
    
    return {
        "template_id": template_id,
        "template_name": template["name"],
        "total_documents": len(template_docs),
        "documents_sent": len([d for d in template_docs if d.get("status") in ["sent", "viewed", "signed"]]),
        "documents_signed": len([d for d in template_docs if d.get("status") == "signed"]),
        "sign_rate": round(random.uniform(0.5, 0.9), 2),
        "avg_sign_time_days": round(random.uniform(1, 5), 1),
        "usage_trend": [
            {"period": (datetime.utcnow() - timedelta(days=30*i)).strftime("%Y-%m"), "count": random.randint(5, 30)}
            for i in range(6)
        ]
    }


# Bulk Operations
@router.post("/documents/bulk-generate")
async def bulk_generate_documents(
    template_id: str,
    records: List[Dict[str, Any]],
    name_pattern: str = "{company_name} - Document",
    output_format: OutputFormat = OutputFormat.PDF,
    tenant_id: str = Query(default="default")
):
    """Generate multiple documents from a template"""
    if template_id not in templates:
        raise HTTPException(status_code=404, detail="Template not found")
    
    generated = []
    for record in records:
        doc_name = name_pattern.format(**record)
        
        doc_request = DocumentCreate(
            template_id=template_id,
            name=doc_name,
            variables=record,
            output_format=output_format
        )
        
        doc = await create_document(request=doc_request, tenant_id=tenant_id)
        generated.append(doc)
    
    return {
        "generated_count": len(generated),
        "documents": generated
    }


# Helper functions
def extract_variables(content: str) -> List[Dict]:
    """Extract variables from template content"""
    import re
    variables = []
    pattern = r'\{\{(\w+)\}\}'
    matches = re.findall(pattern, content)
    
    for match in set(matches):
        variables.append({
            "name": match,
            "type": "text",
            "required": True
        })
    
    return variables


def merge_variables(content: str, variables: Dict) -> str:
    """Merge variables into template content"""
    result = content
    for key, value in variables.items():
        result = result.replace(f"{{{{{key}}}}}", str(value))
    return result
