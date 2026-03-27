## 2026-02-14 - Initial Journal
**Learning:** Initializing Bolt journal.
**Action:** Always document performance wins.

## 2026-02-14 - Sliding Window Performance Optimization
**Learning:** Replacing O(N) list comprehensions with a `collections.deque` sliding window and a running accumulator (`severe_count`) reduced processing time from ~37ms to ~0.6ms (~60x speedup) for 10,000 events. This also fixed a potential memory leak from unbounded buffer growth and a bug where naive and aware datetimes were compared.
**Action:** Always prefer `collections.deque` and running aggregations for high-frequency stream processing in this codebase.
