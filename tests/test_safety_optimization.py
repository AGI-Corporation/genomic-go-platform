"""Tests for safety monitoring optimization."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from clinical_trials.realtime_optimizer import SafetyMonitoringSystem

class TestSafetyOptimization:
    @pytest.fixture
    def monitor(self):
        return SafetyMonitoringSystem(trial_id="TEST-OPT", safety_threshold=0.15)

    @pytest.mark.asyncio
    async def test_sliding_window_pruning(self, monitor):
        """Test that events older than 7 days are pruned."""
        now = datetime.now(timezone.utc)

        # 1. Add an old event (8 days ago)
        old_event = {
            "trial_id": "TEST-OPT",
            "severity": 4,
            "timestamp": (now - timedelta(days=8)).isoformat()
        }
        await monitor.process_adverse_event(old_event)

        # Should be pruned immediately because process_adverse_event checks against now
        assert len(monitor.ae_buffer) == 0
        assert monitor.severe_count == 0

        # 2. Add a recent severe event
        recent_severe = {
            "trial_id": "TEST-OPT",
            "severity": 4,
            "timestamp": (now - timedelta(days=1)).isoformat()
        }
        await monitor.process_adverse_event(recent_severe)
        assert len(monitor.ae_buffer) == 1
        assert monitor.severe_count == 1

        # 3. Add many non-severe recent events to reach the threshold check
        for i in range(10):
            event = {
                "trial_id": "TEST-OPT",
                "severity": 1,
                "timestamp": now.isoformat()
            }
            await monitor.process_adverse_event(event)

        assert len(monitor.ae_buffer) == 11
        assert monitor.severe_count == 1
        # rate = 1 / 11 = 0.0909... which is < 0.15, so no alert triggered (would log)

    @pytest.mark.asyncio
    async def test_severe_count_accuracy(self, monitor):
        """Test that severe_count is accurately maintained during pruning."""
        now = datetime.now(timezone.utc)

        # Add 5 severe events, 2 old, 3 recent
        events = [
            {"severity": 4, "timestamp": (now - timedelta(days=10)).isoformat()},
            {"severity": 3, "timestamp": (now - timedelta(days=9)).isoformat()},
            {"severity": 4, "timestamp": (now - timedelta(days=1)).isoformat()},
            {"severity": 5, "timestamp": (now - timedelta(hours=1)).isoformat()},
            {"severity": 3, "timestamp": now.isoformat()},
        ]

        for e in events:
            e["trial_id"] = "TEST-OPT"
            await monitor.process_adverse_event(e)

        # The 2 old ones should have been pruned
        assert len(monitor.ae_buffer) == 3
        assert monitor.severe_count == 3

        # Verify buffer contents
        for _, event in monitor.ae_buffer:
            assert event["severity"] >= 3

    @pytest.mark.asyncio
    async def test_timezone_handling(self, monitor):
        """Test that both naive and aware timestamps are handled."""
        # Naive timestamp
        naive_event = {
            "trial_id": "TEST-OPT",
            "severity": 1,
            "timestamp": "2026-01-01T12:00:00"
        }
        # This is very old, should be pruned if compared to now
        await monitor.process_adverse_event(naive_event)
        assert len(monitor.ae_buffer) == 0

        # Aware timestamp
        aware_event = {
            "trial_id": "TEST-OPT",
            "severity": 1,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await monitor.process_adverse_event(aware_event)
        assert len(monitor.ae_buffer) == 1
