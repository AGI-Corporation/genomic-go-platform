# Bolt's Performance Journal

## 2026-04-26 - [O(1) Sliding Window for Event Streams]
**Learning:** In high-frequency event processing paths, using a standard list and performing O(n) filtering/summation on every new event causes exponential performance degradation as the buffer grows. Additionally, without pruning, the buffer becomes a memory leak.
**Action:** Use `collections.deque` for O(1) removals from the front and maintain running aggregations (like `severe_count`) to achieve O(1) amortized processing time. Always implement a pruning mechanism for time-windowed buffers.

## 2026-04-26 - [Naive vs Aware Datetime Comparisons]
**Learning:** Mixing naive datetimes (from `datetime.now()` or some ISO strings) with aware datetimes (from `datetime.now(timezone.utc)`) in a comparison triggers a `TypeError`.
**Action:** Always normalize incoming timestamps using `datetime.fromisoformat(ts).replace(tzinfo=timezone.utc)` if `tzinfo` is missing to ensure robust comparisons with system-level UTC-aware datetimes.
