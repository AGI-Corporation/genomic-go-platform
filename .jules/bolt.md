
## 2026-02-14 - [Optimization of Safety Monitoring Sliding Window]
**Learning:** Re-scanning and parsing entire buffers for rolling statistics in high-frequency event streams (like Adverse Events) creates (N^2)$ bottlenecks as the buffer grows.
**Action:** Use `collections.deque` for (1)$ pruning and maintain running aggregations (like `severe_count`) to achieve (1)$ amortized processing per event. Always store parsed, timezone-aware timestamps to avoid redundant parsing and runtime comparison errors.
