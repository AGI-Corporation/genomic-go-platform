# ⚡ Bolt's Performance Journal

## 2026-02-14 - O(N) Sliding Window in Safety Monitoring
**Learning:** The `SafetyMonitoringSystem` was using a list to store adverse events and re-iterating over the entire list for every new event to filter by timestamp and sum severe events. This led to O(N) complexity and a memory leak as the list grew indefinitely.
**Action:** Use `collections.deque` for O(1) pruning from the left and maintain a running `severe_count` to keep the safety rate calculation O(1). Store parsed timestamps with events to avoid redundant parsing.
