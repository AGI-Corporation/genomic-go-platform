## 2026-02-14 - [Optimization of SafetyMonitoringSystem]
**Learning:** The `SafetyMonitoringSystem.process_adverse_event` method had an O(N) bottleneck due to iterating over an unbounded `ae_buffer` on every new event. This would lead to degraded performance over time as the trial progresses.
**Action:** Use a `collections.deque` and a sliding window approach to maintain O(1) amortized complexity for event processing and keep memory usage bounded.
