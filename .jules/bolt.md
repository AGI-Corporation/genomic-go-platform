# Bolt's Performance Journal ⚡

## 2026-02-14 - Sliding Window for Real-Time Event Streams
**Learning:** Unbounded list growth and O(N) filtering in high-frequency event loops (like `process_adverse_event`) cause O(N²) total complexity and memory leaks.
**Action:** Always use `collections.deque` for event buffers and implement O(1) sliding window pruning. Cache parsed objects (like datetimes) in the buffer to avoid redundant expensive operations in the loop.

## 2026-02-14 - Datetime Type Safety in Comparisons
**Learning:** Comparing naive datetimes from `datetime.now()` with aware datetimes from ISO strings results in `TypeError`.
**Action:** Use `datetime.now(timezone.utc)` for all "now" comparisons and ensure parsed ISO strings are made aware with `replace(tzinfo=timezone.utc)` if they lack timezone info.
