
import time
import asyncio
import uuid
from datetime import datetime, timedelta, timezone
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from clinical_trials.realtime_optimizer import SafetyMonitoringSystem

async def run_benchmark(num_events=5000):
    monitor = SafetyMonitoringSystem(trial_id="BENCHMARK-001")

    # Generate mock events
    events = []
    base_time = datetime.now(timezone.utc)
    for i in range(num_events):
        event = {
            "trial_id": "BENCHMARK-001",
            "severity": i % 5,  # Some severe, some not
            "timestamp": (base_time - timedelta(minutes=num_events-i)).isoformat()
        }
        events.append(event)

    print(f"Starting benchmark with {num_events} events...")
    start_time = time.time()

    for event in events:
        await monitor.process_adverse_event(event)

    end_time = time.time()
    duration = end_time - start_time
    print(f"Total time for {num_events} events: {duration:.4f} seconds")
    print(f"Average time per event: {(duration/num_events)*1000:.4f} ms")
    return duration

if __name__ == "__main__":
    asyncio.run(run_benchmark())
