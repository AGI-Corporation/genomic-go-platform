## 2026-02-14 - [O(1) Sliding Window for AE Processing]
**Learning:** O(N) list scanning in real-time streams (like adverse events) is a performance anti-pattern that leads to processing latency increasing linearly with history size. Using `collections.deque` for O(1) removals from the front and maintaining running aggregations (like `severe_count`) allows for constant-time processing regardless of the window size.
**Action:** Always prefer `deque` and running counters for sliding window algorithms on data streams. Ensure timezone-aware datetime comparisons to avoid runtime errors.
