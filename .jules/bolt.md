## 2026-02-14 - [Sliding Window Optimization in Safety Monitoring]
**Learning:** Using a list for a sliding window with O(N) scanning on every update is a major performance bottleneck as the history grows. Standardizing on timezone-aware UTC datetimes is critical when comparing incoming event timestamps with system time to avoid TypeErrors.
**Action:** Always prefer collections.deque for sliding windows and maintain running counters/aggregates to keep processing complexity at O(1). Ensure all timestamps are coerced to timezone-aware UTC before comparison.
