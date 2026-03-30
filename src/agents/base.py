"""Genomic.go Platform - Base agent infrastructure.

This module defines the GenomicAgent abstract base class and AgentStatus enum,
providing lifecycle management, logging, and optional Redis-backed memory for
all genomic AI agents.
"""

import asyncio
import logging
import uuid
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Optional


class AgentStatus(Enum):
    """Lifecycle status for a GenomicAgent."""

    IDLE = "idle"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


class GenomicAgent(ABC):
    """Abstract base class for all Genomic.go Platform agents.

    Provides standardised lifecycle management (init → start → execute → stop),
    structured logging, status tracking, and optional Redis-backed memory.

    Subclasses must implement:
        - ``initialize()`` – set up resources before execution.
        - ``start()`` – begin active processing.
        - ``stop()`` – release resources after execution.
        - ``health_check()`` – return ``True`` if the agent is healthy.
        - ``_execute()`` – core domain logic.

    Args:
        name: Human-readable agent name.
        agent_id: Optional unique identifier; auto-generated when not provided.
        redis_url: Optional Redis connection URL for persistent memory.
    """

    def __init__(
        self,
        name: str,
        agent_id: Optional[str] = None,
        redis_url: Optional[str] = None,
    ) -> None:
        self._name: str = name
        self._agent_id: str = agent_id or str(uuid.uuid4())
        self._status: AgentStatus = AgentStatus.IDLE
        self._metadata: Dict[str, Any] = {}
        self._redis_url: Optional[str] = redis_url
        self._memory: Optional[Any] = None
        self.logger: logging.Logger = logging.getLogger(f"genomic.agent.{name}")

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def agent_id(self) -> str:
        """Unique identifier for this agent instance."""
        return self._agent_id

    @property
    def name(self) -> str:
        """Human-readable agent name."""
        return self._name

    @property
    def status(self) -> AgentStatus:
        """Current lifecycle status."""
        return self._status

    @property
    def metadata(self) -> Dict[str, Any]:
        """Arbitrary metadata dictionary for this agent."""
        return self._metadata

    # ------------------------------------------------------------------
    # Abstract lifecycle methods
    # ------------------------------------------------------------------

    @abstractmethod
    async def initialize(self) -> None:
        """Initialise agent resources (connections, models, caches)."""

    @abstractmethod
    async def start(self) -> None:
        """Begin active processing; called after ``initialize``."""

    @abstractmethod
    async def stop(self) -> None:
        """Release resources; called after ``_execute`` completes or on error."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Return ``True`` if the agent is operating correctly."""

    @abstractmethod
    async def _execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Core domain logic to be implemented by each concrete agent.

        Args:
            input_data: Arbitrary input payload for the agent.

        Returns:
            Arbitrary output dictionary produced by the agent.
        """

    # ------------------------------------------------------------------
    # Public run interface
    # ------------------------------------------------------------------

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the full agent lifecycle for the given input.

        Calls ``initialize`` → ``start`` → ``_execute`` → ``stop`` in
        sequence, updating *status* throughout.  Any exception sets the
        status to ``ERROR`` and re-raises after calling ``stop``.

        Args:
            input_data: Payload forwarded to ``_execute``.

        Returns:
            The result dict produced by ``_execute``.
        """
        self.logger.info("Agent %s starting run (id=%s)", self._name, self._agent_id)
        try:
            await self.initialize()
            await self.start()
            self._status = AgentStatus.RUNNING
            result = await self._execute(input_data)
            return result
        except Exception as exc:
            self._status = AgentStatus.ERROR
            self.logger.error(
                "Agent %s encountered an error: %s", self._name, exc, exc_info=True
            )
            raise
        finally:
            try:
                await self.stop()
            except Exception as stop_exc:
                self.logger.warning(
                    "Agent %s stop raised an error: %s", self._name, stop_exc
                )
            if self._status == AgentStatus.RUNNING:
                self._status = AgentStatus.STOPPED

    # ------------------------------------------------------------------
    # Memory helpers
    # ------------------------------------------------------------------

    def get_memory(self) -> Optional[Any]:
        """Return the Redis-backed memory instance, or ``None``.

        Memory is initialised lazily on first call when a *redis_url* was
        supplied to the constructor.

        Returns:
            An :class:`~src.agents.memory.AgentMemory` instance, or ``None``
            if no Redis URL was configured.
        """
        if self._memory is not None:
            return self._memory
        if self._redis_url:
            from src.agents.memory import AgentMemory  # lazy import

            self._memory = AgentMemory(redis_url=self._redis_url)
        return self._memory
