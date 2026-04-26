import pytest
import asyncio
from datetime import datetime, timedelta, timezone
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from clinical_trials.realtime_optimizer import SafetyMonitoringSystem

class TestSafetyOptimization:
    @pytest.mark.asyncio
    async def test_sliding_window_pruning(self):
        monitor = SafetyMonitoringSystem(trial_id="TEST", safety_threshold=0.15)

        now = datetime.now(timezone.utc)
        # Event 8 days old
        old_event = {
            "trial_id": "TEST",
            "severity": 4,
            "timestamp": (now - timedelta(days=8)).isoformat()
        }
        # Event 1 day old
        recent_event = {
            "trial_id": "TEST",
            "severity": 1,
            "timestamp": (now - timedelta(days=1)).isoformat()
        }

        # When we process old_event, it is added and then pruned because it's already older than 7 days
        await monitor.process_adverse_event(old_event)
        assert len(monitor.ae_buffer) == 0
        assert monitor.severe_count == 0

        # When we process recent_event, it is added and NOT pruned
        await monitor.process_adverse_event(recent_event)
        assert len(monitor.ae_buffer) == 1
        assert monitor.ae_buffer[0][1] == recent_event
        assert monitor.severe_count == 0

    @pytest.mark.asyncio
    async def test_severe_count_accuracy(self):
        monitor = SafetyMonitoringSystem(trial_id="TEST", safety_threshold=0.15)
        now = datetime.now(timezone.utc)

        for i in range(20):
            event = {
                "trial_id": "TEST",
                "severity": 4 if i < 5 else 1, # 5 severe events
                "timestamp": now.isoformat()
            }
            await monitor.process_adverse_event(event)

        assert len(monitor.ae_buffer) == 20
        assert monitor.severe_count == 5

    @pytest.mark.asyncio
    async def test_timezone_robustness(self):
        monitor = SafetyMonitoringSystem(trial_id="TEST", safety_threshold=0.15)

        # Test with naive timestamp string
        event = {
            "trial_id": "TEST",
            "severity": 1,
            "timestamp": "2026-01-01T12:00:00"
        }
        await monitor.process_adverse_event(event)
        assert len(monitor.ae_buffer) == 0 # Should be pruned as it's very old
