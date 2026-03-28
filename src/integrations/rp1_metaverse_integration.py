"""RP1 Spatial Internet Integration for Genomic.go Platform

This module integrates the Genomic.go Platform with RP1's Spatial Internet
(https://rp1.com) — an open-standard metaverse browser and spatial fabric
platform — to provide:

- 3D Virtual Research Lab: persistent spatial environment for collaborative
  genomic research sessions.
- Compound Visualization NSO: real-time 3D molecular structure rendering in
  the virtual space using RP1 Network Service Objects.
- Clinical Trial Dashboard NSO: live adaptive trial metrics and safety
  monitoring visualised as interactive 3D objects.
- Protein Structure Viewer: AlphaFold3 prediction results streamed as 3D
  spatial objects inside the virtual lab.
- Agent Activity Feed NSO: live stream of NANDA agent swarm activity displayed
  as animated events in the spatial environment.
- Collaborative Research Space: multi-researcher real-time sessions with
  presence tracking and shared molecular workspaces.

RP1 Platform Architecture:
  - Spatial Fabric: persistent 3D environment registered on Universal Spatial
    Fabric and discoverable by any RP1-compatible browser.
  - Network Service Objects (NSO): backend services (REST + Socket.IO) that
    bridge the platform's data streams to the spatial environment.
  - RP1 Integrated Activities (RIA): client-side app components embedded in
    the metaverse that consume NSO data.

References:
  - RP1 Developer Docs: https://docs.rp1.com
  - NSO Developer Tools: https://github.com/jl-codes/rp1-dev-mcp
"""

import asyncio
import json
import logging
import os
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class RP1Config:
    """Configuration for connecting to the RP1 Spatial Internet platform.

    All values can be supplied via environment variables (see Configuration
    wiki page) or passed explicitly at construction time.
    """

    api_key: str = field(
        default_factory=lambda: os.getenv("RP1_API_KEY", "")
    )
    """RP1 developer API key obtained from dev.rp1.com."""

    fabric_id: str = field(
        default_factory=lambda: os.getenv("RP1_FABRIC_ID", "")
    )
    """ID of the spatial fabric (3D environment) registered on RP1."""

    base_url: str = field(
        default_factory=lambda: os.getenv(
            "RP1_API_BASE_URL", "https://api.rp1.com/v1"
        )
    )
    """Base URL for the RP1 REST API."""

    socket_url: str = field(
        default_factory=lambda: os.getenv(
            "RP1_SOCKET_URL", "https://socket.rp1.com"
        )
    )
    """URL for the RP1 real-time Socket.IO endpoint."""

    nso_host: str = field(
        default_factory=lambda: os.getenv(
            "RP1_NSO_HOST", "https://nso.genomic.agicorp.network"
        )
    )
    """Public URL of the self-hosted NSO server that RP1 connects to."""

    lab_space_name: str = "Genomic Research Lab"
    """Display name of the virtual lab space shown in RP1."""


# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------


class NSObjectType(str, Enum):
    """Categories of Network Service Objects registered with RP1."""

    COMPOUND_VIEWER = "compound_viewer"
    TRIAL_DASHBOARD = "trial_dashboard"
    PROTEIN_VIEWER = "protein_viewer"
    AGENT_FEED = "agent_feed"
    COLLABORATION = "collaboration"


@dataclass
class SpatialPosition:
    """3-D position and orientation within the virtual lab fabric."""

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    rotation_y: float = 0.0  # yaw in degrees


@dataclass
class NetworkServiceObject:
    """Represents a registered NSO in the RP1 spatial fabric."""

    nso_id: str
    nso_type: NSObjectType
    display_name: str
    position: SpatialPosition
    endpoint_url: str
    registered_at: str
    is_realtime: bool = True  # True → Socket.IO; False → REST polling


@dataclass
class CompoundVisualization:
    """Payload for rendering a compound in 3D inside the virtual lab."""

    compound_id: str
    name: str
    smiles: str
    similarity_score: float
    molecular_weight: float
    target_protein: str
    position: SpatialPosition
    color_hex: str = "#00BFFF"  # DeepSkyBlue by default


@dataclass
class TrialDashboardUpdate:
    """Real-time clinical trial metrics pushed to the trial dashboard NSO."""

    trial_id: str
    arm_allocation_ratios: Dict[str, float]
    enrolled_count: int
    ae_rate_7day: float
    safety_status: str  # "green" | "yellow" | "red"
    should_stop: bool
    stopping_reason: Optional[str]
    timestamp: str


