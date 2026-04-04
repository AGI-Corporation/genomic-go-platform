## 2026-02-14 - [Optimize safety monitoring with O(1) sliding window]
**Learning:** Unbounded list growth and O(N) filtering in high-frequency event streams (like Kafka consumers) lead to quadratic performance degradation and memory leaks.
**Action:** Always prefer `collections.deque` with a sliding window pruning strategy and running counters to maintain O(1) time and space complexity for rolling aggregations.
