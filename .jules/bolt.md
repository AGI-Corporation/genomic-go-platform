## 2026-02-14 - [Adverse Event Processing Bottleneck]
**Learning:** Using an unbounded list for event buffers and filtering the entire list on every new event is a major performance anti-pattern ($O(N^2)$ cumulative complexity). It also creates a memory leak.
**Action:** Use `collections.deque` for $O(1)$ removals from the head and implement a sliding window pruning mechanism. Maintain running aggregates (like `severe_count`) to avoid re-scanning the buffer.
