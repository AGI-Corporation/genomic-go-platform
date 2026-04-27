import pytest
from datetime import datetime, timedelta, timezone
from src.clinical_trials.realtime_optimizer import SafetyMonitoringSystem

@pytest.mark.asyncio
async def test_sliding_window_pruning():
    monitor = SafetyMonitoringSystem(trial_id="TEST-PRUNE", safety_threshold=0.15)

    # 1. Add an event that is 6 days old (not yet expired)
    mid_time = datetime.now(timezone.utc) - timedelta(days=6)
    mid_event = {
        "trial_id": "TEST-PRUNE",
        "severity": 3,
        "timestamp": mid_time.isoformat()
    }
    await monitor.process_adverse_event(mid_event)
    assert len(monitor.ae_buffer) == 1
    assert monitor.severe_count == 1

    # 2. Add a recent event
    recent_time = datetime.now(timezone.utc)
    recent_event = {
        "trial_id": "TEST-PRUNE",
        "severity": 1,
        "timestamp": recent_time.isoformat()
    }
    await monitor.process_adverse_event(recent_event)
    assert len(monitor.ae_buffer) == 2
    assert monitor.severe_count == 1

    # 3. Simulate passage of time by manually adding an event but with a "future" cutoff
    # Actually, we can just add an event and then wait? No, better to mock datetime.now or just use the existing logic.
    # If we add an event NOW, the 6-day-old event is still not 7 days old.

    # Let's add an event that is 8 days old. It should be pruned immediately.
    old_time = datetime.now(timezone.utc) - timedelta(days=8)
    old_event = {
        "trial_id": "TEST-PRUNE",
        "severity": 3,
        "timestamp": old_time.isoformat()
    }

    # If we add it, it's appended to the end. Pruning only happens from the front.
    # Since mid_event (6 days old) is at the front, pruning will NOT reach old_event if it's at the end.
    # BUT, if we added old_event FIRST, it would be at the front.

    monitor2 = SafetyMonitoringSystem(trial_id="TEST-PRUNE-2", safety_threshold=0.15)

    # Add 8-day-old event
    await monitor2.process_adverse_event(old_event)
    # It should be added then immediately pruned because it's older than 7 days.
    assert len(monitor2.ae_buffer) == 0
    assert monitor2.severe_count == 0

    # Add 6-day-old event
    await monitor2.process_adverse_event(mid_event)
    assert len(monitor2.ae_buffer) == 1
    assert monitor2.severe_count == 1

@pytest.mark.asyncio
async def test_severe_count_accuracy():
    monitor = SafetyMonitoringSystem(trial_id="TEST-COUNT", safety_threshold=0.15)

    now = datetime.now(timezone.utc)

    for i in range(20):
        event = {
            "trial_id": "TEST-COUNT",
            "severity": 3 if i < 5 else 1, # 5 severe events
            "timestamp": now.isoformat()
        }
        await monitor.process_adverse_event(event)

    assert len(monitor.ae_buffer) == 20
    assert monitor.severe_count == 5

@pytest.mark.asyncio
async def test_safety_alert_trigger(caplog):
    import logging
    monitor = SafetyMonitoringSystem(trial_id="TEST-ALERT", safety_threshold=0.1)

    now = datetime.now(timezone.utc)

    # Add 12 events, 3 of which are severe (25% rate > 10% threshold)
    for i in range(12):
        event = {
            "trial_id": "TEST-ALERT",
            "severity": 3 if i < 3 else 1,
            "timestamp": now.isoformat()
        }
        await monitor.process_adverse_event(event)

    assert "SAFETY ALERT for TEST-ALERT: Severe AE rate at 25.00%" in caplog.text
