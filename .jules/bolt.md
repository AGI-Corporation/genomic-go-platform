# Bolt's Performance Journal

## 2026-04-24 - O(N^2) Bottleneck in Safety Monitoring
**Learning:** The `SafetyMonitoringSystem` used a list to store all adverse events and iterated through the entire history to filter recent events for every new event processed. This led to O(N^2) total complexity, which became a significant bottleneck as the trial progressed. Additionally, repeated parsing of ISO timestamps in the loop added massive overhead.
**Action:** Use `collections.deque` for a sliding window of events, maintain a running count of severe events, and pre-parse timestamps to achieve O(1) amortized time complexity per event.

## 2026-04-24 - Naive vs Aware Datetime Comparisons
**Learning:** Mixed use of `datetime.now(timezone.utc)` and `datetime.now(timezone.utc).replace(tzinfo=None)` caused `TypeError` when comparing timestamps parsed from ISO strings that included offset information.
**Action:** Standardize on aware UTC datetimes throughout the application to avoid comparison errors and ensure consistency.
