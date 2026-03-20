# Bolt's Journal - Critical Learnings

## 2025-05-15 - Initial Performance Review
**Learning:** Found O(N) list scanning in `SafetyMonitoringSystem.process_adverse_event` which will degrade as the number of events grows. Also noted a potential `TypeError` in datetime comparisons due to mixing naive and aware datetimes.
**Action:** Replace `ae_buffer` with `collections.deque` and implement a more efficient sliding window with running counters. Fix datetime comparison logic.
