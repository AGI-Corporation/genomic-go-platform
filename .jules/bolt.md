## 2026-02-14 - O(1) Sliding Window for Safety Monitoring
**Learning:** The `SafetyMonitoringSystem` used a growing list for adverse events and re-scanned it entirely for every new event, leading to $O(N^2)$ complexity over time. Additionally, redundant `fromisoformat` calls and timezone-naive comparisons were major bottlenecks and reliability risks.
**Action:** Use `collections.deque` for $O(1)$ removals from the front, maintain running aggregates (like `severe_count`) to avoid re-scanning, and store pre-parsed UTC-aware timestamps to eliminate redundant processing.
