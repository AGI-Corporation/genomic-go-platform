## 2026-03-30 - [O(1) Sliding Window for Safety Monitoring]
**Learning:** Using a simple list for a time-series buffer leads to O(N) processing per event due to full buffer scanning and lack of pruning. This causes both a performance bottleneck and a memory leak as the application runs longer.
**Action:** Always prefer `collections.deque` for sliding windows to allow O(1) removals from the front. Maintain running aggregations (like `severe_count`) to keep analysis O(1) regardless of buffer size.
