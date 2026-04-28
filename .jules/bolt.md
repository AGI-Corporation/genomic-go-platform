## 2026-04-28 - O(1) Sliding Window for Real-Time Safety Monitoring
**Learning:** The original `SafetyMonitoringSystem` suffered from O(N) complexity on every event processing due to full-buffer filtering and a memory leak from unbounded list growth. In high-frequency event streams (like clinical trial adverse events), this leads to quadratic performance degradation and eventual OOM.
**Action:** Always prefer `collections.deque` for sliding window buffers and maintain running aggregations (like `severe_count`) to ensure O(1) amortized processing time and constant memory footprint.
