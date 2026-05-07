
import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from src.clinical_trials.realtime_optimizer import SafetyMonitoringSystem
from unittest.mock import patch

class TestSafetyOptimization:
    @pytest.mark.asyncio
    async def test_sliding_window_pruning(self):
        system = SafetyMonitoringSystem(trial_id="test", safety_threshold=0.1)

        # Add a "just about to expire" event (6 days 23 hours 59 min ago)
        nearly_old_time = datetime.now(timezone.utc) - timedelta(days=6, hours=23, minutes=59)
        nearly_old_event = {
            "trial_id": "test",
            "timestamp": nearly_old_time.isoformat(),
            "severity": 1
        }
        await system.process_adverse_event(nearly_old_event)
        assert len(system.ae_buffer) == 1

        # Add a new event, should NOT trigger pruning of the nearly old one yet
        new_event = {
            "trial_id": "test",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "severity": 1
        }
        await system.process_adverse_event(new_event)
        assert len(system.ae_buffer) == 2

        # Add a truly old one, it should NOT be added
        old_time = datetime.now(timezone.utc) - timedelta(days=8)
        old_event = {
            "trial_id": "test",
            "timestamp": old_time.isoformat(),
            "severity": 1
        }
        await system.process_adverse_event(old_event)
        assert len(system.ae_buffer) == 2

    @pytest.mark.asyncio
    async def test_severe_count_accuracy(self):
        system = SafetyMonitoringSystem(trial_id="test", safety_threshold=0.1)

        # Add 5 severe and 5 non-severe
        for i in range(5):
            await system.process_adverse_event({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "severity": 3
            })
            await system.process_adverse_event({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "severity": 1
            })

        assert system.severe_count == 5
        assert len(system.ae_buffer) == 10

        # Manually inject an old severe event into the buffer head (violating chronological order for test)
        old_severe_time = datetime.now(timezone.utc) - timedelta(days=8)
        system.ae_buffer.appendleft((old_severe_time, {"severity": 3, "timestamp": old_severe_time.isoformat()}))
        system.severe_count += 1

        # Trigger pruning by adding a new event
        await system.process_adverse_event({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "severity": 1
        })

        assert system.severe_count == 5 # Should be back to 5 after pruning the old one
        assert len(system.ae_buffer) == 11 # 10 original + 1 new
