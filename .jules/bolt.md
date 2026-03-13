## 2025-05-15 - [Sliding Window Optimization for Event Streams]
**Learning:** Event processing systems often use unbounded lists to store history, leading to $O(N^2)$ cumulative processing time and memory leaks. In Python, `collections.deque` combined with incremental counters (e.g., `severe_ae_count`) transforms these into $O(1)$ operations.
**Action:** Always check for `list.append()` without a corresponding removal strategy in classes that handle continuous data streams. Use `deque(maxlen=K)` if the window is fixed-size, or manual pruning if the window is time-based.
>>>>>>> REPLACE
