import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from src.clinical_trials.realtime_optimizer import SafetyMonitoringSystem
from unittest.mock import patch

class TestSafetyOptimization:
    @pytest.fixture
    def monitor(self):
        return SafetyMonitoringSystem(trial_id="TEST-001", safety_threshold=0.15)

    @pytest.mark.asyncio
    async def test_sliding_window_pruning(self, monitor):
        # 1. Mock time to be 10 days ago
        base_time = datetime.now(timezone.utc) - timedelta(days=10)

        with patch('src.clinical_trials.realtime_optimizer.datetime') as mock_datetime:
            mock_datetime.now.return_value = base_time
            mock_datetime.fromisoformat.side_effect = lambda x: datetime.fromisoformat(x)
            mock_datetime.utcnow = datetime.utcnow # For any other calls

            # Add 5 events with base_time
            for i in range(5):
                event = {
                    "trial_id": "TEST-001",
                    "severity": 3,
                    "timestamp": (base_time + timedelta(seconds=i)).isoformat()
                }
                await monitor.process_adverse_event(event)

            # Buffer should have 5 events, severe_count 5
            assert len(monitor.ae_buffer) == 5
            assert monitor.severe_count == 5

        # 2. Advance time to now
        now = datetime.now(timezone.utc)
        # Add 10 new events
        for i in range(10):
            event = {
                "trial_id": "TEST-001",
                "severity": 0,
                "timestamp": (now + timedelta(seconds=i)).isoformat()
            }
            await monitor.process_adverse_event(event)

        # The 5 old events should have been pruned
        # Buffer should have 10 events, severe_count 0
        assert len(monitor.ae_buffer) == 10
        assert monitor.severe_count == 0

    @pytest.mark.asyncio
    async def test_severe_count_accuracy(self, monitor):
        # Add mixed events within window
        now = datetime.now(timezone.utc)

        # 5 severe
        for i in range(5):
            await monitor.process_adverse_event({
                "trial_id": "TEST-001",
                "severity": 3,
                "timestamp": (now + timedelta(seconds=i)).isoformat()
            })

        # 5 non-severe
        for i in range(5, 10):
            await monitor.process_adverse_event({
                "trial_id": "TEST-001",
                "severity": 1,
                "timestamp": (now + timedelta(seconds=i)).isoformat()
            })

        assert len(monitor.ae_buffer) == 10
        assert monitor.severe_count == 5

        # Add one more severe to trigger alert check (but needs > 10 events)
        await monitor.process_adverse_event({
            "trial_id": "TEST-001",
            "severity": 4,
            "timestamp": (now + timedelta(seconds=11)).isoformat()
        })

        assert len(monitor.ae_buffer) == 11
        assert monitor.severe_count == 6
