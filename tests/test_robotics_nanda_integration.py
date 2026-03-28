"""Tests for robotics and lab automation integration module."""

import pytest
import asyncio
from unittest.mock import Mock, patch
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from integrations.robotics_nanda_integration import (
    RoboticsAutomationManager,
    WearableDataStreamer,
)


class TestRoboticsAutomationManager:
    """Tests for RoboticsAutomationManager."""

    @pytest.fixture
    def manager(self):
        return RoboticsAutomationManager(config={"endpoint": "http://lab-robot.local"})

    def test_initialization_stores_config(self, manager):
        assert manager.config == {"endpoint": "http://lab-robot.local"}

    def test_initialization_empty_active_protocols(self, manager):
        assert manager.active_protocols == []

    @pytest.mark.asyncio
    async def test_execute_protocol_success(self, manager):
        result = await manager.execute_protocol(
            "DNA_EXTRACTION", {"sample_id": "SAM-001", "volume_ml": 5}
        )
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_execute_protocol_returns_protocol_name(self, manager):
        result = await manager.execute_protocol("CELL_CULTURE", {"temp_celsius": 37})
        assert result["protocol"] == "CELL_CULTURE"

    @pytest.mark.asyncio
    async def test_execute_protocol_returns_applied_parameters(self, manager):
        params = {"sample_id": "SAM-002", "rpm": 3000}
        result = await manager.execute_protocol("CENTRIFUGE", params)
        assert result["applied_parameters"] == params

    @pytest.mark.asyncio
    async def test_execute_protocol_includes_timestamp(self, manager):
        result = await manager.execute_protocol("WASH_STEP", {})
        assert "timestamp" in result
        # Verify it is a parseable ISO datetime string
        datetime.fromisoformat(result["timestamp"])

    @pytest.mark.asyncio
    async def test_execute_protocol_empty_name_raises_value_error(self, manager):
        with pytest.raises(ValueError, match="Protocol name must be specified"):
            await manager.execute_protocol("", {"sample": "S1"})

    @pytest.mark.asyncio
    async def test_execute_protocol_empty_parameters(self, manager):
        """Test that execute_protocol works with an empty parameters dict."""
        result = await manager.execute_protocol("RINSE", {})
        assert result["status"] == "success"
        assert result["applied_parameters"] == {}


class TestWearableDataStreamer:
    """Tests for WearableDataStreamer."""

    @pytest.fixture
    def streamer(self):
        return WearableDataStreamer(trial_id="TRIAL-2026-X")

    def test_initialization_stores_trial_id(self, streamer):
        assert streamer.trial_id == "TRIAL-2026-X"

    def test_initialization_empty_buffer(self, streamer):
        assert streamer.data_buffer == []

    def test_initialization_default_max_buffer_size(self, streamer):
        assert streamer.max_buffer_size == 1000

    def test_custom_max_buffer_size(self):
        s = WearableDataStreamer(trial_id="T-001", max_buffer_size=50)
        assert s.max_buffer_size == 50

    @pytest.mark.asyncio
    async def test_ingest_data_appends_to_buffer(self, streamer):
        await streamer.ingest_real_time_data("WATCH-001", {"heart_rate": 72})
        assert len(streamer.data_buffer) == 1

    @pytest.mark.asyncio
    async def test_ingest_data_returns_entry(self, streamer):
        data = {"heart_rate": 88, "spo2": 98}
        entry = await streamer.ingest_real_time_data("WATCH-002", data)
        assert entry["device_id"] == "WATCH-002"
        assert entry["data"] == data
        assert entry["trial_id"] == "TRIAL-2026-X"

    @pytest.mark.asyncio
    async def test_ingest_data_entry_has_timestamp(self, streamer):
        entry = await streamer.ingest_real_time_data("WATCH-003", {"step_count": 500})
        assert "timestamp" in entry
        datetime.fromisoformat(entry["timestamp"])

    @pytest.mark.asyncio
    async def test_ingest_data_preserves_trial_id(self, streamer):
        entry = await streamer.ingest_real_time_data("PATCH-01", {"glucose": 5.4})
        assert entry["trial_id"] == "TRIAL-2026-X"

    @pytest.mark.asyncio
    async def test_ingest_multiple_entries(self, streamer):
        for i in range(5):
            await streamer.ingest_real_time_data(f"DEVICE-{i}", {"value": i})
        assert len(streamer.data_buffer) == 5

    @pytest.mark.asyncio
    async def test_buffer_cap_removes_oldest_entry(self):
        """Test that when the buffer exceeds max_buffer_size, oldest entries are removed."""
        streamer = WearableDataStreamer(trial_id="T-CAP", max_buffer_size=3)
        for i in range(3):
            await streamer.ingest_real_time_data("D", {"seq": i})

        assert len(streamer.data_buffer) == 3

        # Adding a 4th entry should remove the first (seq=0)
        await streamer.ingest_real_time_data("D", {"seq": 3})

        assert len(streamer.data_buffer) == 3
        assert streamer.data_buffer[0]["data"]["seq"] == 1

    @pytest.mark.asyncio
    async def test_buffer_cap_keeps_most_recent_entries(self):
        """Test that the newest entries are always retained."""
        streamer = WearableDataStreamer(trial_id="T-RECENT", max_buffer_size=2)
        for i in range(5):
            await streamer.ingest_real_time_data("D", {"seq": i})

        # Buffer should contain only the last 2 entries (seq=3, seq=4)
        seqs = [entry["data"]["seq"] for entry in streamer.data_buffer]
        assert seqs == [3, 4]

    @pytest.mark.asyncio
    async def test_buffer_does_not_exceed_max_size(self):
        """Test that buffer never grows beyond max_buffer_size."""
        max_size = 5
        streamer = WearableDataStreamer(trial_id="T-MAX", max_buffer_size=max_size)
        for i in range(20):
            await streamer.ingest_real_time_data("D", {"seq": i})
        assert len(streamer.data_buffer) == max_size
