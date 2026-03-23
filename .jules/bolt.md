## 2026-02-14 - [Optimize SafetyMonitoringSystem event processing]
**Learning:** List-based buffers for high-frequency event streams create an O(N) bottleneck due to re-scanning for sliding window calculations. Switching to `collections.deque` and maintaining a running counter allows for O(1) amortized processing time.
**Action:** Always prefer `collections.deque` with sliding window pruning and running aggregations for real-time monitoring systems to maintain O(1) performance as the buffer grows.
