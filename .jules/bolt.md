## 2026-04-29 - [Optimized Safety Monitoring Sliding Window]
**Learning:** Unbounded list growth and O(N) filtering in high-frequency event processing paths (like `process_adverse_event`) creates a significant performance bottleneck and potential memory leak. Re-parsing timestamps on every call is also redundant and expensive.
**Action:** Use `collections.deque` with a sliding window approach for O(1) amortized pruning of old data. Maintain running aggregations (like `severe_count`) to avoid re-iterating the buffer for statistics. Parse and store timestamps once upon entry.
