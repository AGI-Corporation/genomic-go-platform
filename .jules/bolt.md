## 2026-04-30 - O(1) Sliding Window for Safety Monitoring
**Learning:** The previous implementation of `SafetyMonitoringSystem.process_adverse_event` used a list and re-parsed/re-scanned the entire history for every new event, leading to (N^2)$ overall complexity and a memory leak.
**Action:** Use `collections.deque` for O(1) removals from the front, parse timestamps once, and maintain running aggregations (like `severe_count`) to keep processing time constant regardless of history size.
