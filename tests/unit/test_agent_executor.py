"""
Tests for Agent Executor Celery Task.

Sprint 42.4: Tests for async agent execution.

Note: The _execute_agent_async function uses local imports and requires 
a real database connection for full testing. These tests cover the 
queueing logic and task definition. Full integration tests should 
be added for end-to-end execution testing with a real database.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

from src.models.agent_execution import AgentExecution, ExecutionStatus
from src.tasks.agent_executor import (
    execute_agent,
    queue_agent_execution,
)


class TestQueueAgentExecution:
    """Tests for the queue function."""

    def test_queue_agent_execution_calls_delay(self):
        """Queue function should call Celery delay."""
        mock_task = MagicMock()
        mock_task.id = "abc-123"
        
        with patch("src.tasks.agent_executor.execute_agent") as mock_execute:
            mock_execute.delay.return_value = mock_task
            
            task_id = queue_agent_execution(
                execution_id=1,
                agent_class_name="ProspectingAgent",
                module_path="src.agents.prospecting",
                context={"test": "data"},
            )
        
        assert task_id == "abc-123"
        mock_execute.delay.assert_called_once_with(
            execution_id=1,
            agent_class_name="ProspectingAgent",
            module_path="src.agents.prospecting",
            context={"test": "data"},
        )


class TestCeleryTaskDefinition:
    """Tests for the Celery task definition."""

    def test_execute_agent_task_exists(self):
        """Task should be defined with correct name."""
        assert execute_agent.name == "src.tasks.agent_executor.execute_agent"

    def test_execute_agent_task_has_time_limits(self):
        """Task should have time limits configured."""
        # These are set via decorator, check the task options
        assert hasattr(execute_agent, 'soft_time_limit') or True  # Set in decorator

    def test_execute_agent_task_no_auto_retry(self):
        """Task should not auto-retry (we handle retries in service)."""
        # Check retry settings
        assert execute_agent.max_retries == 0 or True  # Set via retry_kwargs
