"""Command Queue models for CaseyOS."""
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from sqlalchemy import String, Float, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.db import Base


class ActionRecommendation(Base):
    """Recommendation with APS and explainability."""

    __tablename__ = "action_recommendations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    aps_score: Mapped[float] = mapped_column(Float, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)

    revenue_impact: Mapped[float] = mapped_column(Float, default=0.0)
    urgency_score: Mapped[float] = mapped_column(Float, default=0.0)
    effort_score: Mapped[float] = mapped_column(Float, default=0.0)
    strategic_score: Mapped[float] = mapped_column(Float, default=0.0)

    recommendation_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, default=dict)
    generated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class CommandQueueItem(Base):
    """Item in the daily command queue."""

    __tablename__ = "command_queue_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))

    priority_score: Mapped[float] = mapped_column(Float, index=True)
    action_type: Mapped[str] = mapped_column(String(64))
    action_context: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, default=dict)

    status: Mapped[str] = mapped_column(String(32), index=True, default="pending")
    owner: Mapped[str] = mapped_column(String(64), default="casey")

    due_by: Mapped[Optional[datetime]] = mapped_column(default=None)
    recommendation_id: Mapped[Optional[str]] = mapped_column(String(36), index=True)

    executed_at: Mapped[Optional[datetime]] = mapped_column(default=None)
    outcome: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, default=None)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
