"""Unit tests for AgentExecution model.

Sprint 42.1: Agent Execution Infrastructure
Tests CRUD operations and state transitions for AgentExecution.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from src.models.agent_execution import AgentExecution, ExecutionStatus


class TestAgentExecutionModel:
    """Test AgentExecution model creation and fields."""
    
    def test_create_execution_basic(self):
        """Test creating an execution with basic values."""
        execution = AgentExecution(
            agent_name="ProspectingAgent",
            domain="sales",
            status=ExecutionStatus.PENDING.value  # Explicitly set status
        )
        
        assert execution.agent_name == "ProspectingAgent"
        assert execution.domain == "sales"
        assert execution.status == ExecutionStatus.PENDING.value
        assert execution.error_message is None
        assert execution.duration_ms is None
    
    def test_create_execution_with_input_context(self):
        """Test creating an execution with input context."""
        context = {"contact_id": "123", "action": "draft_email"}
        execution = AgentExecution(
            agent_name="NurturingAgent",
            domain="sales",
            input_context=context,
            trigger_source="scheduled",
            triggered_by="celery-beat"
        )
        
        assert execution.input_context == context
        assert execution.trigger_source == "scheduled"
        assert execution.triggered_by == "celery-beat"
    
    def test_execution_status_enum_values(self):
        """Test all status enum values are strings."""
        assert ExecutionStatus.PENDING.value == "pending"
        assert ExecutionStatus.RUNNING.value == "running"
        assert ExecutionStatus.SUCCESS.value == "success"
        assert ExecutionStatus.FAILED.value == "failed"
        assert ExecutionStatus.TIMED_OUT.value == "timed_out"
        assert ExecutionStatus.CANCELLED.value == "cancelled"


class TestAgentExecutionStateTransitions:
    """Test state transition methods."""
    
    def test_mark_running(self):
        """Test marking execution as running."""
        execution = AgentExecution(
            agent_name="TestAgent",
            domain="test"
        )
        
        execution.mark_running()
        
        assert execution.status == ExecutionStatus.RUNNING.value
        assert execution.started_at is not None
        assert isinstance(execution.started_at, datetime)
    
    def test_mark_success(self):
        """Test marking execution as successful."""
        execution = AgentExecution(
            agent_name="TestAgent",
            domain="test"
        )
        execution.mark_running()
        
        result = {"drafted": True, "draft_id": "abc123"}
        execution.mark_success(result)
        
        assert execution.status == ExecutionStatus.SUCCESS.value
        assert execution.output_result == result
        assert execution.completed_at is not None
        assert execution.duration_ms is not None
        assert execution.duration_ms >= 0
    
    def test_mark_failed(self):
        """Test marking execution as failed."""
        execution = AgentExecution(
            agent_name="TestAgent",
            domain="test"
        )
        execution.mark_running()
        
        execution.mark_failed(
            error="Connection timeout",
            traceback="Traceback (most recent call last)..."
        )
        
        assert execution.status == ExecutionStatus.FAILED.value
        assert execution.error_message == "Connection timeout"
        assert execution.error_traceback == "Traceback (most recent call last)..."
        assert execution.completed_at is not None
    
    def test_mark_timed_out(self):
        """Test marking execution as timed out."""
        execution = AgentExecution(
            agent_name="TestAgent",
            domain="test"
        )
        execution.mark_running()
        
        execution.mark_timed_out()
        
        assert execution.status == ExecutionStatus.TIMED_OUT.value
        assert "300s" in execution.error_message
        assert execution.completed_at is not None


class TestAgentExecutionProperties:
    """Test computed properties."""
    
    def test_is_terminal_pending(self):
        """Pending is not terminal."""
        execution = AgentExecution(
            agent_name="TestAgent",
            domain="test"
        )
        assert execution.is_terminal is False
    
    def test_is_terminal_running(self):
        """Running is not terminal."""
        execution = AgentExecution(
            agent_name="TestAgent",
            domain="test"
        )
        execution.mark_running()
        assert execution.is_terminal is False
    
    def test_is_terminal_success(self):
        """Success is terminal."""
        execution = AgentExecution(
            agent_name="TestAgent",
            domain="test"
        )
        execution.mark_running()
        execution.mark_success({})
        assert execution.is_terminal is True
    
    def test_is_terminal_failed(self):
        """Failed is terminal."""
        execution = AgentExecution(
            agent_name="TestAgent",
            domain="test"
        )
        execution.mark_running()
        execution.mark_failed("Error")
        assert execution.is_terminal is True
    
    def test_is_terminal_timed_out(self):
        """Timed out is terminal."""
        execution = AgentExecution(
            agent_name="TestAgent",
            domain="test"
        )
        execution.mark_running()
        execution.mark_timed_out()
        assert execution.is_terminal is True
    
    def test_repr(self):
        """Test string representation."""
        execution = AgentExecution(
            agent_name="ProspectingAgent",
            domain="sales",
            status=ExecutionStatus.PENDING.value
        )
        repr_str = repr(execution)
        assert "ProspectingAgent" in repr_str
        assert "pending" in repr_str


class TestAgentExecutionDurationCalculation:
    """Test duration calculation accuracy."""
    
    def test_duration_calculated_on_success(self):
        """Duration should be calculated when marking success."""
        execution = AgentExecution(
            agent_name="TestAgent",
            domain="test"
        )
        # Simulate a start time 100ms ago
        execution.started_at = datetime.utcnow() - timedelta(milliseconds=100)
        execution.status = ExecutionStatus.RUNNING.value
        
        execution.mark_success({"result": "ok"})
        
        # Duration should be approximately 100ms (with some tolerance)
        assert execution.duration_ms is not None
        assert execution.duration_ms >= 50  # Allow for timing variations
    
    def test_duration_calculated_on_failure(self):
        """Duration should be calculated when marking failure."""
        execution = AgentExecution(
            agent_name="TestAgent",
            domain="test"
        )
        execution.started_at = datetime.utcnow() - timedelta(milliseconds=50)
        execution.status = ExecutionStatus.RUNNING.value
        
        execution.mark_failed("Test error")
        
        assert execution.duration_ms is not None
        assert execution.duration_ms >= 0
    
    def test_duration_none_if_never_started(self):
        """Duration should remain None if execution never started."""
        execution = AgentExecution(
            agent_name="TestAgent",
            domain="test"
        )
        # Mark success without ever calling mark_running
        execution.mark_success({})
        
        # started_at is None, so duration should also be None
        assert execution.started_at is None
        assert execution.duration_ms is None
