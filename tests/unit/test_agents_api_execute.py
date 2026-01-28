"""
Tests for Agents API execution endpoints.

Sprint 42.3: Tests for manual trigger API.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from src.models.agent_execution import AgentExecution, ExecutionStatus
from src.security.csrf import csrf_protection


def get_csrf_headers():
    """Generate valid CSRF headers for testing."""
    token = csrf_protection.generate_token()
    return {"X-CSRF-Token": token}


class TestExecuteAgentEndpoint:
    """Test POST /api/agents/{agent_name}/execute."""

    @pytest.fixture
    def mock_registry(self):
        """Create mock agent registry."""
        mock = MagicMock()
        agent_meta = MagicMock()
        agent_meta.class_name = "ProspectingAgent"
        agent_meta.name = "Prospecting Agent"
        agent_meta.domain = "sales"
        agent_meta.to_dict.return_value = {
            "name": "Prospecting Agent",
            "description": "Test",
            "domain": "sales",
            "module_path": "src.agents.prospecting",
            "class_name": "ProspectingAgent",
            "capabilities": [],
            "icon": "🎯",
            "status": "active",
        }
        mock.get_by_name.return_value = agent_meta
        mock.get_by_class.return_value = agent_meta
        return mock

    @pytest.fixture
    def mock_execution(self):
        """Create mock execution record."""
        execution = MagicMock()
        execution.id = 1
        execution.agent_name = "ProspectingAgent"
        execution.domain = "sales"
        execution.status = ExecutionStatus.RUNNING.value
        execution.trigger_source = "api"
        execution.triggered_by = "test_user"
        execution.created_at = datetime.utcnow()
        return execution

    @pytest.mark.asyncio
    async def test_execute_agent_success(self, mock_registry, mock_execution):
        """Execute agent should create execution record."""
        from src.main import app

        mock_service = MagicMock()
        mock_service.start_execution = AsyncMock(return_value=mock_execution)

        with patch("src.routes.agents_api.get_agent_registry", return_value=mock_registry):
            with patch("src.routes.agents_api.get_execution_service", return_value=mock_service):
                with patch("src.routes.agents_api.queue_agent_execution", return_value="test-task-id"):
                    async with AsyncClient(
                        transport=ASGITransport(app=app),
                        base_url="http://test",
                    ) as client:
                        response = await client.post(
                            "/api/agents/ProspectingAgent/execute",
                            json={"context": {"test": "data"}, "triggered_by": "test_user"},
                            headers=get_csrf_headers(),
                        )

        assert response.status_code == 200
        data = response.json()
        assert data["execution_id"] == 1
        assert data["agent_name"] == "Prospecting Agent"
        assert data["status"] == ExecutionStatus.RUNNING.value

    @pytest.mark.asyncio
    async def test_execute_agent_not_found(self):
        """Execute non-existent agent should return 404."""
        from src.main import app

        mock_registry = MagicMock()
        mock_registry.get_by_name.return_value = None
        mock_registry.get_by_class.return_value = None

        with patch("src.routes.agents_api.get_agent_registry", return_value=mock_registry):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/api/agents/NonExistentAgent/execute",
                    json={"context": {}},
                    headers=get_csrf_headers(),
                )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_execute_agent_async_mode(self, mock_registry, mock_execution):
        """Execute with async_mode=True should queue for Celery."""
        from src.main import app

        mock_service = MagicMock()
        mock_service.start_execution = AsyncMock(return_value=mock_execution)

        with patch("src.routes.agents_api.get_agent_registry", return_value=mock_registry):
            with patch("src.routes.agents_api.get_execution_service", return_value=mock_service):
                with patch("src.routes.agents_api.queue_agent_execution", return_value="test-task-id"):
                    async with AsyncClient(
                        transport=ASGITransport(app=app),
                        base_url="http://test",
                    ) as client:
                        response = await client.post(
                            "/api/agents/ProspectingAgent/execute",
                            json={"context": {}, "async_mode": True},
                            headers=get_csrf_headers(),
                        )

        assert response.status_code == 200
        assert "queued" in response.json()["message"].lower()


class TestGetAgentExecutionsEndpoint:
    """Test GET /api/agents/{agent_name}/executions."""

    @pytest.fixture
    def mock_executions(self):
        """Create list of mock executions."""
        executions = []
        for i in range(3):
            exec = MagicMock()
            exec.id = i + 1
            exec.agent_name = "ProspectingAgent"
            exec.domain = "sales"
            exec.status = ExecutionStatus.SUCCESS.value
            exec.input_context = {"test": i}
            exec.output_result = {"result": i}
            exec.error_message = None
            exec.error_traceback = None
            exec.duration_ms = 100 + i * 10
            exec.trigger_source = "api"
            exec.triggered_by = "test_user"
            exec.celery_task_id = None
            exec.created_at = datetime.utcnow()
            exec.started_at = datetime.utcnow()
            exec.completed_at = datetime.utcnow()
            executions.append(exec)
        return executions

    @pytest.mark.asyncio
    async def test_get_agent_executions_success(self, mock_executions):
        """Get executions should return list."""
        from src.main import app

        mock_registry = MagicMock()
        agent_meta = MagicMock()
        agent_meta.class_name = "ProspectingAgent"
        mock_registry.get_by_name.return_value = agent_meta
        mock_registry.get_by_class.return_value = agent_meta

        mock_service = MagicMock()
        mock_service.get_recent_executions = AsyncMock(return_value=mock_executions)

        with patch("src.routes.agents_api.get_agent_registry", return_value=mock_registry):
            with patch("src.routes.agents_api.get_execution_service", return_value=mock_service):
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
                    response = await client.get("/api/agents/ProspectingAgent/executions")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["executions"]) == 3

    @pytest.mark.asyncio
    async def test_get_agent_executions_with_status_filter(self, mock_executions):
        """Get executions should respect status filter."""
        from src.main import app

        mock_registry = MagicMock()
        agent_meta = MagicMock()
        agent_meta.class_name = "ProspectingAgent"
        mock_registry.get_by_name.return_value = agent_meta

        mock_service = MagicMock()
        mock_service.get_recent_executions = AsyncMock(return_value=mock_executions[:1])

        with patch("src.routes.agents_api.get_agent_registry", return_value=mock_registry):
            with patch("src.routes.agents_api.get_execution_service", return_value=mock_service):
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
                    response = await client.get(
                        "/api/agents/ProspectingAgent/executions?status=success"
                    )

        assert response.status_code == 200
        # Verify the service was called with the status filter
        mock_service.get_recent_executions.assert_called_once()
        call_kwargs = mock_service.get_recent_executions.call_args[1]
        assert call_kwargs["status"] == "success"


class TestGetAgentExecutionStatsEndpoint:
    """Test GET /api/agents/{agent_name}/executions/stats."""

    @pytest.mark.asyncio
    async def test_get_agent_stats_success(self):
        """Get stats should return aggregated data."""
        from src.main import app

        mock_registry = MagicMock()
        agent_meta = MagicMock()
        agent_meta.class_name = "ProspectingAgent"
        mock_registry.get_by_name.return_value = agent_meta

        mock_stats = {
            "period_hours": 24,
            "agent_name": "ProspectingAgent",
            "total": 10,
            "success_rate": 80.0,
            "avg_duration_ms": 150,
            "by_status": {
                "success": {"count": 8, "avg_duration_ms": 140},
                "failed": {"count": 2, "avg_duration_ms": 200},
            },
        }

        mock_service = MagicMock()
        mock_service.get_execution_stats = AsyncMock(return_value=mock_stats)

        with patch("src.routes.agents_api.get_agent_registry", return_value=mock_registry):
            with patch("src.routes.agents_api.get_execution_service", return_value=mock_service):
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
                    response = await client.get(
                        "/api/agents/ProspectingAgent/executions/stats?hours=24"
                    )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 10
        assert data["success_rate"] == 80.0
        assert data["period_hours"] == 24


class TestGetAllExecutionsEndpoint:
    """Test GET /api/agents/executions/all."""

    @pytest.mark.asyncio
    async def test_get_all_executions_success(self):
        """Get all executions should return list."""
        from src.main import app

        mock_executions = []
        for i in range(2):
            exec = MagicMock()
            exec.id = i + 1
            exec.agent_name = f"Agent{i}"
            exec.domain = "sales"
            exec.status = ExecutionStatus.SUCCESS.value
            exec.input_context = {}
            exec.output_result = {}
            exec.error_message = None
            exec.error_traceback = None
            exec.duration_ms = 100
            exec.trigger_source = "api"
            exec.triggered_by = None
            exec.celery_task_id = None
            exec.created_at = datetime.utcnow()
            exec.started_at = datetime.utcnow()
            exec.completed_at = datetime.utcnow()
            mock_executions.append(exec)

        mock_service = MagicMock()
        mock_service.get_recent_executions = AsyncMock(return_value=mock_executions)

        with patch("src.routes.agents_api.get_execution_service", return_value=mock_service):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get("/api/agents/executions/all")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2


class TestCancelExecutionEndpoint:
    """Test DELETE /api/agents/executions/{execution_id}."""

    @pytest.mark.asyncio
    async def test_cancel_execution_success(self):
        """Cancel execution should return cancelled status."""
        from src.main import app

        mock_execution = MagicMock()
        mock_execution.id = 1
        mock_execution.status = ExecutionStatus.CANCELLED.value

        mock_service = MagicMock()
        mock_service.cancel_execution = AsyncMock(return_value=mock_execution)

        with patch("src.routes.agents_api.get_execution_service", return_value=mock_service):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.delete(
                    "/api/agents/executions/1?reason=Test%20cancellation",
                    headers=get_csrf_headers(),
                )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == ExecutionStatus.CANCELLED.value
        assert "cancelled" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_cancel_execution_not_found(self):
        """Cancel non-existent execution should return 404."""
        from src.main import app

        mock_service = MagicMock()
        mock_service.cancel_execution = AsyncMock(
            side_effect=ValueError("Execution 999 not found")
        )

        with patch("src.routes.agents_api.get_execution_service", return_value=mock_service):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.delete(
                    "/api/agents/executions/999",
                    headers=get_csrf_headers(),
                )

        assert response.status_code == 404


class TestRetryExecutionEndpoint:
    """Test POST /api/agents/executions/{execution_id}/retry - Sprint 42.7."""

    @pytest.mark.asyncio
    async def test_retry_failed_execution_success(self):
        """Retry should create new execution from failed one."""
        from src.main import app
        from src.models.agent_execution import AgentExecution

        # Mock original failed execution
        original_execution = MagicMock(spec=AgentExecution)
        original_execution.id = 42
        original_execution.agent_name = "ProspectingAgent"
        original_execution.domain = "sales"
        original_execution.status = ExecutionStatus.FAILED.value
        original_execution.input_context = {"lead_id": 123}
        original_execution.triggered_by = "user123"

        # Mock new execution
        new_execution = MagicMock(spec=AgentExecution)
        new_execution.id = 43
        new_execution.agent_name = "ProspectingAgent"
        new_execution.domain = "sales"
        new_execution.status = ExecutionStatus.PENDING.value
        new_execution.trigger_source = "retry:42"
        new_execution.triggered_by = "user123"
        new_execution.created_at = datetime.utcnow()

        # Mock agent meta
        mock_registry = MagicMock()
        agent_meta = MagicMock()
        agent_meta.name = "ProspectingAgent"
        agent_meta.class_name = "ProspectingAgent"
        agent_meta.domain = "sales"
        agent_meta.module_path = "src.agents.prospecting"
        mock_registry.agents = {"ProspectingAgent": agent_meta}

        mock_service = MagicMock()
        mock_service.get_execution = AsyncMock(return_value=original_execution)
        mock_service.start_execution = AsyncMock(return_value=new_execution)

        with patch("src.routes.agents_api.get_agent_registry", return_value=mock_registry):
            with patch("src.routes.agents_api.get_execution_service", return_value=mock_service):
                with patch("src.routes.agents_api.queue_agent_execution", return_value="celery-task-id-123"):
                    async with AsyncClient(
                        transport=ASGITransport(app=app),
                        base_url="http://test",
                    ) as client:
                        response = await client.post(
                            "/api/agents/executions/42/retry",
                            headers=get_csrf_headers(),
                        )

        assert response.status_code == 200
        data = response.json()
        assert data["execution_id"] == 43
        assert "Retry" in data["message"]

    @pytest.mark.asyncio
    async def test_retry_execution_not_found(self):
        """Retry non-existent execution should return 404."""
        from src.main import app

        mock_service = MagicMock()
        mock_service.get_execution = AsyncMock(return_value=None)

        with patch("src.routes.agents_api.get_execution_service", return_value=mock_service):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/api/agents/executions/999/retry",
                    headers=get_csrf_headers(),
                )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_retry_success_execution_fails(self):
        """Retry should fail for execution that succeeded."""
        from src.main import app
        from src.models.agent_execution import AgentExecution

        # Mock successful execution (not retryable)
        success_execution = MagicMock(spec=AgentExecution)
        success_execution.id = 42
        success_execution.status = ExecutionStatus.SUCCESS.value

        mock_service = MagicMock()
        mock_service.get_execution = AsyncMock(return_value=success_execution)

        with patch("src.routes.agents_api.get_execution_service", return_value=mock_service):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/api/agents/executions/42/retry",
                    headers=get_csrf_headers(),
                )

        assert response.status_code == 400
        assert "Cannot retry" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_retry_timed_out_execution_success(self):
        """Retry should work for timed out executions."""
        from src.main import app
        from src.models.agent_execution import AgentExecution

        # Mock timed out execution
        timed_out_execution = MagicMock(spec=AgentExecution)
        timed_out_execution.id = 42
        timed_out_execution.agent_name = "ProspectingAgent"
        timed_out_execution.domain = "sales"
        timed_out_execution.status = ExecutionStatus.TIMED_OUT.value
        timed_out_execution.input_context = {}
        timed_out_execution.triggered_by = None

        new_execution = MagicMock(spec=AgentExecution)
        new_execution.id = 43
        new_execution.agent_name = "ProspectingAgent"
        new_execution.domain = "sales"
        new_execution.status = ExecutionStatus.PENDING.value
        new_execution.trigger_source = "retry:42"
        new_execution.triggered_by = None
        new_execution.created_at = datetime.utcnow()

        mock_registry = MagicMock()
        agent_meta = MagicMock()
        agent_meta.name = "ProspectingAgent"
        agent_meta.class_name = "ProspectingAgent"
        agent_meta.domain = "sales"
        agent_meta.module_path = "src.agents.prospecting"
        mock_registry.agents = {"ProspectingAgent": agent_meta}

        mock_service = MagicMock()
        mock_service.get_execution = AsyncMock(return_value=timed_out_execution)
        mock_service.start_execution = AsyncMock(return_value=new_execution)

        with patch("src.routes.agents_api.get_agent_registry", return_value=mock_registry):
            with patch("src.routes.agents_api.get_execution_service", return_value=mock_service):
                with patch("src.routes.agents_api.queue_agent_execution", return_value="celery-task-id"):
                    async with AsyncClient(
                        transport=ASGITransport(app=app),
                        base_url="http://test",
                    ) as client:
                        response = await client.post(
                            "/api/agents/executions/42/retry",
                            headers=get_csrf_headers(),
                        )

        assert response.status_code == 200
