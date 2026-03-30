import asyncio
import time
import json
from datetime import datetime, timedelta, timezone
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from clinical_trials.realtime_optimizer import SafetyMonitoringSystem

async def run_benchmark(num_events=5000):
    monitor = SafetyMonitoringSystem(trial_id="BENCHMARK-TRIAL")

    # Pre-generate events
    events = []
    # Use UTC-aware datetime for comparison as optimized code handles both
    base_time = datetime.now(timezone.utc)
    for i in range(num_events):
        # Events spread over 10 days
        timestamp = (base_time - timedelta(days=10) + timedelta(seconds=i * (10*24*3600/num_events))).isoformat()
        events.append({
            "trial_id": "BENCHMARK-TRIAL",
            "severity": i % 5, # some severe, some not
            "timestamp": timestamp
        })

    print(f"Starting benchmark with {num_events} events...")
    start_time = time.perf_counter()

    for event in events:
        await monitor.process_adverse_event(event)

    end_time = time.perf_counter()
    duration = end_time - start_time

    print(f"Processed {num_events} events in {duration:.4f} seconds")
    print(f"Average time per event: {(duration/num_events)*1000:.4f} ms")
    print(f"Final buffer size: {len(monitor.ae_buffer)}")

    return duration

if __name__ == "__main__":
    asyncio.run(run_benchmark())
