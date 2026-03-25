## 2026-02-14 - [O(1) Sliding Window for Safety Monitoring]
**Learning:** Unbounded list growth and O(N) re-scanning of event buffers is a common bottleneck in real-time stream processing. Using `collections.deque` with a pruning loop and maintaining running aggregations (like `severe_count`) transforms linear bottlenecks into constant-time operations.
**Action:** Always prefer `deque` for sliding windows and maintain running counts/sums for any metrics that need to be checked on every event arrival.
