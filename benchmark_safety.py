import asyncio
import time
import json
from datetime import datetime, timedelta, timezone
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from clinical_trials.realtime_optimizer import SafetyMonitoringSystem

async def benchmark_safety_system():
    monitor = SafetyMonitoringSystem(trial_id="BENCH-001", safety_threshold=0.15)

    num_events = 5000
    # Use naive datetime for the events to match the monitor's bug
    base_time = datetime.now()

    events = []
    for i in range(num_events):
        event = {
            "trial_id": "BENCH-001",
            "severity": 1 + (i % 5),  # Severities 1, 2, 3, 4, 5
            "timestamp": (base_time + timedelta(minutes=i)).isoformat()
        }
        events.append(event)

    print(f"Benchmarking {num_events} events...")
    start_time = time.time()

    for event in events:
        await monitor.process_adverse_event(event)

    end_time = time.time()
    total_time = end_time - start_time
    print(f"Total time: {total_time:.4f} seconds")
    print(f"Average time per event: {(total_time/num_events)*1000:.4f} ms")

if __name__ == "__main__":
    asyncio.run(benchmark_safety_system())
