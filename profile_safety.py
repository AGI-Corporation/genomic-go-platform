import time
import asyncio
import sys
import os
from datetime import datetime, timedelta, timezone

# Add src to path
sys.path.insert(0, os.path.join(os.getcwd(), "src"))

from clinical_trials.realtime_optimizer import SafetyMonitoringSystem

async def profile_safety_system():
    monitor = SafetyMonitoringSystem(trial_id="TEST-001")
    # Using naive datetime to match the implementation's current behavior
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Generate 5000 events
    events = []
    for i in range(5000):
        # Stagger them slightly so they are mostly within the 7-day window
        event = {
            "trial_id": "TEST-001",
            "severity": i % 5,
            "timestamp": (now - timedelta(minutes=i)).isoformat()
        }
        events.append(event)

    print("Starting profile of SafetyMonitoringSystem.process_adverse_event with 5000 events...")
    start_time = time.time()
    for event in events:
        await monitor.process_adverse_event(event)
    end_time = time.time()

    print(f"Processing 5000 events took: {end_time - start_time:.4f} seconds")

if __name__ == "__main__":
    asyncio.run(profile_safety_system())
