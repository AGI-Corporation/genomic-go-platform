## 2026-02-14 - [O(1) Sliding Window for Safety Monitoring]
**Learning:** Using an unbounded list for a real-time event buffer creates $O(N^2)$ complexity over time and a memory leak. Replacing it with `collections.deque` and a sliding window pruning approach reduces complexity to $O(1)$ amortized and stabilizes memory usage.
**Action:** Always prefer `deque` for rolling windows and maintain running aggregates to avoid re-scanning buffers.
