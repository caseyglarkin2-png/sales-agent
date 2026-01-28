"""Tests for HubSpot Pipeline methods - Sprint 43.4."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from src.connectors.hubspot import HubSpotConnector


class TestGetPipelineStages:
    """Test get_pipeline_stages method."""

    @pytest.fixture
    def connector(self):
        """Create a HubSpot connector."""
        return HubSpotConnector("test_api_key")

    @pytest.mark.asyncio
    async def test_returns_stages_on_success(self, connector):
        """Should return list of stages on successful API call."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {"id": "stage1", "label": "Qualified", "displayOrder": 1},
                {"id": "stage2", "label": "Proposal", "displayOrder": 2},
            ]
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            stages = await connector.get_pipeline_stages()

        assert len(stages) == 2
        assert stages[0]["label"] == "Qualified"
        assert stages[1]["label"] == "Proposal"

    @pytest.mark.asyncio
    async def test_returns_empty_on_error(self, connector):
        """Should return empty list on API error."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.HTTPError("API Error")
            )
            stages = await connector.get_pipeline_stages()

        assert stages == []


class TestGetDealsByStage:
    """Test get_deals_by_stage method."""

    @pytest.fixture
    def connector(self):
        """Create a HubSpot connector."""
        return HubSpotConnector("test_api_key")

    @pytest.mark.asyncio
    async def test_groups_deals_by_stage(self, connector):
        """Should group deals by their stage."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "id": "deal1",
                    "properties": {
                        "dealname": "Deal 1",
                        "dealstage": "qualified",
                        "amount": "10000",
                    }
                },
                {
                    "id": "deal2",
                    "properties": {
                        "dealname": "Deal 2",
                        "dealstage": "qualified",
                        "amount": "20000",
                    }
                },
                {
                    "id": "deal3",
                    "properties": {
                        "dealname": "Deal 3",
                        "dealstage": "proposal",
                        "amount": "15000",
                    }
                },
            ]
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            by_stage = await connector.get_deals_by_stage()

        assert "qualified" in by_stage
        assert "proposal" in by_stage
        assert len(by_stage["qualified"]) == 2
        assert len(by_stage["proposal"]) == 1
        assert by_stage["qualified"][0]["amount"] == 10000.0

    @pytest.mark.asyncio
    async def test_returns_empty_on_error(self, connector):
        """Should return empty dict on API error."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.HTTPError("API Error")
            )
            by_stage = await connector.get_deals_by_stage()

        assert by_stage == {}


class TestGetPipelineSummary:
    """Test get_pipeline_summary method."""

    @pytest.fixture
    def connector(self):
        """Create a HubSpot connector."""
        return HubSpotConnector("test_api_key")

    @pytest.mark.asyncio
    async def test_returns_complete_summary(self, connector):
        """Should return complete pipeline summary."""
        # Mock the dependent methods
        connector.get_pipeline_stages = AsyncMock(return_value=[
            {"id": "qualified", "label": "Qualified", "displayOrder": 1},
            {"id": "proposal", "label": "Proposal", "displayOrder": 2},
        ])
        connector.get_deals_by_stage = AsyncMock(return_value={
            "qualified": [
                {"id": "1", "name": "Deal 1", "amount": 10000, "last_modified": None},
                {"id": "2", "name": "Deal 2", "amount": 20000, "last_modified": None},
            ],
            "proposal": [
                {"id": "3", "name": "Deal 3", "amount": 15000, "last_modified": None},
            ],
        })

        summary = await connector.get_pipeline_summary()

        assert summary["total_deals"] == 3
        assert summary["total_value"] == 45000.0
        assert len(summary["stages"]) == 2
        assert summary["stages"][0]["label"] == "Qualified"
        assert summary["stages"][0]["count"] == 2
        assert summary["stages"][0]["value"] == 30000.0

    @pytest.mark.asyncio
    async def test_identifies_at_risk_deals(self, connector):
        """Should identify deals with no recent activity."""
        old_date = (datetime.utcnow() - timedelta(days=45)).isoformat() + "Z"
        
        connector.get_pipeline_stages = AsyncMock(return_value=[
            {"id": "qualified", "label": "Qualified", "displayOrder": 1},
        ])
        connector.get_deals_by_stage = AsyncMock(return_value={
            "qualified": [
                {"id": "1", "name": "Stale Deal", "amount": 10000, "last_modified": old_date},
            ],
        })

        summary = await connector.get_pipeline_summary()

        assert summary["at_risk_count"] == 1
        assert len(summary["at_risk_deals"]) == 1
        assert summary["at_risk_deals"][0]["name"] == "Stale Deal"

    @pytest.mark.asyncio
    async def test_handles_empty_pipeline(self, connector):
        """Should handle empty pipeline gracefully."""
        connector.get_pipeline_stages = AsyncMock(return_value=[])
        connector.get_deals_by_stage = AsyncMock(return_value={})

        summary = await connector.get_pipeline_summary()

        assert summary["total_deals"] == 0
        assert summary["total_value"] == 0.0
        assert summary["stages"] == []
