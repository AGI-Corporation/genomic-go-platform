## 2026-02-14 - [Adverse Event Stream Optimization]
**Learning:** High-frequency event streams (like Kafka-based AE monitoring) often feature redundant processing in sliding window aggregations. Replacing O(N) list filtering with an O(1) amortized deque-based sliding window and running counters yields massive performance gains (~294x in benchmarks). However, the O(1) pruning logic (popping from the left) assumes a mostly chronological event stream; out-of-order events might stay in the buffer longer than expected until a later event triggers their pruning.

**Action:** Use `collections.deque` for sliding windows and maintain running aggregations for high-frequency paths. Ensure timestamp comparisons are always UTC-aware to avoid `TypeError`.
