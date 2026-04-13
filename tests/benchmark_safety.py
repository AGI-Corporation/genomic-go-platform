import asyncio
import time
from datetime import datetime, timedelta, timezone
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from clinical_trials.realtime_optimizer import SafetyMonitoringSystem
import logging

# Disable logging for cleaner benchmark
logging.getLogger("clinical_trials.realtime_optimizer").setLevel(logging.CRITICAL)

async def benchmark():
    monitor = SafetyMonitoringSystem(trial_id="TEST-TRIAL")

    # Pre-fill with some events
    num_events = 5000
    base_time = datetime.now(timezone.utc)

    events = []
    for i in range(num_events):
        # Events spanning the last 10 days
        event_time = base_time - timedelta(minutes=i * 2)
        events.append({
            "trial_id": "TEST-TRIAL",
            "severity": (i % 5) + 1, # Severity 1-5
            "timestamp": event_time.isoformat()
        })

    # Reverse to process them in chronological order
    events.reverse()

    print(f"Starting benchmark with {num_events} events...")
    start_time = time.perf_counter()
    for event in events:
        await monitor.process_adverse_event(event)
    end_time = time.perf_counter()

    total_time = end_time - start_time
    print(f"Processed {num_events} events in {total_time:.4f} seconds")
    print(f"Average time per event: {(total_time/num_events)*1000:.4f} ms")

if __name__ == "__main__":
    asyncio.run(benchmark())
