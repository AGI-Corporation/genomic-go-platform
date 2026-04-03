## 2025-05-15 - [Optimize Safety Monitoring System with O(1) Sliding Window]
**Learning:** Unbounded list growth and redundant O(N) scanning of historical buffers for rolling metrics is a major performance bottleneck. Using `collections.deque` with a sliding window pruning approach and maintaining running totals converts O(N) operations to O(1) amortized.
**Action:** Always prefer `collections.deque` for rolling buffers and maintain running aggregations instead of re-calculating from the full buffer on every new event.
