import time
import asyncio
import numpy as np
import sys
import os
from datetime import datetime, timedelta, timezone

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from clinical_trials.realtime_optimizer import SafetyMonitoringSystem

async def benchmark_safety_monitor():
    monitor = SafetyMonitoringSystem(trial_id="BENCHMARK", safety_threshold=0.15)

    # Generate 10,000 events over the last 10 days
    num_events = 10000
    base_time = datetime.now(timezone.utc)
    events = []
    for i in range(num_events):
        # Distributed over 10 days
        event_time = base_time - timedelta(seconds=i * (10 * 24 * 3600 / num_events))
        # Use timezone-aware timestamps
        events.append({
            "trial_id": "BENCHMARK",
            "severity": 3 if i % 10 == 0 else 1, # 10% severe rate
            "timestamp": event_time.isoformat()
        })

    # Measure processing time
    start_time = time.time()
    for event in reversed(events): # Process from oldest to newest
        await monitor.process_adverse_event(event)
    end_time = time.time()

    total_time = end_time - start_time
    print(f"Processed {num_events} events in {total_time:.4f} seconds")
    print(f"Average time per event: {total_time/num_events:.6f} seconds")
    print(f"Final buffer size: {len(monitor.ae_buffer)}")
    print(f"Final severe count: {monitor.severe_ae_count}")
    return total_time

if __name__ == "__main__":
    asyncio.run(benchmark_safety_monitor())
