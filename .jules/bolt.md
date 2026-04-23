# Bolt's Performance Journal ⚡

## 2026-02-14 - O(1) Sliding Window for Safety Monitoring
**Learning:** Real-time event streams with rolling windows are common bottlenecks when implemented with standard lists and (N)$ filtering. Unbounded buffer growth also leads to memory leaks.
**Action:** Use `collections.deque` for amortized (1)$ removals from the front and maintain running aggregations (like `severe_count`) to avoid full buffer scans. Always ensure timezone consistency (UTC-aware) to prevent runtime errors in comparison logic.
