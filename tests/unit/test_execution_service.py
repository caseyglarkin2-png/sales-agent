"""
Tests for ExecutionService.

Tests cover:
- Execution lifecycle (start, complete, fail, timeout, cancel)
- Query methods (get, filter, stats)
- Error handling and edge cases
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from src.models.agent_execution import AgentExecution, ExecutionStatus
from src.services.execution_service import ExecutionService, get_execution_service


class TestExecutionServiceLifecycle:
    """Test execution lifecycle methods."""

    @pytest.fixture
    def mock_db(self):
        """Create mock async database session."""
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def service(self, mock_db):
        """Create service with mock db."""
        return ExecutionService(mock_db)

    @pytest.mark.asyncio
    async def test_start_execution_creates_running_record(self, service, mock_db):
        """Start execution should create record and mark as running."""
        with patch("src.services.execution_service.log_event"):
            # Mock refresh to set ID
            async def mock_refresh(obj):
                obj.id = 1
            mock_db.refresh = mock_refresh

            execution = await service.start_execution(
                agent_name="ProspectingAgent",
                domain="prospecting",
                input_context={"contact_id": 123},
                trigger_source="api",
                triggered_by="user_1",
            )

            # Verify record was added
            mock_db.add.assert_called_once()
            added_execution = mock_db.add.call_args[0][0]
            assert added_execution.agent_name == "ProspectingAgent"
            assert added_execution.domain == "prospecting"
            assert added_execution.input_context == {"contact_id": 123}
            assert added_execution.trigger_source == "api"
            assert added_execution.triggered_by == "user_1"

    @pytest.mark.asyncio
    async def test_start_execution_with_celery_task_id(self, service, mock_db):
        """Start execution should store celery task ID when provided."""
        with patch("src.services.execution_service.log_event"):
            async def mock_refresh(obj):
                obj.id = 1
            mock_db.refresh = mock_refresh

            execution = await service.start_execution(
                agent_name="NurturingAgent",
                domain="nurturing",
                input_context={},
                celery_task_id="abc-123-def",
            )

            added_execution = mock_db.add.call_args[0][0]
            assert added_execution.celery_task_id == "abc-123-def"

    @pytest.mark.asyncio
    async def test_complete_execution_marks_success(self, service, mock_db):
        """Complete execution should mark as success with result."""
        # Create mock execution
        execution = AgentExecution(
            id=1,
            agent_name="TestAgent",
            domain="test",
            status=ExecutionStatus.RUNNING.value,
            started_at=datetime.utcnow(),
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = execution
        mock_db.execute.return_value = mock_result

        with patch("src.services.execution_service.log_event"):
            result = await service.complete_execution(
                execution_id=1,
                result={"drafted_emails": 5},
            )

            assert result.status == ExecutionStatus.SUCCESS.value
            assert result.output_result == {"drafted_emails": 5}
            assert result.completed_at is not None
            assert result.duration_ms is not None

    @pytest.mark.asyncio
    async def test_complete_execution_raises_for_terminal_state(self, service, mock_db):
        """Complete execution should raise error if already terminal."""
        execution = AgentExecution(
            id=1,
            agent_name="TestAgent",
            domain="test",
            status=ExecutionStatus.SUCCESS.value,
            completed_at=datetime.utcnow(),
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = execution
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="already in terminal state"):
            await service.complete_execution(1, {"data": "test"})

    @pytest.mark.asyncio
    async def test_fail_execution_marks_failure(self, service, mock_db):
        """Fail execution should mark as failed with error details."""
        execution = AgentExecution(
            id=1,
            agent_name="TestAgent",
            domain="test",
            status=ExecutionStatus.RUNNING.value,
            started_at=datetime.utcnow(),
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = execution
        mock_db.execute.return_value = mock_result

        with patch("src.services.execution_service.log_event"):
            result = await service.fail_execution(
                execution_id=1,
                error_message="Connection timeout",
                error_traceback="Traceback:\n...",
            )

            assert result.status == ExecutionStatus.FAILED.value
            assert result.error_message == "Connection timeout"
            assert result.error_traceback == "Traceback:\n..."
            assert result.completed_at is not None

    @pytest.mark.asyncio
    async def test_timeout_execution_marks_timed_out(self, service, mock_db):
        """Timeout execution should mark as timed out."""
        execution = AgentExecution(
            id=1,
            agent_name="TestAgent",
            domain="test",
            status=ExecutionStatus.RUNNING.value,
            started_at=datetime.utcnow(),
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = execution
        mock_db.execute.return_value = mock_result

        with patch("src.services.execution_service.log_event"):
            result = await service.timeout_execution(execution_id=1)

            assert result.status == ExecutionStatus.TIMED_OUT.value
            assert result.completed_at is not None

    @pytest.mark.asyncio
    async def test_cancel_execution_marks_cancelled(self, service, mock_db):
        """Cancel execution should mark as cancelled with reason."""
        execution = AgentExecution(
            id=1,
            agent_name="TestAgent",
            domain="test",
            status=ExecutionStatus.RUNNING.value,
            started_at=datetime.utcnow(),
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = execution
        mock_db.execute.return_value = mock_result

        with patch("src.services.execution_service.log_event"):
            result = await service.cancel_execution(
                execution_id=1,
                reason="User requested stop",
            )

            assert result.status == ExecutionStatus.CANCELLED.value
            assert result.error_message == "User requested stop"
            assert result.completed_at is not None


class TestExecutionServiceQueries:
    """Test execution query methods."""

    @pytest.fixture
    def mock_db(self):
        """Create mock async database session."""
        db = AsyncMock()
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def service(self, mock_db):
        """Create service with mock db."""
        return ExecutionService(mock_db)

    @pytest.mark.asyncio
    async def test_get_execution_returns_record(self, service, mock_db):
        """Get execution should return record by ID."""
        execution = AgentExecution(
            id=1,
            agent_name="TestAgent",
            domain="test",
            status=ExecutionStatus.SUCCESS.value,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = execution
        mock_db.execute.return_value = mock_result

        result = await service.get_execution(1)

        assert result.id == 1
        assert result.agent_name == "TestAgent"

    @pytest.mark.asyncio
    async def test_get_execution_returns_none_for_missing(self, service, mock_db):
        """Get execution should return None if not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.get_execution(999)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_recent_executions_returns_list(self, service, mock_db):
        """Get recent executions should return list."""
        executions = [
            AgentExecution(id=1, agent_name="Agent1", domain="test", status=ExecutionStatus.SUCCESS.value),
            AgentExecution(id=2, agent_name="Agent2", domain="test", status=ExecutionStatus.RUNNING.value),
        ]

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = executions
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await service.get_recent_executions(limit=10)

        assert len(result) == 2
        assert result[0].id == 1

    @pytest.mark.asyncio
    async def test_get_recent_executions_with_filters(self, service, mock_db):
        """Get recent executions should apply filters."""
        executions = [
            AgentExecution(id=1, agent_name="ProspectingAgent", domain="prospecting", status=ExecutionStatus.SUCCESS.value),
        ]

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = executions
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await service.get_recent_executions(
            agent_name="ProspectingAgent",
            domain="prospecting",
            status=ExecutionStatus.SUCCESS.value,
        )

        assert len(result) == 1
        assert result[0].agent_name == "ProspectingAgent"

    @pytest.mark.asyncio
    async def test_get_running_executions(self, service, mock_db):
        """Get running executions should return only running."""
        executions = [
            AgentExecution(id=1, agent_name="Agent1", domain="test", status=ExecutionStatus.RUNNING.value),
        ]

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = executions
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await service.get_running_executions()

        assert len(result) == 1
        assert result[0].status == ExecutionStatus.RUNNING.value

    @pytest.mark.asyncio
    async def test_get_stale_executions(self, service, mock_db):
        """Get stale executions should return long-running ones."""
        old_start = datetime.utcnow() - timedelta(minutes=60)
        executions = [
            AgentExecution(
                id=1,
                agent_name="StuckAgent",
                domain="test",
                status=ExecutionStatus.RUNNING.value,
                started_at=old_start,
            ),
        ]

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = executions
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await service.get_stale_executions(stale_after_minutes=30)

        assert len(result) == 1


