import asyncio
import time
import json
from datetime import datetime, timedelta, timezone
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.getcwd(), "src"))

from clinical_trials.realtime_optimizer import SafetyMonitoringSystem

async def benchmark_safety_system(num_events=1000):
    monitor = SafetyMonitoringSystem(trial_id="TEST-BENCH", safety_threshold=0.15)

    events = []
    # Use UTC aware time to match the optimized implementation
    base_time = datetime.now(timezone.utc)
    for i in range(num_events):
        event = {
            "trial_id": "TEST-BENCH",
            "severity": (i % 10), # some will be >= 3 (specifically 3,4,5,6,7,8,9 which is 70%)
            "timestamp": (base_time + timedelta(seconds=i)).isoformat()
        }
        events.append(event)

    start_time = time.perf_counter()
    for event in events:
        await monitor.process_adverse_event(event)
    end_time = time.perf_counter()

    duration = end_time - start_time
    print(f"Processed {num_events} events in {duration:.4f} seconds")
    print(f"Average time per event: {duration/num_events:.6f} seconds")
    print(f"Final buffer size: {len(monitor.ae_buffer)}")

if __name__ == "__main__":
    # Same number as before to compare
    asyncio.run(benchmark_safety_system(5000))
