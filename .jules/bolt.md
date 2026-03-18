## 2026-03-18 - Sliding window optimization for SafetyMonitoringSystem

**Learning:** Replacing O(N) list filtering with a `collections.deque` and a running counter for the sliding window reduced processing time by ~300x (from 7.39ms to 0.02ms for 5000 events). This also fixed a potential memory leak from unbounded buffer growth.

**Learning:** When using `datetime.fromisoformat()` on ISO strings that might be naive, always check for `tzinfo` and normalize to `timezone.utc` before comparing with aware datetimes to prevent `TypeError`.

**Action:** Always prefer `collections.deque` with a sliding window and running aggregations for high-frequency event processing to maintain O(1) performance. Ensure all timestamp comparisons are timezone-aware.