class TestExecutionServiceStats:
    """Test execution statistics methods."""

    @pytest.fixture
    def mock_db(self):
        """Create mock async database session."""
        db = AsyncMock()
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def service(self, mock_db):
        """Create service with mock db."""
        return ExecutionService(mock_db)

    @pytest.mark.asyncio
    async def test_get_execution_stats_aggregates_by_status(self, service, mock_db):
        """Get stats should aggregate by status."""
        # Mock aggregate query results
        mock_result = MagicMock()
        mock_result.all.return_value = [
            (ExecutionStatus.SUCCESS.value, 10, 150.0),
            (ExecutionStatus.FAILED.value, 2, 50.0),
            (ExecutionStatus.RUNNING.value, 1, None),
        ]
        mock_db.execute.return_value = mock_result

        stats = await service.get_execution_stats(hours=24)

        assert stats["total"] == 13
        assert stats["period_hours"] == 24
        assert ExecutionStatus.SUCCESS.value in stats["by_status"]
        assert stats["by_status"][ExecutionStatus.SUCCESS.value]["count"] == 10
        assert stats["success_rate"] == round(10 / 13 * 100, 1)

    @pytest.mark.asyncio
    async def test_get_execution_stats_for_specific_agent(self, service, mock_db):
        """Get stats should filter by agent name."""
        mock_result = MagicMock()
        mock_result.all.return_value = [
            (ExecutionStatus.SUCCESS.value, 5, 200.0),
        ]
        mock_db.execute.return_value = mock_result

        stats = await service.get_execution_stats(
            agent_name="ProspectingAgent",
            hours=48,
        )

        assert stats["agent_name"] == "ProspectingAgent"
        assert stats["period_hours"] == 48

    @pytest.mark.asyncio
    async def test_get_execution_stats_empty_returns_zeros(self, service, mock_db):
        """Get stats with no data should return zeros."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute.return_value = mock_result

        stats = await service.get_execution_stats(hours=24)

        assert stats["total"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["avg_duration_ms"] is None


class TestExecutionServiceFactory:
    """Test factory function."""

    def test_get_execution_service_creates_instance(self):
        """Factory should create service with db session."""
        mock_db = AsyncMock()
        service = get_execution_service(mock_db)

        assert isinstance(service, ExecutionService)
        assert service.db is mock_db


class TestExecutionServiceErrorHandling:
    """Test error handling scenarios."""

    @pytest.fixture
    def mock_db(self):
        """Create mock async database session."""
        db = AsyncMock()
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def service(self, mock_db):
        """Create service with mock db."""
        return ExecutionService(mock_db)

    @pytest.mark.asyncio
    async def test_complete_nonexistent_execution_raises_error(self, service, mock_db):
        """Completing nonexistent execution should raise ValueError."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="not found"):
            await service.complete_execution(999, {"data": "test"})

    @pytest.mark.asyncio
    async def test_fail_nonexistent_execution_raises_error(self, service, mock_db):
        """Failing nonexistent execution should raise ValueError."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="not found"):
            await service.fail_execution(999, "Error")

    @pytest.mark.asyncio
    async def test_timeout_already_failed_raises_error(self, service, mock_db):
        """Timeout on failed execution should raise ValueError."""
        execution = AgentExecution(
            id=1,
            agent_name="TestAgent",
            domain="test",
            status=ExecutionStatus.FAILED.value,
            completed_at=datetime.utcnow(),
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = execution
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="already in terminal state"):
            await service.timeout_execution(1)
