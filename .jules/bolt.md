## 2025-05-15 - Sliding Window Performance Anti-pattern

**Learning:** Using list comprehensions and `datetime.fromisoformat()` inside a high-frequency event processing loop causes $O(N^2)$ total complexity. Additionally, failing to prune old events leads to an unbounded memory leak.

**Action:** Always prefer `collections.deque` for event buffers. Implement an amortized $O(1)$ sliding window by pruning from the front and maintaining running aggregates (like `severe_count`) to avoid re-scanning the entire buffer. Parse timestamps once and store them with the event to avoid redundant parsing.
