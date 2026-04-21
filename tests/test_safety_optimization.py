import pytest
import asyncio
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
from clinical_trials.realtime_optimizer import SafetyMonitoringSystem

@pytest.mark.asyncio
async def test_safety_sliding_window_pruning():
    monitor = SafetyMonitoringSystem(trial_id="TEST-001", safety_threshold=0.15)
    now = datetime.now(timezone.utc)

    # 1. Add 10 old events (older than 7 days)
    # NOTE: Our implementation prunes BEFORE adding if they are already old,
    # but actually it prunes AFTER adding the new one if we use a loop.
    # Wait, the code is:
    # self.ae_buffer.append((event_time, event))
    # ...
    # while self.ae_buffer and self.ae_buffer[0][0] < cutoff:
    #     self.ae_buffer.popleft()
    #
    # So if we add an old event, it gets added and then IMMEDIATELY pruned.
    # To test windowing, we should add events that are RECENT, then "wait" or add a new event that moves the window.

    # Let's add 10 events that are exactly 6 days 23 hours old.
    near_cutoff_time = now - timedelta(days=6, hours=23)
    for i in range(10):
        await monitor.process_adverse_event({
            "trial_id": "TEST-001",
            "severity": 3,
            "timestamp": (near_cutoff_time + timedelta(minutes=i)).isoformat()
        })

    # At this point, we have 10 events, all severe
    assert len(monitor.ae_buffer) == 10
    assert monitor.severe_count == 10

    # 2. Add 5 new events (within 7 days)
    # To trigger pruning, we need to add an event with a "current time" that makes previous ones old.
    # But our implementation uses `datetime.now(timezone.utc)` as the current time.
    # To test this without waiting 7 days, we can mock `datetime.now`.

    with patch("clinical_trials.realtime_optimizer.datetime") as mock_datetime:
        # Re-import datetime for our own use if needed, or just use the mock
        mock_datetime.now.return_value = now + timedelta(days=1)
        mock_datetime.fromisoformat = datetime.fromisoformat # Keep this working

        new_time = now + timedelta(hours=1)
        await monitor.process_adverse_event({
            "trial_id": "TEST-001",
            "severity": 1,
            "timestamp": new_time.isoformat()
        })

    # After 1 day, the near_cutoff_time (now - 6d 23h) is now (now + 1d - 7d 23h) = (now - 6d 23h)
    # The cutoff is now + 1d - 7d = now - 6d.
    # near_cutoff_time was now - 6d 23h, which IS older than now - 6d.
    # So they should be pruned.

    # Buffer should now only contain the 1 new event
    assert len(monitor.ae_buffer) == 1
    assert monitor.severe_count == 0

    # 3. Add more events to reach threshold
    for i in range(15):
        await monitor.process_adverse_event({
            "trial_id": "TEST-001",
            "severity": 4, # severe
            "timestamp": (new_time + timedelta(minutes=i+1)).isoformat()
        })

    # Buffer size: 1 (not severe) + 15 (severe) = 16
    # Severe count: 15
    assert len(monitor.ae_buffer) == 16
    assert monitor.severe_count == 15
    assert (15/16) > 0.15

if __name__ == "__main__":
    asyncio.run(test_safety_sliding_window_pruning())
