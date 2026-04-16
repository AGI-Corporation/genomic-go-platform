## 2026-04-16 - [O(1) Sliding Window for Safety Monitoring]
**Learning:** Unbounded list growth and O(n) filtering in high-frequency event processing (like `SafetyMonitoringSystem.process_adverse_event`) causes significant latency degradation as buffer size increases. Implementing a sliding window with `collections.deque` and running aggregates (like `severe_count`) reduces complexity from O(n) to O(1).
**Action:** Always prefer `collections.deque` with sliding window pruning and running aggregations for time-series event buffers to maintain constant-time performance.
