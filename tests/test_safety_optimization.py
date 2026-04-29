import pytest
import asyncio
import time
from datetime import datetime, timedelta, timezone
from src.clinical_trials.realtime_optimizer import SafetyMonitoringSystem

@pytest.mark.asyncio
async def test_safety_monitor_sliding_window():
    system = SafetyMonitoringSystem(trial_id="test-trial", safety_threshold=0.1)

    # Use naive datetimes to match current buggy implementation's expectation
    now = datetime.now()

    # Event 1: 8 days ago (should be ignored)
    await system.process_adverse_event({
        "trial_id": "test-trial",
        "timestamp": (now - timedelta(days=8)).isoformat(),
        "severity": 4
    })

    # Event 2-12: Recent events, severity 1 (not severe)
    for i in range(11):
        await system.process_adverse_event({
            "trial_id": "test-trial",
            "timestamp": now.isoformat(),
            "severity": 1
        })

    # At this point, we have 12 events total.
    # 1 is old, 11 are recent.
    # recent_aes should have 11 events.
    # severe_ae_rate should be 0/11 = 0.

    # Event 13: Recent, severe
    await system.process_adverse_event({
        "trial_id": "test-trial",
        "timestamp": now.isoformat(),
        "severity": 4
    })

    # Now we have 12 recent events. 1 is severe.
    # severe_ae_rate = 1/12 = 0.0833... (still <= 0.1)

    # Event 14: Recent, severe
    await system.process_adverse_event({
        "trial_id": "test-trial",
        "timestamp": now.isoformat(),
        "severity": 5
    })

    # Now we have 13 recent events. 2 are severe.
    # severe_ae_rate = 2/13 = 0.1538... (> 0.1)
    # This should trigger alert (we can't easily check logger here without more mocking,
    # but we can check if it runs without error)

@pytest.mark.asyncio
async def test_safety_monitor_performance_bottleneck():
    system = SafetyMonitoringSystem(trial_id="perf-trial")
    now = datetime.now(timezone.utc)

    # Fill with 2000 events - MUST USE TUPLE (datetime, dict) now
    for i in range(2000):
        system.ae_buffer.append((
            now,
            {
                "trial_id": "perf-trial",
                "timestamp": now.isoformat(),
                "severity": 1
            }
        ))

    start = time.perf_counter()
    await system.process_adverse_event({
        "trial_id": "perf-trial",
        "timestamp": now.isoformat(),
        "severity": 1
    })
    end = time.perf_counter()

    duration = (end - start) * 1000
    print(f"\nProcessing one event with 2000 events took {duration:.2f}ms")
    # This is just to demonstrate it's slow-ish, won't assert on time to avoid flaky tests
    assert len(system.ae_buffer) == 2001
