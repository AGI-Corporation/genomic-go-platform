
import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from clinical_trials.realtime_optimizer import SafetyMonitoringSystem
from unittest.mock import patch

@pytest.mark.asyncio
async def test_sliding_window_pruning():
    """Verify that old events are pruned and counters are updated correctly."""
    monitor = SafetyMonitoringSystem(trial_id="TEST-PRUNE", safety_threshold=0.5)

    now = datetime.now(timezone.utc)
    old_ts = (now - timedelta(days=8)).isoformat()
    recent_ts = (now - timedelta(days=1)).isoformat()

    # 1. Add an old severe event
    # It will be pruned immediately because it is 8 days old
    await monitor.process_adverse_event({
        "timestamp": old_ts,
        "severity": 4
    })
    assert len(monitor.ae_buffer) == 0
    assert monitor.severe_count == 0

    # 2. Add a recent severe event
    await monitor.process_adverse_event({
        "timestamp": recent_ts,
        "severity": 4
    })

    assert len(monitor.ae_buffer) == 1
    assert monitor.severe_count == 1
    assert monitor.ae_buffer[0]["timestamp"] == recent_ts

@pytest.mark.asyncio
async def test_safety_alert_triggering():
    """Verify that safety alerts are triggered when threshold is crossed."""
    monitor = SafetyMonitoringSystem(trial_id="TEST-ALERT", safety_threshold=0.2)
    now = datetime.now(timezone.utc)

    # Add 11 events (min 10 required)
    # 3 severe events out of 11 = 27%, which is > 20% threshold
    with patch.object(monitor, 'trigger_safety_alert', return_value=None) as mock_alert:
        for i in range(11):
            severity = 4 if i < 3 else 1
            await monitor.process_adverse_event({
                "timestamp": now.isoformat(),
                "severity": severity
            })

        mock_alert.assert_called_once()
        rate = mock_alert.call_args[0][0]
        assert abs(rate - 3/11) < 1e-6

@pytest.mark.asyncio
async def test_datetime_awareness_mix():
    """Verify that both naive and aware strings are handled safely."""
    monitor = SafetyMonitoringSystem(trial_id="TEST-TZ", safety_threshold=0.5)

    # Naive string (no offset)
    naive_ts = "2026-01-01T12:00:00"
    # Aware string
    aware_ts = "2026-01-01T12:00:00+00:00"

    # These should NOT raise TypeError now
    await monitor.process_adverse_event({"timestamp": naive_ts, "severity": 1})
    await monitor.process_adverse_event({"timestamp": aware_ts, "severity": 1})

    assert len(monitor.ae_buffer) == 0 # Pruned because they are very old
