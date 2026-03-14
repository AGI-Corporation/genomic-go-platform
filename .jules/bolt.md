## 2026-02-14 - [Efficient Stream Processing in SafetyMonitoringSystem]
**Learning:** Using a list for an event buffer with $O(N)$ recalculations for rolling statistics leads to $O(N^2)$ cumulative complexity and potential memory leaks as the buffer grows indefinitely.
**Action:** Always prefer `collections.deque` for event buffers with a pruning mechanism to maintain a sliding window. Use running counts or sums to keep the computational complexity $O(1)$ amortized per event.
