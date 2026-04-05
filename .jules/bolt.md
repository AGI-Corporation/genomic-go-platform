## 2025-05-14 - [Async I/O in NANDA Integration]
**Learning:** Using synchronous `requests` inside `async` methods blocks the entire event loop, negating the benefits of concurrency. Sequential loops with hardcoded `asyncio.sleep` for staggering deployments are significant bottlenecks when scaling agent swarms.
**Action:** Always prefer `aiohttp` for non-blocking HTTP requests in an async context. Use `asyncio.gather` to parallelize independent operations like agent deployments and swarm initializations. Use a shared `ClientSession` with a managed lifecycle for efficient connection pooling.
