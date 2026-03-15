## 2026-03-15 - [Sliding Window & Timezone Robustness]
**Learning:** Unbounded list growth for event buffers combined with O(N) re-scanning is a major performance anti-pattern in real-time streams. Additionally, normalizing timestamps to aware UTC is critical when implementing sliding window pruning to avoid TypeErrors between naive strings and aware cutoffs.
**Action:** Use `collections.deque` for O(1) amortized sliding windows and always normalize incoming ISO timestamps to aware UTC before comparison.
