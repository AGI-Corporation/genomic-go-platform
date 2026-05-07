# Bolt's Performance Journal

## 2025-05-15 - Journal Created
**Learning:** Initializing Bolt's journal to track critical performance learnings.
**Action:** Always document significant performance findings here.

## 2025-05-15 - O(1) Sliding Window requires Chronological Stream
**Learning:** In `SafetyMonitoringSystem`, implementing an O(1) sliding window with `collections.deque` and a `while` loop for pruning assumes that incoming events are mostly chronological. If an event much older than the current window is inserted, it should be dropped immediately to prevent it from "poisoning" the buffer and requiring a full sort or O(N) pruning to maintain correctness.
**Action:** Always validate and potentially drop out-of-order/expired events when using deque-based sliding windows for real-time stream processing.
