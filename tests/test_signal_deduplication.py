"""
Tests for signal deduplication logic.
"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import json
import hashlib

from src.models.signal import Signal, SignalSource, compute_payload_hash
from src.services.signal_service import SignalService, DEDUP_WINDOW_MINUTES


class TestComputePayloadHash:
    """Tests for payload hash computation."""

    def test_computes_sha256_hash(self):
        """Hash is a valid SHA256 hex digest."""
        payload = {"email": "test@example.com", "name": "Test User"}
        hash_value = compute_payload_hash(payload)
        assert len(hash_value) == 64
        assert all(c in "0123456789abcdef" for c in hash_value)

    def test_same_payload_same_hash(self):
        """Same payload produces same hash."""
        payload = {"email": "test@example.com", "name": "Test User"}
        hash1 = compute_payload_hash(payload)
        hash2 = compute_payload_hash(payload)
        assert hash1 == hash2

    def test_different_payload_different_hash(self):
        """Different payloads produce different hashes."""
        payload1 = {"email": "test1@example.com"}
        payload2 = {"email": "test2@example.com"}
        hash1 = compute_payload_hash(payload1)
        hash2 = compute_payload_hash(payload2)
        assert hash1 != hash2

    def test_order_independent(self):
        """Key order doesn't affect hash (json.dumps with sort_keys)."""
        payload1 = {"name": "Test", "email": "test@example.com"}
        payload2 = {"email": "test@example.com", "name": "Test"}
        hash1 = compute_payload_hash(payload1)
        hash2 = compute_payload_hash(payload2)
        assert hash1 == hash2

    def test_handles_nested_payload(self):
        """Nested payloads are properly hashed."""
        payload = {
            "contact": {"email": "test@example.com", "name": "Test"},
            "metadata": {"source": "form", "utm": {"campaign": "test"}}
        }
        hash_value = compute_payload_hash(payload)
        assert len(hash_value) == 64


class TestCheckDuplicate:
    """Tests for duplicate signal detection."""

    @pytest.fixture
    def signal_service(self):
        """Create a SignalService with mocked db session."""
        mock_db = MagicMock()
        return SignalService(mock_db)

    @pytest.mark.asyncio
    async def test_returns_none_when_no_duplicate(self, signal_service):
        """Returns None when no duplicate exists."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        signal_service.db.execute = AsyncMock(return_value=mock_result)

        result = await signal_service.check_duplicate(
            source=SignalSource.FORM,
            payload={"email": "test@example.com"},
            window_minutes=5
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_signal_when_duplicate_exists(self, signal_service):
        """Returns existing signal when duplicate found."""
        existing_signal = Signal(
            source=SignalSource.FORM,
            event_type="form_submission",
            payload={"email": "test@example.com"},
            payload_hash="abc123"
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_signal
        signal_service.db.execute = AsyncMock(return_value=mock_result)

        result = await signal_service.check_duplicate(
            source=SignalSource.FORM,
            payload={"email": "test@example.com"},
            window_minutes=5
        )
        assert result == existing_signal


class TestCreateSignalDeduplication:
    """Tests for deduplication in create_signal."""

    @pytest.fixture
    def signal_service(self):
        """Create a SignalService with mocked db session."""
        mock_db = MagicMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()
        return SignalService(mock_db)

    @pytest.mark.asyncio
    async def test_skips_dedup_when_flag_set(self, signal_service):
        """Dedup check is skipped when skip_dedup=True."""
        signal_service.check_duplicate = AsyncMock()
        
        with patch.object(signal_service.db, 'add'):
            with patch.object(signal_service.db, 'flush', new_callable=AsyncMock):
                await signal_service.create_signal(
                    source=SignalSource.FORM,
                    event_type="form_submission",
                    payload={"email": "test@example.com"},
                    skip_dedup=True
                )
        
        signal_service.check_duplicate.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_none_for_duplicate(self, signal_service):
        """Returns None when duplicate detected."""
        existing_signal = Signal(
            id=1,
            source=SignalSource.FORM,
            event_type="form_submission",
            payload={"email": "test@example.com"},
            payload_hash="abc123"
        )
        signal_service.check_duplicate = AsyncMock(return_value=existing_signal)

        result = await signal_service.create_signal(
            source=SignalSource.FORM,
            event_type="form_submission",
            payload={"email": "test@example.com"}
        )
        
        assert result is None

    @pytest.mark.asyncio
    async def test_creates_signal_when_no_duplicate(self, signal_service):
        """Creates new signal when no duplicate exists."""
        signal_service.check_duplicate = AsyncMock(return_value=None)
        
        result = await signal_service.create_signal(
            source=SignalSource.FORM,
            event_type="form_submission",
            payload={"email": "test@example.com"}
        )
        
        assert result is not None
        assert result.source == SignalSource.FORM
        assert result.event_type == "form_submission"
        assert result.payload_hash is not None


class TestCreateAndProcessDeduplication:
    """Tests for deduplication in create_and_process."""

    @pytest.fixture
    def signal_service(self):
        """Create a SignalService with mocked db session."""
        mock_db = MagicMock()
        return SignalService(mock_db)

    @pytest.mark.asyncio
    async def test_returns_none_tuple_for_duplicate(self, signal_service):
        """Returns (None, None) when signal is duplicate."""
        signal_service.create_signal = AsyncMock(return_value=None)

        signal, item = await signal_service.create_and_process(
            source=SignalSource.FORM,
            event_type="form_submission",
            payload={"email": "test@example.com"}
        )
        
        assert signal is None
        assert item is None

    @pytest.mark.asyncio
    async def test_processes_signal_when_not_duplicate(self, signal_service):
        """Processes signal when not a duplicate."""
        mock_signal = Signal(
            id=1,
            source=SignalSource.FORM,
            event_type="form_submission",
            payload={"email": "test@example.com"}
        )
        mock_item = MagicMock()
        signal_service.create_signal = AsyncMock(return_value=mock_signal)
        signal_service.process_signal = AsyncMock(return_value=mock_item)

        signal, item = await signal_service.create_and_process(
            source=SignalSource.FORM,
            event_type="form_submission",
            payload={"email": "test@example.com"}
        )
        
        assert signal == mock_signal
        assert item == mock_item
        signal_service.process_signal.assert_called_once_with(mock_signal)


class TestDedupWindowMinutes:
    """Tests for the deduplication window constant."""

    def test_dedup_window_is_5_minutes(self):
        """Default dedup window is 5 minutes."""
        assert DEDUP_WINDOW_MINUTES == 5
