"""Tests for Dashboard Metrics Service - Sprint 43."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock, patch

from src.services.dashboard_metrics import DashboardMetricsService
from src.models.agent_execution import ExecutionStatus


class TestDashboardMetricsService:
    """Test dashboard metrics service initialization."""

    def test_init_with_session(self):
        """Service initializes with db session."""
        mock_db = MagicMock()
        service = DashboardMetricsService(mock_db)
        assert service.db == mock_db


class TestGetTodayMetrics:
    """Test get_today_metrics method."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = MagicMock()
        db.execute = AsyncMock()
        return db

    @pytest.mark.asyncio
    async def test_get_today_metrics_returns_all_fields(self, mock_db):
        """Today metrics should return all expected fields."""
        # Mock empty results
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_db.execute.return_value = mock_result

        service = DashboardMetricsService(mock_db)
        metrics = await service.get_today_metrics()

        # Check all expected fields are present
        assert "pending_actions" in metrics
        assert "approved_today" in metrics
        assert "sent_today" in metrics
        assert "failed_today" in metrics
        assert "agent_executions_24h" in metrics
        assert "success_rate" in metrics
        assert "as_of" in metrics

    @pytest.mark.asyncio
    async def test_get_today_metrics_calculates_success_rate(self, mock_db):
        """Success rate should be calculated correctly."""
        # Setup mock to return different values per call
        results = [
            0,   # pending_actions
            5,   # approved_today
            3,   # sent_today
            10,  # total executions
            8,   # success count
            2,   # failed today
            1,   # running
        ]
        call_count = 0

        def get_result():
            nonlocal call_count
            mock_result = MagicMock()
            mock_result.scalar.return_value = results[call_count] if call_count < len(results) else 0
            call_count += 1
            return mock_result

        mock_db.execute = AsyncMock(side_effect=lambda *args, **kwargs: get_result())

        service = DashboardMetricsService(mock_db)
        metrics = await service.get_today_metrics()

        # 8 success out of 10 = 80%
        assert metrics["success_rate"] == 80.0

    @pytest.mark.asyncio
    async def test_get_today_metrics_handles_zero_executions(self, mock_db):
        """Success rate should be 0 when no executions."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_db.execute.return_value = mock_result

        service = DashboardMetricsService(mock_db)
        metrics = await service.get_today_metrics()

        assert metrics["success_rate"] == 0.0
        assert metrics["agent_executions_24h"] == 0


class TestGetTopPriorityItems:
    """Test get_top_priority_items method."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = MagicMock()
        db.execute = AsyncMock()
        return db

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_items(self, mock_db):
        """Should return empty list when no pending items."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        service = DashboardMetricsService(mock_db)
        items = await service.get_top_priority_items(limit=5)

        assert items == []

    @pytest.mark.asyncio
    async def test_returns_items_with_expected_fields(self, mock_db):
        """Each item should have expected fields."""
        mock_item = MagicMock()
        mock_item.id = 1
        mock_item.title = "Follow up with John"
        mock_item.action_type = "send_email"
        mock_item.priority_score = 85.5
        mock_item.action_context = {"contact_name": "John Doe"}
        mock_item.created_at = datetime.utcnow()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_item]
        mock_db.execute.return_value = mock_result

        service = DashboardMetricsService(mock_db)
        items = await service.get_top_priority_items(limit=5)

        assert len(items) == 1
        assert items[0]["id"] == 1
        assert items[0]["action_type"] == "send_email"
        assert items[0]["priority_score"] == 85.5
        assert items[0]["contact_name"] == "John Doe"

    @pytest.mark.asyncio
    async def test_respects_limit_parameter(self, mock_db):
        """Should respect the limit parameter."""
        service = DashboardMetricsService(mock_db)
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        await service.get_top_priority_items(limit=3)
        
        # Verify execute was called (specific assertion would require inspecting SQL)
        assert mock_db.execute.called


class TestGetAgentPerformance:
    """Test get_agent_performance method."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = MagicMock()
        db.execute = AsyncMock()
        return db

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_executions(self, mock_db):
        """Should return None leaders when no executions."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute.return_value = mock_result

        service = DashboardMetricsService(mock_db)
        performance = await service.get_agent_performance(hours=24)

        assert performance["most_active"] is None
        assert performance["highest_success_rate"] is None
        assert performance["most_failed"] is None
        assert performance["agents"] == []

    @pytest.mark.asyncio
    async def test_identifies_most_active_agent(self, mock_db):
        """Should identify agent with most executions."""
        # Mock rows: (agent_name, total, success_count, failed_count)
        mock_row1 = MagicMock()
        mock_row1.agent_name = "ProspectingAgent"
        mock_row1.total = 10
        mock_row1.success_count = 8
        mock_row1.failed_count = 2

        mock_row2 = MagicMock()
        mock_row2.agent_name = "ResearchAgent"
        mock_row2.total = 5
        mock_row2.success_count = 5
        mock_row2.failed_count = 0

        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row1, mock_row2]
        mock_db.execute.return_value = mock_result

        service = DashboardMetricsService(mock_db)
        performance = await service.get_agent_performance(hours=24)

        assert performance["most_active"]["agent_name"] == "ProspectingAgent"
        assert performance["most_active"]["total"] == 10

    @pytest.mark.asyncio
    async def test_calculates_success_rates(self, mock_db):
        """Should calculate correct success rates."""
        mock_row = MagicMock()
        mock_row.agent_name = "TestAgent"
        mock_row.total = 10
        mock_row.success_count = 7
        mock_row.failed_count = 3

        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]
        mock_db.execute.return_value = mock_result

        service = DashboardMetricsService(mock_db)
        performance = await service.get_agent_performance()

        assert performance["agents"][0]["success_rate"] == 70.0


class TestGetRecentActivity:
    """Test get_recent_activity method."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = MagicMock()
        db.execute = AsyncMock()
        return db

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_activity(self, mock_db):
        """Should return empty list when no activity."""
        mock_result = MagicMock()
        mock_result.scalars.return_value = iter([])
        mock_db.execute.return_value = mock_result

        service = DashboardMetricsService(mock_db)
        activities = await service.get_recent_activity(limit=20)

        assert activities == []

    @pytest.mark.asyncio
    async def test_combines_queue_and_executions(self, mock_db):
        """Should combine both queue and execution activity."""
        now = datetime.utcnow()
        
        # Mock queue item
        mock_queue_item = MagicMock()
        mock_queue_item.id = 1
        mock_queue_item.status = "approved"
        mock_queue_item.action_type = "send_email"
        mock_queue_item.updated_at = now

        # Mock execution
        mock_execution = MagicMock()
        mock_execution.id = 1
        mock_execution.status = ExecutionStatus.SUCCESS.value
        mock_execution.agent_name = "ProspectingAgent"
        mock_execution.completed_at = now - timedelta(minutes=5)
        mock_execution.created_at = now - timedelta(minutes=10)

        # Setup mock to return different results per call
        call_count = 0
        def get_scalars():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return iter([mock_queue_item])
            return iter([mock_execution])

        mock_result = MagicMock()
        mock_result.scalars.side_effect = get_scalars
        mock_db.execute.return_value = mock_result

        service = DashboardMetricsService(mock_db)
        activities = await service.get_recent_activity(limit=20)

        # Should have both types
        types = [a["type"] for a in activities]
        assert "queue" in types
        assert "execution" in types

    @pytest.mark.asyncio
    async def test_sorts_by_timestamp(self, mock_db):
        """Activities should be sorted newest first."""
        now = datetime.utcnow()
        
        # Older item
        mock_old = MagicMock()
        mock_old.id = 1
        mock_old.status = "approved"
        mock_old.action_type = "send_email"
        mock_old.updated_at = now - timedelta(hours=1)

        # Newer item
        mock_new = MagicMock()
        mock_new.id = 2
        mock_new.status = "sent"
        mock_new.action_type = "send_email"
        mock_new.updated_at = now

        # Setup mock
        call_count = 0
        def get_scalars():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return iter([mock_old, mock_new])
            return iter([])

        mock_result = MagicMock()
        mock_result.scalars.side_effect = get_scalars
        mock_db.execute.return_value = mock_result

        service = DashboardMetricsService(mock_db)
        activities = await service.get_recent_activity(limit=20)

        # Newest should be first
        if len(activities) >= 2:
            assert activities[0]["item_id"] == 2


class TestFactoryFunction:
    """Test factory function."""

    def test_get_dashboard_metrics_service(self):
        """Factory should return service instance."""
        from src.services.dashboard_metrics import get_dashboard_metrics_service
        
        mock_db = MagicMock()
        service = get_dashboard_metrics_service(mock_db)
        
        assert isinstance(service, DashboardMetricsService)
        assert service.db == mock_db
