## 2026-02-14 - [Sliding Window Optimization]
**Learning:** Real-time event streams that use list comprehensions for "recent" event filtering suffer from O(N^2) total complexity as the stream grows. This also leads to unbounded memory growth if events are never removed.
**Action:** Always use 'collections.deque' with a 'while' loop to 'popleft()' expired events and maintain a running counter for metrics to achieve O(1) amortized complexity per event.

**Learning:** Mixing offset-naive and offset-aware datetimes is a common source of 'TypeError' in Python event processing.
**Action:** Explicitly handle timezone info during 'datetime.fromisoformat()' parsing to ensure consistency in comparisons.
