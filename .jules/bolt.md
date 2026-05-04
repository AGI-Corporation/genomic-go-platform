# Bolt's Performance Journal

## 2026-02-14 - O(1) Sliding Window for Time-Series Streams
**Learning:** In systems processing event streams (like Adverse Events in clinical trials), using a simple list and re-filtering on every event leads to $O(N^2)$ total complexity for $N$ events and creates memory leaks if the buffer isn't pruned. A `collections.deque` combined with an amortized $O(1)$ pruning loop and running aggregators (like `severe_count`) provides massive speedups (~300x in this case) while maintaining a constant memory footprint.

**Action:** Always prefer `deque` and running totals over list comprehensions/filtering for rolling window calculations on high-frequency streams. Ensure timestamps are standardized to UTC-aware objects early to avoid comparison crashes.
