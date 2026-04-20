## 2026-04-20 - Sliding Window Optimization for Safety Monitoring
**Learning:** Unbounded list growth for event buffers and O(N) filtering on hot paths (like processing real-time streams) causes significant performance degradation. Using `collections.deque` for O(1) pruning and maintaining running aggregations (like `severe_count`) reduces complexity to O(1) amortized.
**Action:** Always prefer `collections.deque` with sliding window pruning and running aggregations for high-frequency event processing. Ensure consistent timezone handling (UTC) for datetime comparisons to avoid `TypeError`.
