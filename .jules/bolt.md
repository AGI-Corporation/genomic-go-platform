## 2026-04-10 - [O(1) Sliding Window for Safety Monitoring]
**Learning:** Using a list and re-filtering for a rolling window is a common O(N) bottleneck that scales poorly with event frequency. Storing parsed timestamps in a `deque` and maintaining running aggregations (like `severe_count`) reduces complexity to O(1) amortized.
**Action:** Always check if a rolling time window can be optimized with a sliding window and a `collections.deque` instead of list comprehensions.

**Learning:** `datetime.fromisoformat` can return naive or aware datetimes depending on the input string, which leads to `TypeError` during comparison.
**Action:** Always explicitly check for `tzinfo` and normalize to `timezone.utc` before comparing datetimes.
