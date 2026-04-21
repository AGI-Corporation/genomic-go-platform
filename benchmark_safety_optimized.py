import time
import asyncio
import sys
import os
from datetime import datetime, timedelta, timezone

# Add src to path
sys.path.insert(0, os.path.join(os.getcwd(), "src"))

from clinical_trials.realtime_optimizer import SafetyMonitoringSystem

async def benchmark_optimized():
    monitor = SafetyMonitoringSystem(trial_id="TEST-001")
    # All internal logic is now UTC-aware, so use UTC-aware here
    now = datetime.now(timezone.utc)

    # Generate 5000 events
    events = []
    for i in range(5000):
        event = {
            "trial_id": "TEST-001",
            "severity": i % 5,
            "timestamp": (now - timedelta(minutes=i)).isoformat()
        }
        events.append(event)

    print("Starting benchmark of OPTIMIZED SafetyMonitoringSystem.process_adverse_event with 5000 events...")
    start_time = time.time()
    for event in events:
        await monitor.process_adverse_event(event)
    end_time = time.time()

    print(f"Processing 5000 events took: {end_time - start_time:.4f} seconds")
    print(f"Final buffer size: {len(monitor.ae_buffer)}")
    print(f"Final severe count: {monitor.severe_count}")

if __name__ == "__main__":
    asyncio.run(benchmark_optimized())
