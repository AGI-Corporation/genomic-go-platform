## 2025-02-14 - [O(N^2) Event Processing Bottleneck]
**Learning:** High-frequency event streams (like adverse events in `SafetyMonitoringSystem`) using unbounded lists and repetitive $O(N)$ filtering/parsing on every new event lead to $O(N^2)$ cumulative complexity and memory leaks.
**Action:** Always prefer `collections.deque` for sliding windows and maintain running aggregations (e.g., `severe_count`) to achieve $O(1)$ amortized processing per event. Pre-parse timestamps before storing in the buffer to avoid redundant parsing.

## 2025-02-14 - [Datetime Naive/Aware Comparison]
**Learning:** Mixing naive and UTC-aware datetimes during comparison causes `TypeError` in production paths.
**Action:** Standardize on UTC-aware datetimes (`datetime.now(timezone.utc)`) and ensure `fromisoformat` results are checked for `tzinfo` and patched with `timezone.utc` if missing.
