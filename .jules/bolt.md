## 2026-03-24 - [Optimize safety monitoring with sliding window]
**Learning:** O(N) list filtering in high-frequency event processing loops leads to (N^2)$ overall complexity and unbounded memory growth. A sliding window approach with `collections.deque` and running aggregations (e.g., counters) achieves O(1) amortized complexity and capped memory usage.
**Action:** Always prefer `collections.deque` with pruning and running counters for rolling window calculations in stream-based components like `SafetyMonitoringSystem`. Ensure timezone-aware comparisons (UTC) for robust datetime logic.
