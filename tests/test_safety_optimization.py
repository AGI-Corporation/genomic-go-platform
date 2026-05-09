import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from src.clinical_trials.realtime_optimizer import SafetyMonitoringSystem

@pytest.mark.asyncio
async def test_safety_monitoring_sliding_window():
    """Verify that events older than 7 days are pruned from the buffer."""
    monitor = SafetyMonitoringSystem(trial_id="TEST-TRIAL", safety_threshold=0.1)

    # Mock datetime.now to have a fixed reference point
    now = datetime.now(timezone.utc)

    # Event from 8 days ago
    old_event = {
        "timestamp": (now - timedelta(days=8)).isoformat(),
        "severity": 1,
        "trial_id": "TEST-TRIAL"
    }

    # Recent event
    recent_event = {
        "timestamp": (now - timedelta(days=2)).isoformat(),
        "severity": 1,
        "trial_id": "TEST-TRIAL"
    }

    with patch('src.clinical_trials.realtime_optimizer.datetime') as mock_datetime:
        mock_datetime.now.return_value = now
        mock_datetime.fromisoformat = datetime.fromisoformat

        await monitor.process_adverse_event(old_event)
        assert len(monitor.ae_buffer) == 0 # Pruned because it's older than 7 days

        await monitor.process_adverse_event(recent_event)
        assert len(monitor.ae_buffer) == 1 # Kept because it's within 7 days
        assert monitor.ae_buffer[0][1]["timestamp"] == recent_event["timestamp"]

@pytest.mark.asyncio
async def test_severe_rate_calculation():
    """Verify that the severe AE rate is calculated correctly."""
    monitor = SafetyMonitoringSystem(trial_id="TEST-TRIAL", safety_threshold=0.1)
    now = datetime.now(timezone.utc)

    # 11 events, 2 severe (severity >= 3) -> 18.18% rate
    for i in range(9):
        await monitor.process_adverse_event({
            "timestamp": now.isoformat(),
            "severity": 1,
            "trial_id": "TEST-TRIAL"
        })

    for i in range(2):
        await monitor.process_adverse_event({
            "timestamp": now.isoformat(),
            "severity": 3,
            "trial_id": "TEST-TRIAL"
        })

    # Total 11 events. Severe rate = 2/11 = 0.1818...
    # threshold is 0.1, so it should trigger.

    with patch.object(monitor, 'trigger_safety_alert', return_value=None) as mock_alert:
        await monitor.process_adverse_event({
            "timestamp": now.isoformat(),
            "severity": 1,
            "trial_id": "TEST-TRIAL"
        })
        # Now 12 events, 2 severe -> 2/12 = 0.166... Still > 0.1
        assert mock_alert.called

@pytest.mark.asyncio
async def test_datetime_robustness():
    """Verify that the system handles both naive and aware datetimes correctly."""
    monitor = SafetyMonitoringSystem(trial_id="TEST-TRIAL", safety_threshold=0.1)

    aware_now = datetime.now(timezone.utc)
    naive_now = datetime.now()

    # These should NOT crash
    await monitor.process_adverse_event({
        "timestamp": aware_now.isoformat(),
        "severity": 1,
        "trial_id": "TEST-TRIAL"
    })

    await monitor.process_adverse_event({
        "timestamp": naive_now.isoformat(),
        "severity": 1,
        "trial_id": "TEST-TRIAL"
    })

    # If the system currently crashes (as seen in benchmark), this test will fail,
    # which is good as it confirms the bug.