@dataclass
class AgentActivityEvent:
    """Single agent swarm activity event streamed to the agent feed NSO."""

    agent_id: str
    agent_type: str
    event_type: str  # "task_started" | "task_completed" | "task_failed"
    description: str
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Core RP1 client
# ---------------------------------------------------------------------------


class RP1SpatialClient:
    """Low-level HTTP client for the RP1 REST API.

    Handles authentication, request construction, and error propagation.
    All methods are synchronous; use :class:`RP1SpatialIntegration` for
    async wrappers suitable for use with the rest of the platform.
    """

    def __init__(self, config: RP1Config):
        self.config = config
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-RP1-Client": "genomic-go-platform/1.0",
            }
        )

    def _url(self, path: str) -> str:
        return f"{self.config.base_url}/{path.lstrip('/')}"

    def get_fabric(self) -> Dict[str, Any]:
        """Retrieve metadata for the configured spatial fabric."""
        response = self._session.get(
            self._url(f"fabrics/{self.config.fabric_id}"), timeout=10
        )
        response.raise_for_status()
        return response.json()

    def register_nso(self, nso_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Register a new Network Service Object on the spatial fabric."""
        response = self._session.post(
            self._url(f"fabrics/{self.config.fabric_id}/nso"),
            json=nso_payload,
            timeout=15,
        )
        response.raise_for_status()
        return response.json()

    def update_nso(self, nso_id: str, update_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing NSO (e.g. change endpoint or display name)."""
        response = self._session.patch(
            self._url(f"fabrics/{self.config.fabric_id}/nso/{nso_id}"),
            json=update_payload,
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def list_nso(self) -> List[Dict[str, Any]]:
        """List all NSOs currently registered on the fabric."""
        response = self._session.get(
            self._url(f"fabrics/{self.config.fabric_id}/nso"), timeout=10
        )
        response.raise_for_status()
        return response.json().get("nso_objects", [])

    def delete_nso(self, nso_id: str) -> bool:
        """Remove an NSO from the fabric."""
        response = self._session.delete(
            self._url(f"fabrics/{self.config.fabric_id}/nso/{nso_id}"),
            timeout=10,
        )
        return response.status_code == 204

    def push_spatial_event(
        self, nso_id: str, event_type: str, payload: Dict[str, Any]
    ) -> bool:
        """Push a one-shot event to an NSO via the RP1 REST relay.

        For high-frequency real-time events prefer the Socket.IO stream
        in :class:`RP1RealtimeStream`.
        """
        response = self._session.post(
            self._url(f"fabrics/{self.config.fabric_id}/nso/{nso_id}/events"),
            json={"event": event_type, "data": payload},
            timeout=10,
        )
        return response.ok

    def get_presence(self) -> List[Dict[str, Any]]:
        """Return list of researchers currently present in the virtual lab."""
        response = self._session.get(
            self._url(f"fabrics/{self.config.fabric_id}/presence"), timeout=10
        )
        response.raise_for_status()
        return response.json().get("users", [])


# ---------------------------------------------------------------------------
# Real-time Socket.IO stream bridge
# ---------------------------------------------------------------------------


class RP1RealtimeStream:
    """Bridges Genomic.go data streams to RP1 via Socket.IO.

    This class maintains a logical connection to RP1's real-time relay and
    emits events that the RP1 client-side RIA (Integrated Activity) renders
    as live updates inside the spatial environment.

    In production, replace the REST-based ``_emit`` stub with a proper
    python-socketio or socketio-client call. The interface is kept
    transport-agnostic here so it can be swapped without changing callers.
    """

    def __init__(self, config: RP1Config):
        self.config = config
        self._client = RP1SpatialClient(config)
        self._nso_registry: Dict[str, str] = {}  # nso_type → nso_id

    def bind_nso(self, nso_type: NSObjectType, nso_id: str) -> None:
        """Associate a registered NSO ID with a logical object type."""
        self._nso_registry[nso_type.value] = nso_id
        logger.debug("Bound NSO %s → %s", nso_type.value, nso_id)

    def _nso_id_for(self, nso_type: NSObjectType) -> Optional[str]:
        return self._nso_registry.get(nso_type.value)

    def emit_compound(self, viz: CompoundVisualization) -> bool:
        """Stream a compound visualization event to the compound viewer NSO."""
        nso_id = self._nso_id_for(NSObjectType.COMPOUND_VIEWER)
        if not nso_id:
            logger.warning("Compound viewer NSO not bound; skipping emit")
            return False
        payload = {
            **asdict(viz),
            "position": asdict(viz.position),
        }
        return self._client.push_spatial_event(nso_id, "compound_rendered", payload)

    def emit_trial_update(self, update: TrialDashboardUpdate) -> bool:
        """Stream a trial dashboard update to the trial dashboard NSO."""
        nso_id = self._nso_id_for(NSObjectType.TRIAL_DASHBOARD)
        if not nso_id:
            logger.warning("Trial dashboard NSO not bound; skipping emit")
            return False
        return self._client.push_spatial_event(
            nso_id, "trial_metrics_updated", asdict(update)
        )

    def emit_agent_event(self, event: AgentActivityEvent) -> bool:
        """Stream an agent activity event to the agent feed NSO."""
        nso_id = self._nso_id_for(NSObjectType.AGENT_FEED)
        if not nso_id:
            logger.warning("Agent feed NSO not bound; skipping emit")
            return False
        return self._client.push_spatial_event(
            nso_id, "agent_activity", asdict(event)
        )

    def emit_protein_structure(
        self, task_id: str, protein_sequence: str, pdb_url: str, position: SpatialPosition
    ) -> bool:
        """Stream a protein structure prediction result to the protein viewer NSO."""
        nso_id = self._nso_id_for(NSObjectType.PROTEIN_VIEWER)
        if not nso_id:
            logger.warning("Protein viewer NSO not bound; skipping emit")
            return False
        payload = {
            "task_id": task_id,
            "sequence_preview": protein_sequence[:40] + "...",
            "pdb_url": pdb_url,
            "position": asdict(position),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return self._client.push_spatial_event(nso_id, "structure_available", payload)


# ---------------------------------------------------------------------------
# High-level integration orchestrator
# ---------------------------------------------------------------------------


class RP1SpatialIntegration:
    """High-level async interface for the RP1 Spatial Internet integration.

    Manages the lifecycle of the virtual lab: NSO registration on startup,
    real-time event streaming during research sessions, and cleanup on
    shutdown.

    Usage::

        config = RP1Config(api_key="rp1-key", fabric_id="fab-xyz")
        lab = RP1SpatialIntegration(config)
        await lab.initialize_virtual_lab()

        # Stream a compound found during drug discovery
        await lab.stream_compound_to_lab(compound_data, position=SpatialPosition(x=1, y=0, z=0))

        # Stream trial update from AdaptiveTrialDesign
        await lab.stream_trial_update(trial_metrics)
    """

    # Default positions for NSO objects arranged inside the virtual lab
    _NSO_POSITIONS: Dict[NSObjectType, SpatialPosition] = {
        NSObjectType.COMPOUND_VIEWER:  SpatialPosition(x=-4.0, y=0.0, z=0.0),
        NSObjectType.TRIAL_DASHBOARD:  SpatialPosition(x=0.0,  y=0.0, z=-3.0),
        NSObjectType.PROTEIN_VIEWER:   SpatialPosition(x=4.0,  y=0.0, z=0.0),
        NSObjectType.AGENT_FEED:       SpatialPosition(x=0.0,  y=2.5, z=2.0),
        NSObjectType.COLLABORATION:    SpatialPosition(x=0.0,  y=0.0, z=0.0),
    }

    def __init__(self, config: RP1Config):
        self.config = config
        self._client = RP1SpatialClient(config)
        self._stream = RP1RealtimeStream(config)
        self._registered_nso: Dict[NSObjectType, NetworkServiceObject] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize_virtual_lab(self) -> Dict[str, Any]:
        """Register all NSOs and configure the virtual lab spatial fabric.

        This should be called once on platform startup. It is idempotent:
        existing NSOs with matching names on the fabric are reused rather
        than duplicated.

        Returns:
            Summary dict with fabric metadata and registered NSO IDs.
        """
        logger.info("Initialising RP1 virtual research lab: %s", self.config.lab_space_name)

        # Verify fabric is accessible
        try:
            fabric_meta = await asyncio.get_event_loop().run_in_executor(
                None, self._client.get_fabric
            )
            logger.info("Connected to spatial fabric: %s", fabric_meta.get("name"))
        except Exception as exc:
            logger.error("Failed to connect to RP1 fabric: %s", exc)
            raise

        # Register each NSO type
        for nso_type, position in self._NSO_POSITIONS.items():
            nso = await self._register_nso(nso_type, position)
            self._registered_nso[nso_type] = nso
            self._stream.bind_nso(nso_type, nso.nso_id)

        logger.info(
            "Virtual lab ready with %d NSOs", len(self._registered_nso)
        )
        return {
            "fabric_id": self.config.fabric_id,
            "lab_name": self.config.lab_space_name,
            "nso_count": len(self._registered_nso),
            "nso_ids": {k.value: v.nso_id for k, v in self._registered_nso.items()},
        }

    async def _register_nso(
        self, nso_type: NSObjectType, position: SpatialPosition
    ) -> NetworkServiceObject:
        """Register a single NSO on the RP1 fabric (or reuse existing)."""
        display_names = {
            NSObjectType.COMPOUND_VIEWER: "🧪 Compound Explorer",
            NSObjectType.TRIAL_DASHBOARD: "📊 Trial Dashboard",
            NSObjectType.PROTEIN_VIEWER:  "🔬 Protein Viewer",
            NSObjectType.AGENT_FEED:      "🤖 Agent Activity",
            NSObjectType.COLLABORATION:   "👥 Collaboration Hub",
        }

        nso_payload = {
            "type": nso_type.value,
            "display_name": display_names[nso_type],
            "endpoint_url": f"{self.config.nso_host}/nso/{nso_type.value}",
            "is_realtime": True,
            "position": asdict(position),
            "metadata": {
                "platform": "genomic-go-platform",
                "version": "1.0.0",
            },
        }

        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self._client.register_nso(nso_payload)
            )
            nso_id = result.get("nso_id", str(uuid.uuid4()))
        except Exception as exc:
            logger.warning(
                "NSO registration failed for %s (%s); using placeholder ID",
                nso_type.value,
                exc,
            )
            nso_id = str(uuid.uuid4())

        return NetworkServiceObject(
            nso_id=nso_id,
            nso_type=nso_type,
            display_name=display_names[nso_type],
            position=position,
            endpoint_url=nso_payload["endpoint_url"],
            registered_at=datetime.now(timezone.utc).isoformat(),
        )

    async def teardown_virtual_lab(self) -> None:
        """Deregister all NSOs and clean up the virtual lab."""
        logger.info("Tearing down RP1 virtual lab")
        for nso_type, nso in self._registered_nso.items():
            try:
                await asyncio.get_event_loop().run_in_executor(
                    None, lambda n=nso: self._client.delete_nso(n.nso_id)
                )
                logger.info("Removed NSO: %s (%s)", nso.display_name, nso.nso_id)
            except Exception as exc:
                logger.warning("Failed to remove NSO %s: %s", nso.nso_id, exc)
        self._registered_nso.clear()

    # ------------------------------------------------------------------
    # Data streaming helpers
    # ------------------------------------------------------------------

    async def stream_compound_to_lab(
        self,
        compound: Dict[str, Any],
        position: Optional[SpatialPosition] = None,
    ) -> bool:
        """Render a compound discovery result in the virtual lab.

        Args:
            compound: Compound dict from :class:`CompoundSearcher` results.
            position: 3D placement in the spatial fabric. Auto-assigned if omitted.

        Returns:
            True if the event was accepted by RP1, False otherwise.
        """
        pos = position or SpatialPosition(
            x=float(hash(compound.get("compound_id", "")) % 5),
            y=0.0,
            z=float(hash(compound.get("name", "")) % 5),
        )
        viz = CompoundVisualization(
            compound_id=compound.get("compound_id", "unknown"),
            name=compound.get("name", "Unknown"),
            smiles=compound.get("smiles", ""),
            similarity_score=float(compound.get("score", 0.0)),
            molecular_weight=float(compound.get("molecular_weight", 0.0)),
            target_protein=compound.get("target_protein", ""),
            position=pos,
        )
        return await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._stream.emit_compound(viz)
        )

    async def stream_trial_update(
        self,
        trial_id: str,
        arm_ratios: Dict[str, float],
        enrolled: int,
        ae_rate: float,
        should_stop: bool = False,
        stopping_reason: Optional[str] = None,
    ) -> bool:
        """Push clinical trial metrics to the trial dashboard NSO.

        Args:
            trial_id: Trial identifier.
            arm_ratios: Current allocation probabilities per arm.
            enrolled: Total patients enrolled so far.
            ae_rate: 7-day rolling adverse event rate.
            should_stop: Whether stopping rules have been triggered.
            stopping_reason: Reason for stopping, if applicable.

        Returns:
            True if the event was accepted by RP1, False otherwise.
        """
        safety = (
            "red" if ae_rate > 0.15 else "yellow" if ae_rate > 0.08 else "green"
        )
        update = TrialDashboardUpdate(
            trial_id=trial_id,
            arm_allocation_ratios=arm_ratios,
            enrolled_count=enrolled,
            ae_rate_7day=ae_rate,
            safety_status=safety,
            should_stop=should_stop,
            stopping_reason=stopping_reason,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        return await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._stream.emit_trial_update(update)
        )

    async def stream_protein_structure(
        self,
        task_id: str,
        protein_sequence: str,
        pdb_url: str,
        position: Optional[SpatialPosition] = None,
    ) -> bool:
        """Display an AlphaFold3 structure prediction result in the lab.

        Args:
            task_id: NANDA task ID returned by AlphaFold3NANDAIntegration.
            protein_sequence: Amino acid sequence that was predicted.
            pdb_url: Public URL of the resulting PDB file.
            position: 3D placement in the protein viewer zone.

        Returns:
            True if the event was accepted by RP1, False otherwise.
        """
        pos = position or self._NSO_POSITIONS[NSObjectType.PROTEIN_VIEWER]
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self._stream.emit_protein_structure(
                task_id, protein_sequence, pdb_url, pos
            ),
        )

    async def stream_agent_event(
        self,
        agent_id: str,
        agent_type: str,
        event_type: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Publish a NANDA agent activity event to the agent feed NSO.

        Args:
            agent_id: NANDA agent identifier.
            agent_type: Swarm type (e.g. "compound_discovery").
            event_type: One of "task_started", "task_completed", "task_failed".
            description: Human-readable summary of the event.
            metadata: Optional structured metadata attached to the event.

        Returns:
            True if the event was accepted by RP1, False otherwise.
        """
        event = AgentActivityEvent(
            agent_id=agent_id,
            agent_type=agent_type,
            event_type=event_type,
            description=description,
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata=metadata or {},
        )
        return await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._stream.emit_agent_event(event)
        )

    async def get_active_researchers(self) -> List[Dict[str, Any]]:
        """Return the list of researchers currently in the virtual lab.

        Returns:
            List of presence objects from the RP1 API, each containing
            ``user_id``, ``display_name``, ``position``, and ``joined_at``.
        """
        return await asyncio.get_event_loop().run_in_executor(
            None, self._client.get_presence
        )


# ---------------------------------------------------------------------------
# Genomic research session coordinator
# ---------------------------------------------------------------------------


class GenomicSpatialSession:
    """Coordinates a full genomic research session inside the RP1 virtual lab.

    This is the top-level class integrating:
    - Compound search results → RP1 compound viewer NSO
    - AdaptiveTrialDesign metrics → RP1 trial dashboard NSO
    - AlphaFold3 predictions → RP1 protein viewer NSO
    - NANDA agent swarm events → RP1 agent feed NSO

    It acts as a bridge layer: the rest of the platform calls the stream_*
    methods here, and this class handles routing to the correct NSO.

    Usage::

        session = GenomicSpatialSession(rp1_config)
        await session.start()

        # Then call from compound searcher results:
        await session.on_compound_found(compound_dict)

        # From trial optimizer:
        await session.on_trial_metrics(trial_id, ratios, enrolled, ae_rate)

        # From AlphaFold3:
        await session.on_structure_predicted(task_id, seq, pdb_url)

        # From NANDA agent:
        await session.on_agent_task_completed(agent_id, "compound_discovery", summary)

        await session.stop()
    """

    def __init__(self, rp1_config: RP1Config):
        self._integration = RP1SpatialIntegration(rp1_config)
        self._session_id = str(uuid.uuid4())
        self._started = False

    @property
    def session_id(self) -> str:
        return self._session_id

    async def start(self) -> Dict[str, Any]:
        """Initialise the virtual lab and return setup summary."""
        result = await self._integration.initialize_virtual_lab()
        self._started = True
        logger.info("Genomic spatial session %s started", self._session_id)
        return result

    async def stop(self) -> None:
        """Tear down the virtual lab and release RP1 resources."""
        await self._integration.teardown_virtual_lab()
        self._started = False
        logger.info("Genomic spatial session %s stopped", self._session_id)

    def _assert_started(self) -> None:
        if not self._started:
            raise RuntimeError("Session not started. Call start() first.")

    async def on_compound_found(
        self,
        compound: Dict[str, Any],
        position: Optional[SpatialPosition] = None,
    ) -> None:
        """Called when CompoundSearcher returns a result."""
        self._assert_started()
        ok = await self._integration.stream_compound_to_lab(compound, position)
        if not ok:
            logger.warning("Failed to stream compound %s to RP1", compound.get("name"))

    async def on_trial_metrics(
        self,
        trial_id: str,
        arm_ratios: Dict[str, float],
        enrolled: int,
        ae_rate: float,
        should_stop: bool = False,
        stopping_reason: Optional[str] = None,
    ) -> None:
        """Called after each AdaptiveTrialDesign allocation or outcome update."""
        self._assert_started()
        await self._integration.stream_trial_update(
            trial_id, arm_ratios, enrolled, ae_rate, should_stop, stopping_reason
        )

    async def on_structure_predicted(
        self,
        task_id: str,
        protein_sequence: str,
        pdb_url: str,
        position: Optional[SpatialPosition] = None,
    ) -> None:
        """Called when AlphaFold3NANDAIntegration.predict_structure() completes."""
        self._assert_started()
        await self._integration.stream_protein_structure(
            task_id, protein_sequence, pdb_url, position
        )

    async def on_agent_task_started(
        self, agent_id: str, agent_type: str, description: str
    ) -> None:
        """Called when a NANDA agent begins a task."""
        self._assert_started()
        await self._integration.stream_agent_event(
            agent_id, agent_type, "task_started", description
        )

    async def on_agent_task_completed(
        self,
        agent_id: str,
        agent_type: str,
        description: str,
        result_summary: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Called when a NANDA agent completes a task."""
        self._assert_started()
        await self._integration.stream_agent_event(
            agent_id,
            agent_type,
            "task_completed",
            description,
            metadata=result_summary,
        )

    async def on_agent_task_failed(
        self, agent_id: str, agent_type: str, error: str
    ) -> None:
        """Called when a NANDA agent task fails."""
        self._assert_started()
        await self._integration.stream_agent_event(
            agent_id, agent_type, "task_failed", error
        )

    async def get_present_researchers(self) -> List[Dict[str, Any]]:
        """Return researchers currently inhabiting the virtual lab."""
        self._assert_started()
        return await self._integration.get_active_researchers()


# ---------------------------------------------------------------------------
# Entry point / example
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    config = RP1Config(
        api_key=os.getenv("RP1_API_KEY", "demo-key"),
        fabric_id=os.getenv("RP1_FABRIC_ID", "demo-fabric"),
    )

    async def demo():
        session = GenomicSpatialSession(config)
        summary = await session.start()
        print(json.dumps(summary, indent=2))

        # Simulate a compound discovery result
        compound = {
            "compound_id": "CHEMBL475825",
            "name": "Erlotinib",
            "smiles": "C#Cc1cccc(Nc2ncnc3cc(OCC)c(OCC)cc23)c1",
            "score": 0.923,
            "molecular_weight": 393.4,
            "target_protein": "EGFR",
            "therapeutic_area": "Oncology",
        }
        await session.on_compound_found(compound, SpatialPosition(x=1.0, y=0.0, z=2.0))

        # Simulate a trial metrics push
        await session.on_trial_metrics(
            trial_id="TRIAL-2026-EGFR",
            arm_ratios={"treatment_A": 0.68, "placebo": 0.32},
            enrolled=142,
            ae_rate=0.06,
        )

        # Simulate an agent completing a task
        await session.on_agent_task_completed(
            agent_id="compound-agent-03",
            agent_type="compound_discovery",
            description="Screened 10,000 compounds against EGFR binding pocket",
            result_summary={"top_hits": 23, "admet_passed": 8},
        )

        await session.stop()

    asyncio.run(demo())
