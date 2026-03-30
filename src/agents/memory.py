"""Genomic.go Platform - Redis-backed agent memory.

Provides :class:`AgentMemory` for storing and retrieving experiment
context per agent, with optional TTL and a FIFO event history ring-buffer
backed by a Redis list.
"""

import json
import logging
from typing import Any, Dict, List, Optional

import redis

logger = logging.getLogger(__name__)


class AgentMemory:
    """Redis-backed key/value store and event history for a genomic agent.

    All keys are namespaced under ``genomic:<namespace>`` to avoid
    collisions when multiple agents share the same Redis instance.

    Args:
        redis_url: Redis connection URL (e.g. ``"redis://localhost:6379/0"``).
        namespace: Optional namespace prefix (default ``"agent"``).
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        namespace: str = "agent",
    ) -> None:
        self._namespace = namespace
        self._client: redis.Redis = redis.from_url(redis_url, decode_responses=True)
        logger.debug("AgentMemory initialised (namespace=%s)", namespace)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _key(self, *parts: str) -> str:
        """Build a namespaced Redis key.

        Args:
            *parts: Path segments joined with ``:``.

        Returns:
            Fully-qualified Redis key string.
        """
        return ":".join(["genomic", self._namespace] + list(parts))

    # ------------------------------------------------------------------
    # Key/value storage
    # ------------------------------------------------------------------

    def store(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> None:
        """Serialise *value* to JSON and store it under *key*.

        Args:
            key: Storage key (namespaced automatically).
            value: Any JSON-serialisable object.
            ttl: Optional expiry in seconds.  ``None`` means no expiry.
        """
        redis_key = self._key("kv", key)
        serialised = json.dumps(value)
        if ttl is not None:
            self._client.setex(redis_key, ttl, serialised)
        else:
            self._client.set(redis_key, serialised)
        logger.debug("store: key=%s ttl=%s", redis_key, ttl)

    def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve and deserialise the value stored under *key*.

        Args:
            key: Storage key (namespaced automatically).

        Returns:
            The deserialised Python object, or ``None`` if the key is absent.
        """
        redis_key = self._key("kv", key)
        raw = self._client.get(redis_key)
        if raw is None:
            return None
        return json.loads(raw)

    # ------------------------------------------------------------------
    # Event history
    # ------------------------------------------------------------------

    def append_to_history(self, agent_id: str, event: Dict[str, Any]) -> None:
        """Append *event* to the agent's FIFO event history list.

        Args:
            agent_id: Unique agent identifier.
            event: Arbitrary event dictionary (must be JSON-serialisable).
        """
        history_key = self._key("history", agent_id)
        self._client.rpush(history_key, json.dumps(event))
        logger.debug("append_to_history: agent=%s", agent_id)

    def get_history(
        self, agent_id: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Retrieve the most recent *limit* events for *agent_id*.

        Args:
            agent_id: Unique agent identifier.
            limit: Maximum number of events to return (default 100).

        Returns:
            List of event dictionaries, oldest first.
        """
        history_key = self._key("history", agent_id)
        raw_events = self._client.lrange(history_key, -limit, -1)
        return [json.loads(e) for e in raw_events]

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def clear(self, agent_id: str) -> None:
        """Delete all memory entries (kv and history) for *agent_id*.

        Args:
            agent_id: Unique agent identifier.
        """
        history_key = self._key("history", agent_id)
        self._client.delete(history_key)
        pattern = self._key("kv", f"{agent_id}:*")
        cursor = 0
        while True:
            cursor, keys = self._client.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                self._client.delete(*keys)
            if cursor == 0:
                break
        logger.debug("clear: agent=%s", agent_id)
