## 2025-05-15 - Sliding Window Performance in Safety Monitoring
**Learning:** Unbounded list growth for event buffers is a performance anti-pattern. Always prefer `collections.deque` with sliding window pruning and running aggregations to maintain O(1) performance. Comparing naive vs aware datetimes in Python raises `TypeError` - robust handling requires checking `tzinfo`.
**Action:** Use `collections.deque` for time-series buffers and ensure all timestamps are normalized to UTC-aware before comparison.
