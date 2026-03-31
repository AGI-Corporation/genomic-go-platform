## 2026-02-14 - [O(1) Sliding Window for Safety Monitoring]
**Learning:** Using a list-based buffer for rolling window calculations leads to O(N) processing time per event, which becomes a major bottleneck as the buffer grows. Storing pre-parsed timestamps in a deque and maintaining a running counter allows for O(1) amortized processing.
**Action:** Always prefer collections.deque with sliding window pruning and running aggregations for real-time stream processing to maintain constant-time performance. Ensure timezone-aware comparisons to avoid TypeErrors.
