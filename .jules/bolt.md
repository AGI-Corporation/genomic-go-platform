## 2026-02-14 - Optimized Safety Monitoring with O(1) Sliding Window
**Learning:** Replacing an O(N) list-based sliding window with a `collections.deque` and a running counter reduces event processing time from O(N) to O(1) amortized. Assuming events arrive mostly in chronological order allows for efficient pruning by stopping the loop as soon as a non-expired event is reached.
**Action:** Always prefer `collections.deque` and running aggregations for sliding window calculations over list-based filtering.
