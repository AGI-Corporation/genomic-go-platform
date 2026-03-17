## 2026-02-14 - [Optimization] O(1) Sliding Window for Safety Monitoring

**Learning:** Unbounded list growth for event buffers combined with O(N) re-scanning in high-frequency paths (like adverse event streams) leads to quadratic performance degradation as the trial progresses. Using `collections.deque` with a sliding window approach maintains O(1) amortized complexity. Additionally, mixing naive and aware datetimes when parsing ISO strings from Kafka is a common source of runtime TypeErrors in Python 3.12+.

**Action:** Always prefer `deque` for time-windowed buffers and ensure consistent UTC awareness using `datetime.now(timezone.utc)` and explicit `.replace(tzinfo=timezone.utc)` for parsed naive strings.
