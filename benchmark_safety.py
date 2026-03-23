
import asyncio
import time
import uuid
from datetime import datetime, timedelta, timezone
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from clinical_trials.realtime_optimizer import SafetyMonitoringSystem

async def benchmark_safety_monitor():
    monitor = SafetyMonitoringSystem(trial_id="BENCHMARK-001")

    # Pre-fill buffer with some events
    initial_events = 1000
    for i in range(initial_events):
        event = {
            "trial_id": "BENCHMARK-001",
            "severity": i % 5,
            "timestamp": (datetime.now(timezone.utc) - timedelta(days=i/100)).isoformat()
        }
        await monitor.process_adverse_event(event)

    print(f"Buffer size after pre-fill: {len(monitor.ae_buffer)}")

    # Measure processing time for new events
    num_test_events = 100
    start_time = time.perf_counter()

    for i in range(num_test_events):
        event = {
            "trial_id": "BENCHMARK-001",
            "severity": 4, # Severe
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await monitor.process_adverse_event(event)

    end_time = time.perf_counter()
    avg_time = (end_time - start_time) / num_test_events
    print(f"Average processing time per event (with {initial_events} existing events): {avg_time*1000:.4f} ms")
    print(f"Final buffer size: {len(monitor.ae_buffer)}")

if __name__ == "__main__":
    asyncio.run(benchmark_safety_monitor())
