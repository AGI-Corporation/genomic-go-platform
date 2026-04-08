import asyncio
import time
import uuid
from datetime import datetime, timedelta, timezone
from src.clinical_trials.realtime_optimizer import SafetyMonitoringSystem

async def benchmark():
    sms = SafetyMonitoringSystem(trial_id="test-trial")

    # Generate 5000 events over a period of time
    base_time = datetime.now(timezone.utc)
    events = []
    for i in range(5000):
        event_time = base_time - timedelta(days=i/1000) # Spread over 5 days
        events.append({
            "trial_id": "test-trial",
            "timestamp": event_time.isoformat(),
            "severity": i % 5, # some severe, some not
            "event_id": str(uuid.uuid4())
        })

    # Sort events by timestamp as they would arrive in real-time (mostly)
    events.sort(key=lambda x: x["timestamp"])

    start_time = time.time()
    for event in events:
        await sms.process_adverse_event(event)
    end_time = time.time()

    total_time = end_time - start_time
    avg_time = total_time / len(events)

    print(f"Total time for 5000 events: {total_time:.4f}s")
    print(f"Average time per event: {avg_time*1000:.4f}ms")

if __name__ == "__main__":
    asyncio.run(benchmark())
