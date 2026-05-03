
import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from src.clinical_trials.realtime_optimizer import SafetyMonitoringSystem

@pytest.mark.asyncio
async def test_safety_monitoring_sliding_window():
    monitor = SafetyMonitoringSystem(trial_id="test-trial", safety_threshold=0.2)

    # Mock trigger_safety_alert to track calls
    monitor.trigger_safety_alert = MagicMock(side_effect=monitor.trigger_safety_alert)

    now = datetime.now(timezone.utc)

    # 1. Add 5 non-severe events (well within 7 days)
    for i in range(5):
        event = {
            "trial_id": "test-trial",
            "timestamp": (now - timedelta(days=1)).isoformat(),
            "severity": 1
        }
        await monitor.process_adverse_event(event)

    assert len(monitor.ae_buffer) == 5
    assert monitor.severe_count == 0

    # 2. Add 3 severe events
    for i in range(3):
        event = {
            "trial_id": "test-trial",
            "timestamp": now.isoformat(),
            "severity": 4
        }
        await monitor.process_adverse_event(event)

    # Total 8 events, 3 severe. Rate = 3/8 = 0.375 > 0.2
    # But wait, the original code had "if len(recent_aes) > 10"
    # I should probably respect that or lower it for testing.
    # Let's add more to reach 11 events.

    for i in range(3):
        event = {
            "trial_id": "test-trial",
            "timestamp": now.isoformat(),
            "severity": 1
        }
        await monitor.process_adverse_event(event)

    # Now 11 events total. 3 are severe. Rate = 3/11 = 0.27 > 0.2
    assert monitor.trigger_safety_alert.called

    # 3. Test sliding window pruning
    # Move time forward by 7 days and add a new event
    future_now = now + timedelta(days=7, seconds=1)

    with patch('src.clinical_trials.realtime_optimizer.datetime') as mock_datetime:
        mock_datetime.now.return_value = future_now
        mock_datetime.fromisoformat = datetime.fromisoformat
        mock_datetime.utcnow = datetime.utcnow

        # Adding a new event now should prune all previous events which are now > 7 days old
        await monitor.process_adverse_event({
            "trial_id": "test-trial",
            "timestamp": future_now.isoformat(),
            "severity": 1
        })

    # All previous events (from 'now' or 'now - 1d') are now > 7 days old relative to 'future_now'
    assert len(monitor.ae_buffer) == 1
    assert monitor.severe_count == 0

@pytest.mark.asyncio
async def test_severe_count_accuracy():
    monitor = SafetyMonitoringSystem(trial_id="test-trial", safety_threshold=0.1)
    now = datetime.now(timezone.utc)

    # Add 10 non-severe
    for i in range(10):
        await monitor.process_adverse_event({"trial_id": "test-trial", "timestamp": now.isoformat(), "severity": 1})

    # Add 2 severe
    await monitor.process_adverse_event({"trial_id": "test-trial", "timestamp": now.isoformat(), "severity": 4})
    await monitor.process_adverse_event({"trial_id": "test-trial", "timestamp": now.isoformat(), "severity": 5})

    assert monitor.severe_count == 2

    # Now add an event that triggers pruning of one of the severe ones
    # We need to mock "now" inside the method for deterministic pruning
    future_now = now + timedelta(days=8)

    with patch('src.clinical_trials.realtime_optimizer.datetime') as mock_datetime:
        mock_datetime.now.return_value = future_now
        mock_datetime.fromisoformat = datetime.fromisoformat
        mock_datetime.utcnow = datetime.utcnow

        # Adding a new event 8 days later should prune all previous events
        await monitor.process_adverse_event({"trial_id": "test-trial", "timestamp": future_now.isoformat(), "severity": 1})

    assert len(monitor.ae_buffer) == 1
    assert monitor.severe_count == 0
