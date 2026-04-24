
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, AsyncMock
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from clinical_trials.realtime_optimizer import SafetyMonitoringSystem

@pytest.mark.asyncio
async def test_safety_monitoring_sliding_window_pruning():
    monitor = SafetyMonitoringSystem(trial_id="TEST-WINDOW", safety_threshold=0.15)

    def get_ts(days_ago):
        dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
        return dt.isoformat()

    # 1. Add 5 severe events 8 days ago
    for i in range(5):
        event = {
            "trial_id": "TEST-WINDOW",
            "severity": 4,
            "timestamp": get_ts(8)
        }
        await monitor.process_adverse_event(event)

    # After processing these, they are already older than 7 days,
    # but the pruning happens AFTER adding them and checking cutoff.
    # Actually, in my optimized code:
    # 1. Append (event_time, event)
    # 2. Increment severe_count
    # 3. while buffer[0] < cutoff: popleft, decrement severe_count
    # Since these are 8 days ago, they will be appended and then immediately pruned if I use datetime.now() as cutoff.

    # Wait, let's see:
    # event_time = 8 days ago
    # cutoff = now - 7 days = 7 days ago
    # event_time < cutoff is True.
    # So they should be pruned immediately.
    assert len(monitor.ae_buffer) == 0
    assert monitor.severe_count == 0

    # 2. Add 10 non-severe events now
    for i in range(10):
        event = {
            "trial_id": "TEST-WINDOW",
            "severity": 1,
            "timestamp": get_ts(0)
        }
        await monitor.process_adverse_event(event)

    # buffer size should be 10
    assert len(monitor.ae_buffer) == 10
    assert monitor.severe_count == 0

@pytest.mark.asyncio
async def test_severe_ae_rate_calculation_trigger():
    monitor = SafetyMonitoringSystem(trial_id="TEST-RATE", safety_threshold=0.15)

    def get_ts(days_ago):
        dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
        return dt.isoformat()

    # Add 11 events within the 7-day window
    # 3 severe, 8 non-severe -> 3/11 = 27.27% > 15% threshold

    events = []
    for i in range(3):
        events.append({"trial_id": "TEST-RATE", "severity": 3, "timestamp": get_ts(0)})
    for i in range(8):
        events.append({"trial_id": "TEST-RATE", "severity": 1, "timestamp": get_ts(0)})

    with patch.object(SafetyMonitoringSystem, 'trigger_safety_alert', new_callable=AsyncMock) as mock_alert:
        for event in events:
            await monitor.process_adverse_event(event)

        # Check if alert was triggered
        mock_alert.assert_called()
        args, kwargs = mock_alert.call_args
        rate = args[0]
        assert pytest.approx(rate, 0.01) == 3/11

        # Check that events passed to alert are the dicts, not tuples
        recent_events = args[1]
        assert isinstance(recent_events[0], dict)
        assert "severity" in recent_events[0]
