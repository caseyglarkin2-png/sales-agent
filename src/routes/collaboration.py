"""API routes for team collaboration."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from src.collaboration import (
    get_team_service,
    TeamRole,
    ActivityType,
)

router = APIRouter(prefix="/api/team", tags=["team"])


class AddMemberRequest(BaseModel):
    email: str
    name: str
    role: str = "member"


class UpdateMemberRequest(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class AssignRecordRequest(BaseModel):
    record_type: str
    record_id: str
    assignee_id: str
    assigned_by: str
    due_date: Optional[str] = None
    priority: str = "normal"
    notes: str = ""


class AddCommentRequest(BaseModel):
    record_type: str
    record_id: str
    author_id: str
    content: str
    parent_id: Optional[str] = None


class EditCommentRequest(BaseModel):
    new_content: str
    editor_id: str


class LogActivityRequest(BaseModel):
    activity_type: str
    actor_id: str
    record_type: Optional[str] = None
    record_id: Optional[str] = None
    description: str = ""
    metadata: dict = {}


# Team Members

@router.post("/members")
async def add_member(request: AddMemberRequest):
    """Add a team member."""
    service = get_team_service()
    
    try:
        role = TeamRole(request.role)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role. Valid: {[r.value for r in TeamRole]}"
        )
    
    member = service.add_member(
        email=request.email,
        name=request.name,
        role=role,
    )
    
    return {
        "message": "Member added",
        "member": member.to_dict(),
    }


@router.get("/members")
async def list_members(role: Optional[str] = None, active_only: bool = True):
    """List team members."""
    service = get_team_service()
    
    team_role = None
    if role:
        try:
            team_role = TeamRole(role)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid role")
    
    members = service.list_members(role=team_role, active_only=active_only)
    
    return {
        "members": [m.to_dict() for m in members],
        "total": len(members),
    }


@router.get("/members/{member_id}")
async def get_member(member_id: str):
    """Get a team member."""
    service = get_team_service()
    member = service.get_member(member_id)
    
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    return member.to_dict()


@router.put("/members/{member_id}")
async def update_member(member_id: str, request: UpdateMemberRequest):
    """Update a team member."""
    service = get_team_service()
    
    updates = {}
    if request.name:
        updates["name"] = request.name
    if request.role:
        updates["role"] = request.role
    if request.is_active is not None:
        updates["is_active"] = request.is_active
    
    member = service.update_member(member_id, updates)
    
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    return {
        "message": "Member updated",
        "member": member.to_dict(),
    }


@router.delete("/members/{member_id}")
async def deactivate_member(member_id: str):
    """Deactivate a team member."""
    service = get_team_service()
    
    if not service.deactivate_member(member_id):
        raise HTTPException(status_code=404, detail="Member not found")
    
    return {"message": "Member deactivated"}


# Assignments

@router.post("/assignments")
async def assign_record(request: AssignRecordRequest):
    """Assign a record to a team member."""
    service = get_team_service()
    
    due_date = None
    if request.due_date:
        due_date = datetime.fromisoformat(request.due_date)
    
    assignment = service.assign_record(
        record_type=request.record_type,
        record_id=request.record_id,
        assignee_id=request.assignee_id,
        assigned_by=request.assigned_by,
        due_date=due_date,
        priority=request.priority,
        notes=request.notes,
    )
    
    return {
        "message": "Record assigned",
        "assignment": assignment.to_dict(),
    }


@router.get("/assignments")
async def get_assignments(
    member_id: Optional[str] = None,
    record_type: Optional[str] = None,
    record_id: Optional[str] = None,
    status: str = "active",
):
    """Get assignments."""
    service = get_team_service()
    
    if member_id:
        assignments = service.get_assignments_for_member(member_id, status)
    elif record_type and record_id:
        assignment = service.get_assignment(record_type, record_id)
        assignments = [assignment] if assignment else []
    else:
        assignments = [
            a for a in service.assignments.values()
            if a.status == status
        ]
    
    return {
        "assignments": [a.to_dict() for a in assignments],
        "total": len(assignments),
    }


@router.post("/assignments/{assignment_id}/complete")
async def complete_assignment(assignment_id: str):
    """Complete an assignment."""
    service = get_team_service()
    
    assignment = service.complete_assignment(assignment_id)
    
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    return {
        "message": "Assignment completed",
        "assignment": assignment.to_dict(),
    }


# Comments

@router.post("/comments")
async def add_comment(request: AddCommentRequest):
    """Add a comment to a record."""
    service = get_team_service()
    
    comment = service.add_comment(
        record_type=request.record_type,
        record_id=request.record_id,
        author_id=request.author_id,
        content=request.content,
        parent_id=request.parent_id,
    )
    
    return {
        "message": "Comment added",
        "comment": comment.to_dict(),
    }


@router.get("/comments")
async def get_comments(record_type: str, record_id: str):
    """Get comments for a record."""
    service = get_team_service()
    
    comments = service.get_comments(record_type, record_id)
    
    return {
        "comments": [c.to_dict() for c in comments],
        "total": len(comments),
    }


@router.put("/comments/{comment_id}")
async def edit_comment(comment_id: str, request: EditCommentRequest):
    """Edit a comment."""
    service = get_team_service()
    
    comment = service.edit_comment(
        comment_id=comment_id,
        new_content=request.new_content,
        editor_id=request.editor_id,
    )
    
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found or not authorized")
    
    return {
        "message": "Comment edited",
        "comment": comment.to_dict(),
    }


@router.delete("/comments/{comment_id}")
async def delete_comment(comment_id: str, deleter_id: str):
    """Delete a comment."""
    service = get_team_service()
    
    if not service.delete_comment(comment_id, deleter_id):
        raise HTTPException(status_code=404, detail="Comment not found or not authorized")
    
    return {"message": "Comment deleted"}


@router.post("/comments/{comment_id}/react")
async def add_reaction(comment_id: str, user_id: str, emoji: str):
    """Add a reaction to a comment."""
    service = get_team_service()
    
    comment = service.add_reaction(comment_id, user_id, emoji)
    
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    return {
        "message": "Reaction added",
        "comment": comment.to_dict(),
    }


# Activity Feed

@router.post("/activities")
async def log_activity(request: LogActivityRequest):
    """Log an activity."""
    service = get_team_service()
    
    activity = service.log_activity(
        activity_type=request.activity_type,
        actor_id=request.actor_id,
        record_type=request.record_type,
        record_id=request.record_id,
        description=request.description,
        metadata=request.metadata,
    )
    
    return {
        "message": "Activity logged",
        "activity": activity.to_dict(),
    }


@router.get("/activities")
async def get_activity_feed(
    limit: int = 50,
    actor_id: Optional[str] = None,
    record_type: Optional[str] = None,
    record_id: Optional[str] = None,
):
    """Get activity feed."""
    service = get_team_service()
    
    activities = service.get_activity_feed(
        limit=limit,
        actor_id=actor_id,
        record_type=record_type,
        record_id=record_id,
    )
    
    return {
        "activities": [a.to_dict() for a in activities],
        "total": len(activities),
    }


@router.get("/mentions/{member_id}")
async def get_mentions(member_id: str):
    """Get mentions for a team member."""
    service = get_team_service()
    
    mentions = service.get_mentions_for_member(member_id)
    
    return {
        "mentions": [m.to_dict() for m in mentions],
        "total": len(mentions),
    }


# Stats

@router.get("/stats")
async def get_team_stats():
    """Get team statistics."""
    service = get_team_service()
    return service.get_team_stats()


@router.get("/roles")
async def list_roles():
    """List available team roles."""
    return {
        "roles": [
            {"role": r.value, "name": r.name.replace("_", " ").title()}
            for r in TeamRole
        ]
    }


@router.get("/activity-types")
async def list_activity_types():
    """List available activity types."""
    return {
        "activity_types": [
            {"type": t.value, "name": t.name.replace("_", " ").title()}
            for t in ActivityType
        ]
    }
