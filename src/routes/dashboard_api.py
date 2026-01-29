"""
Dashboard API endpoints for operator visibility.

Provides workflow status, draft approval, and system metrics.
"""
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from src.db import get_session
from src.logger import get_logger
from src.models.workflow import Workflow, WorkflowStatus
from src.models.form_submission import FormSubmission
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

logger = get_logger(__name__)
router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


class WorkflowListItem(BaseModel):
    """Workflow item for list view."""
    id: str
    status: str
    prospect_email: str
    prospect_name: Optional[str] = None
    prospect_company: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    final_status: Optional[str] = None
    
    class Config:
        from_attributes = True


class WorkflowListResponse(BaseModel):
    """Paginated workflow list."""
    workflows: list[WorkflowListItem]
    total: int
    page: int
    page_size: int


class WorkflowDetailResponse(BaseModel):
    """Detailed workflow information."""
    id: str
    status: str
    mode: str
    prospect_email: str
    prospect_name: Optional[str] = None
    prospect_company: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    final_status: Optional[str] = None
    form_id: str
    portal_id: int
    raw_payload: dict
    error_count: int = 0
    
    class Config:
        from_attributes = True


class DashboardStatsResponse(BaseModel):
    """Dashboard statistics."""
    total_workflows: int
    pending_workflows: int
    completed_workflows: int
    failed_workflows: int
    pending_approvals: int
    success_rate: float


@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats():
    """
    Get dashboard statistics.
    
    Returns:
        Current workflow counts and metrics
    """
    async with get_session() as session:
        # Count workflows by status
        total_result = await session.execute(select(func.count(Workflow.id)))
        total_workflows = total_result.scalar() or 0
        
        pending_result = await session.execute(
            select(func.count(Workflow.id)).where(
                Workflow.status.in_([WorkflowStatus.TRIGGERED, WorkflowStatus.PROCESSING])
            )
        )
        pending_workflows = pending_result.scalar() or 0
        
        completed_result = await session.execute(
            select(func.count(Workflow.id)).where(Workflow.status == WorkflowStatus.COMPLETED)
        )
        completed_workflows = completed_result.scalar() or 0
        
        failed_result = await session.execute(
            select(func.count(Workflow.id)).where(Workflow.status == WorkflowStatus.FAILED)
        )
        failed_workflows = failed_result.scalar() or 0
        
        # Count pending approvals from pending_drafts table (Sprint 70)
        pending_approvals = 0
        try:
            from src.db.workflow_db import get_workflow_db
            workflow_db = await get_workflow_db()
            if workflow_db and workflow_db.pool:
                async with workflow_db.get_connection() as conn:
                    if conn:
                        result = await conn.fetchval(
                            "SELECT COUNT(*) FROM pending_drafts WHERE status = 'PENDING_APPROVAL'"
                        )
                        pending_approvals = result or 0
        except Exception as e:
            # Log but don't fail the request
            import logging
            logging.getLogger(__name__).warning(f"Could not count pending approvals: {e}")
        
        # Calculate success rate
        if total_workflows > 0:
            success_rate = (completed_workflows / total_workflows) * 100
        else:
            success_rate = 0.0
        
        return DashboardStatsResponse(
            total_workflows=total_workflows,
            pending_workflows=pending_workflows,
            completed_workflows=completed_workflows,
            failed_workflows=failed_workflows,
            pending_approvals=pending_approvals,  # Sprint 70: Real count from DB
            success_rate=round(success_rate, 2)
        )


@router.get("/workflows", response_model=WorkflowListResponse)
async def list_workflows(
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page")
):
    """
    List workflows with pagination and filtering.
    
    Args:
        status: Optional status filter (triggered, processing, completed, failed)
        page: Page number (1-indexed)
        page_size: Number of items per page
        
    Returns:
        Paginated list of workflows
    """
    async with get_session() as session:
        # Build query
        query = (
            select(Workflow, FormSubmission)
            .join(FormSubmission, Workflow.form_submission_id == FormSubmission.id)
            .order_by(Workflow.created_at.desc())
        )
        
        if status:
            try:
                workflow_status = WorkflowStatus(status.lower())
                query = query.where(Workflow.status == workflow_status)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status: {status}. Must be one of: triggered, processing, completed, failed"
                )
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0
        
        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        
        # Execute query
        result = await session.execute(query)
        rows = result.all()
        
        # Convert to response items
        workflows = []
        for workflow, submission in rows:
            workflows.append(WorkflowListItem(
                id=str(workflow.id),
                status=workflow.status.value,
                prospect_email=submission.prospect_email,
                prospect_name=submission.prospect_full_name,
                prospect_company=submission.prospect_company,
                started_at=workflow.started_at,
                completed_at=workflow.completed_at,
                final_status=workflow.final_status
            ))
        
        return WorkflowListResponse(
            workflows=workflows,
            total=total,
            page=page,
            page_size=page_size
        )


@router.get("/workflows/{workflow_id}", response_model=WorkflowDetailResponse)
async def get_workflow_detail(workflow_id: str):
    """
    Get detailed workflow information.
    
    Args:
        workflow_id: Workflow UUID
        
    Returns:
        Detailed workflow data including form submission and errors
        
    Raises:
        404: If workflow not found
    """
    async with get_session() as session:
        query = (
            select(Workflow, FormSubmission)
            .join(FormSubmission, Workflow.form_submission_id == FormSubmission.id)
            .where(Workflow.id == UUID(workflow_id))
            .options(selectinload(Workflow.errors))
        )
        
        result = await session.execute(query)
        row = result.first()
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {workflow_id} not found"
            )
        
        workflow, submission = row
        
        return WorkflowDetailResponse(
            id=str(workflow.id),
            status=workflow.status.value,
            mode=workflow.mode.value,
            prospect_email=submission.prospect_email,
            prospect_name=submission.prospect_full_name,
            prospect_company=submission.prospect_company,
            started_at=workflow.started_at,
            completed_at=workflow.completed_at,
            final_status=workflow.final_status,
            form_id=submission.form_id,
            portal_id=submission.portal_id,
            raw_payload=submission.raw_payload or {},
            error_count=len(workflow.errors) if workflow.errors else 0
        )
