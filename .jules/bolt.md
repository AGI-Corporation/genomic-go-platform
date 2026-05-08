## 2026-02-14 - Optimized SafetyMonitoringSystem O(N) bottleneck

**Learning:** The `SafetyMonitoringSystem.process_adverse_event` was performing an O(N) list comprehension and sum on every incoming event to calculate a 7-day rolling average. This created a significant bottleneck as the buffer grew. Additionally, storing all events without pruning caused a memory leak. Standardizing on UTC-aware datetimes is critical when comparing against `datetime.now(timezone.utc)`.

**Action:** Use `collections.deque` for O(1) removals from the front and maintain running aggregations (like `severe_count`) to keep the hot path O(1) amortized. Always prune sliding windows to bound memory usage.
