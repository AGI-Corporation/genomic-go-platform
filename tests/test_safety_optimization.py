import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from src.clinical_trials.realtime_optimizer import SafetyMonitoringSystem
from unittest.mock import patch

@pytest.mark.asyncio
async def test_safety_monitor_threshold_detection():
    monitor = SafetyMonitoringSystem(trial_id="TEST-001", safety_threshold=0.2)

    # Send 11 events, 3 are severe (3/11 = 27.2% > 20%)
    # Use UTC for consistency
    base_time = datetime.now(timezone.utc)

    events = []
    for i in range(11):
        event = {
            "trial_id": "TEST-001",
            "severity": 4 if i < 3 else 1,
            # Reverse order to ensure they are within the window
            "timestamp": (base_time - timedelta(minutes=10-i)).isoformat()
        }
        events.append(event)

    with patch.object(monitor, 'trigger_safety_alert', return_value=None) as mock_alert:
        for event in events:
            await monitor.process_adverse_event(event)

        assert mock_alert.called
        # The rate should be checked
        last_call_args = mock_alert.call_args
        assert abs(last_call_args[0][0] - 3/11) < 1e-6

@pytest.mark.asyncio
async def test_safety_monitor_sliding_window():
    monitor = SafetyMonitoringSystem(trial_id="TEST-002", safety_threshold=0.2)

    base_time = datetime.now(timezone.utc)

    # Recent event
    recent_event = {
        "trial_id": "TEST-002",
        "severity": 1,
        "timestamp": base_time.isoformat()
    }

    # Event 8 days ago (should be pruned during NEXT process call if it's already there)
    old_event = {
        "trial_id": "TEST-002",
        "severity": 4,
        "timestamp": (base_time - timedelta(days=8)).isoformat()
    }

    await monitor.process_adverse_event(old_event)
    assert len(monitor.ae_buffer) == 0
    assert monitor.severe_count == 0

    await monitor.process_adverse_event(recent_event)
    assert len(monitor.ae_buffer) == 1
    assert monitor.severe_count == 0

@pytest.mark.asyncio
async def test_safety_monitor_accuracy_large_scale():
    monitor = SafetyMonitoringSystem(trial_id="TEST-003", safety_threshold=0.1)
    num_events = 100
    base_time = datetime.now(timezone.utc)

    # 10% severe events
    events = []
    for i in range(num_events):
        events.append({
            "trial_id": "TEST-003",
            "severity": 4 if i % 10 == 0 else 1,
            "timestamp": (base_time - timedelta(minutes=i)).isoformat()
        })

    # Sort events by timestamp so they are processed in order
    events.reverse()

    with patch.object(monitor, 'trigger_safety_alert', return_value=None) as mock_alert:
        for event in events:
            await monitor.process_adverse_event(event)

    assert len(monitor.ae_buffer) == 100
    assert monitor.severe_count == 10
