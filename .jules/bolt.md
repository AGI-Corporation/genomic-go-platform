## 2026-02-14 - Optimize Safety Monitoring with O(1) Sliding Window
**Learning:** Using a standard list for rolling window calculations creates a linear performance degradation ($O(N)$ per event) and a memory leak as the buffer grows indefinitely. In high-frequency event streams like clinical trial safety monitoring, this can lead to system instability.
**Action:** Always prefer `collections.deque` for rolling windows to enable $O(1)$ pruning from the left. Maintain running aggregations (like `severe_count`) to avoid re-iterating the entire buffer on every update.
