## 2026-02-14 - [Sliding Window vs Memory Leak]
**Learning:** Using list comprehension for filtering time-based windows results in O(N^2) overall complexity and unbounded memory growth if the buffer isn't explicitly pruned. Storing parsed `datetime` objects alongside raw payloads in a `collections.deque` allows for O(1) amortized pruning and avoids redundant ISO parsing.
**Action:** Always prefer `collections.deque` with a `while` loop for sliding window pruning, and maintain running counters/aggregates to keep analysis O(1).

## 2026-02-14 - [Aware vs Naive Datetime robustness]
**Learning:** In production streams, ISO timestamps may or may not include timezone offsets. Comparing a naive datetime with an aware one (e.g., from `datetime.now(timezone.utc)`) causes a `TypeError`.
**Action:** Always normalize incoming timestamps to UTC-aware using `dt.replace(tzinfo=timezone.utc)` if `dt.tzinfo` is None.
