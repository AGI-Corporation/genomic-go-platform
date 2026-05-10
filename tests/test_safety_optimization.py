import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from src.clinical_trials.realtime_optimizer import SafetyMonitoringSystem

class TestSafetyOptimization:
    @pytest.fixture
    def monitor(self):
        return SafetyMonitoringSystem(trial_id="TEST-OPT", safety_threshold=0.15)

    @pytest.mark.asyncio
    async def test_sliding_window_pruning(self, monitor):
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        # Event 8 days ago (should be pruned)
        event1 = {
            "trial_id": "TEST-OPT",
            "severity": 4,
            "timestamp": (now - timedelta(days=8)).isoformat()
        }
        # Event 1 day ago (should stay)
        event2 = {
            "trial_id": "TEST-OPT",
            "severity": 4,
            "timestamp": (now - timedelta(days=1)).isoformat()
        }

        await monitor.process_adverse_event(event1)
        assert len(monitor.ae_buffer) == 0 # event1 was pruned immediately because it's already old
        assert monitor.severe_count == 0

        await monitor.process_adverse_event(event2)
        assert len(monitor.ae_buffer) == 1
        assert monitor.severe_count == 1

    @pytest.mark.asyncio
    async def test_severe_count_accuracy(self, monitor):
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        # 5 severe events
        for i in range(5):
            await monitor.process_adverse_event({
                "trial_id": "TEST-OPT",
                "severity": 3,
                "timestamp": now.isoformat()
            })

        # 5 non-severe events
        for i in range(5):
            await monitor.process_adverse_event({
                "trial_id": "TEST-OPT",
                "severity": 2,
                "timestamp": now.isoformat()
            })

        assert len(monitor.ae_buffer) == 10
        assert monitor.severe_count == 5

        # Add one more to trigger rate calculation (limit is 10)
        await monitor.process_adverse_event({
            "trial_id": "TEST-OPT",
            "severity": 3,
            "timestamp": now.isoformat()
        })

        assert len(monitor.ae_buffer) == 11
        assert monitor.severe_count == 6
        # rate = 6/11 = 0.545 > 0.15
