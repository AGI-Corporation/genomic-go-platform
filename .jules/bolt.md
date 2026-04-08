## 2025-05-15 - [Sliding Window Optimization for Adverse Event Processing]
**Learning:** Unbounded list growth in event buffers leads to $O(N^2)$ complexity when performing sliding window calculations (like rolling rates) and creates memory leaks. Timezone handling is critical when parsing ISO strings to avoid comparison crashes.
**Action:** Always prefer `collections.deque` with sliding window pruning and running aggregations (e.g., `severe_count`) to maintain $O(1)$ amortized performance and stable memory usage. Ensure all `datetime` objects are UTC-aware before comparison.
