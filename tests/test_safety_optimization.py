
import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from clinical_trials.realtime_optimizer import SafetyMonitoringSystem
from unittest.mock import patch, AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_safety_monitoring_sliding_window():
    monitor = SafetyMonitoringSystem(trial_id="TEST-TRIAL", safety_threshold=0.2)

    # Use a fixed "now" for testing pruning
    base_now = datetime(2026, 1, 10, tzinfo=timezone.utc)

    with patch('clinical_trials.realtime_optimizer.datetime') as mock_datetime:
        mock_datetime.now.return_value = base_now
        mock_datetime.fromisoformat = datetime.fromisoformat

        # 1. Add event from 6 days ago (relative to base_now)
        old_time = (base_now - timedelta(days=6)).isoformat()
        await monitor.process_adverse_event({"severity": 4, "timestamp": old_time})
        assert len(monitor.ae_buffer) == 1
        assert monitor.severe_count == 1

        # 2. Advance "now" by 2 days. The old event is now 8 days old relative to new "now".
        mock_datetime.now.return_value = base_now + timedelta(days=2)
        new_time = (base_now + timedelta(days=2)).isoformat()

        # Adding a new event should trigger pruning of the old one
        await monitor.process_adverse_event({"severity": 1, "timestamp": new_time})
        assert len(monitor.ae_buffer) == 1
        assert monitor.severe_count == 0
        assert monitor.ae_buffer[0][1]["severity"] == 1

@pytest.mark.asyncio
async def test_safety_monitoring_severe_count():
    monitor = SafetyMonitoringSystem(trial_id="TEST-TRIAL", safety_threshold=0.2)
    now = datetime.now(timezone.utc).isoformat()

    for i in range(5):
        await monitor.process_adverse_event({"severity": 3, "timestamp": now})
    for i in range(5):
        await monitor.process_adverse_event({"severity": 1, "timestamp": now})

    assert len(monitor.ae_buffer) == 10
    assert monitor.severe_count == 5

@pytest.mark.asyncio
async def test_safety_alert_trigger():
    monitor = SafetyMonitoringSystem(trial_id="TEST-TRIAL", safety_threshold=0.1)
    now = datetime.now(timezone.utc).isoformat()

    with patch.object(monitor, 'trigger_safety_alert', new_callable=AsyncMock) as mock_alert:
        # Need > 10 events to trigger
        for i in range(11):
            severity = 4 if i == 0 or i == 1 else 1 # 2/11 = ~18% > 10%
            await monitor.process_adverse_event({"severity": severity, "timestamp": now})

        assert mock_alert.called
        rate, events = mock_alert.call_args[0]
        assert rate == pytest.approx(2/11)
        assert len(events) == 11
