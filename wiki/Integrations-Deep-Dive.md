# Integrations Deep Dive

A granular technical comparison and in-depth discussion of every external integration in the Genomic.go Platform: **NANDA SDK**, **AlphaFold3**, **Robotics**, and **RP1 Spatial Internet**.

---

## Integration Landscape

```
                        Genomic.go Platform
                              │
          ┌───────────────────┼───────────────────────┐
          │                   │                       │
    ┌─────▼──────┐    ┌───────▼───────┐    ┌─────────▼─────────┐
    │ NANDA SDK  │    │  AlphaFold3   │    │  RP1 Spatial      │
    │ Agent Swarm│    │  NANDA Proto  │    │  Internet         │
    │ (Core AI)  │    │  (Structure)  │    │  (Visualisation)  │
    └─────┬──────┘    └───────┬───────┘    └─────────┬─────────┘
          │                   │                       │
    ┌─────▼──────┐    ┌───────▼───────┐    ┌─────────▼─────────┐
    │ Robotics   │    │   Qdrant      │    │  Kafka Streams    │
    │ Lab Auto   │    │   Vector DB   │    │  (Safety Events)  │
    │ (Physical) │    │   (150M cpds) │    │                   │
    └────────────┘    └───────────────┘    └───────────────────┘
```

---

## 1. NANDA SDK Integration

**File:** `src/integrations/nanda_agent_integration.py`  
**Purpose:** Orchestrate 35+ specialised AI agent swarms for parallel research

### How It Works

NANDA (Node-based Agent Network for Distributed Analysis) is an **Internet of Agents** protocol that allows heterogeneous AI agents to register, discover, and communicate with each other through a shared registry.

#### Agent Registration Flow

```
1. nanda-sdk CLI process is spawned as a subprocess
   (asyncio.create_subprocess_exec)

2. Process connects to NANDA registry at:
   https://chat.nanda-registry.com

3. Agent registers with:
   - Anthropic API key (for Claude reasoning)
   - Domain (genomic.agicorp.network)
   - Agent ID (unique 6-digit integer)

4. Agent exposes HTTP endpoints:
   - GET  /health          → liveness probe
   - POST /api/tasks       → task ingestion
   - POST /api/shutdown    → graceful stop
```

#### Task Dispatch Pattern

```python
# Partition workflow steps across agent pool
steps_per_agent = len(steps) // len(agent_ids)

# Gather all tasks in parallel
results = await asyncio.gather(*tasks, return_exceptions=True)

# Resilient: exceptions do not propagate; they are logged and skipped
successful_results = [r for r in results if not isinstance(r, Exception)]
```

#### Swarm Composition (production)

| Swarm | Count | Timeout | Primary task |
|-------|-------|---------|-------------|
| `literature_analysis` | 3 | 300s | PubMed/bioRxiv search, summarisation |
| `compound_discovery` | 5 | 300s | Qdrant semantic search, ADMET scoring |
| `genomics_analysis` | 4 | 300s | GWAS, multi-omic correlation |
| `protocol_automation` | 3 | 300s | Experimental protocol generation |
| `structure_prediction` | 2 | 300s | AlphaFold3 task coordination |

#### Deployment Stagger

Agents are deployed with a 2-second stagger (`await asyncio.sleep(2)`) to avoid overwhelming the NANDA registry with simultaneous registrations.

#### Failure Model

- `send_task_to_agent()` raises on non-200 HTTP responses
- `distribute_workflow()` catches per-agent exceptions with `return_exceptions=True`
- No automatic retry at the workflow level — callers must implement retries if needed
- Health check (`/health`) returns HTTP 200 for healthy, non-200 for unhealthy, connection error for unreachable

### Integration Points with Other Modules

| Downstream | How NANDA uses it |
|-----------|-------------------|
| `CompoundSearcher` | Compound discovery agents call the searcher internally |
| `AlphaFold3NANDAIntegration` | Structure prediction agents delegate to the AlphaFold3 coordinator |
| `AdaptiveTrialDesign` | Protocol automation agents generate and submit trial designs |
| `RP1SpatialIntegration` | Agent swarm events are streamed to RP1 agent feed NSO |

### Key Design Decisions

1. **Subprocess-based deployment**: Each agent runs as a separate OS process (via NANDA SDK CLI). This provides process isolation and allows each agent to crash independently.
2. **HTTP-over-subprocess communication**: Agents expose an HTTP server; the orchestrator talks to them via `requests.post`. This is intentional — the NANDA protocol is transport-agnostic.
3. **Stateless tasks**: Each task sent to an agent is self-contained (no shared mutable state). Results are returned synchronously in the response body.
4. **Random agent IDs**: When NANDA SDK doesn't provide one, a random 6-digit integer is used. This is deterministic enough for the 300s lifetime of an agent but not globally unique — production should use UUIDs.

---

## 2. AlphaFold3 + NANDA Protocol Integration

**File:** `src/integrations/alphafold3_nanda_integration.py`  
**Purpose:** Distributed protein structure prediction with high availability

### How It Works

This integration uses a **NANDA-flavoured coordinator** (distinct from the agent swarm NANDA above) that manages a pool of GPU-capable inference nodes.

#### Node Registration and Selection

```python
# Register a GPU node
coordinator.register_node(
    node_id="sf-agent-01",
    capabilities=["alphafold3"],
    endpoint="https://node1.agicorp.network"
)

# Node selection: sort by ascending load
eligible.sort(key=lambda nid: self.nodes[nid]["load"])
selected = eligible[:redundancy_factor]  # default 2
```

#### Task Lifecycle

```
submit_task(sequence)
  → Create AlphaFoldTask(status=PENDING)
  → _select_nodes("alphafold3", redundancy_factor=2)
  → _dispatch_to_nodes(task, [node-1, node-2])
      → node["load"] += 1 for each dispatched node
  → Return task_id

(Background) monitor_health() every 10s
  → Check last_heartbeat for each node
  → If > 30s since last heartbeat:
      node["status"] = "offline"
      _handle_node_failure(node_id)
        → Find in-flight tasks on failed node
        → _dispatch_to_nodes(task, new_healthy_nodes)
```

#### Redundancy Model

Every task is dispatched to `redundancy_factor` nodes simultaneously. The **first successful result** is used; remaining in-flight tasks on other nodes are cancelled. This trades compute efficiency for reliability — suitable for long-running predictions (minutes) where a node failure would otherwise waste the entire computation.

#### State Machine (AgentTaskStatus)

```
PENDING → PROCESSING → COMPLETED
                    ↘ FAILED
           RETRYING ← (node failure)
```

### AlphaFold3 vs. NANDA Agent Swarm: Key Differences

| Dimension | AlphaFold3 Coordinator | NANDA Agent Swarm |
|-----------|----------------------|-------------------|
| Node discovery | Manual `register_node()` calls | Automatic via NANDA registry |
| Task assignment | Explicit load-based selection | Registry-mediated |
| Redundancy | Simultaneous multi-node dispatch | Single agent per task |
| Communication | HTTP to inference endpoint | HTTP to agent subprocess |
| Health monitoring | Background asyncio loop, 10s interval | On-demand health check |
| Failure handling | Automatic failover | Logged, not retried |

### Current Limitations

- `_dispatch_to_nodes` increments load counter but does not decrement on completion — load grows monotonically until process restart. Production should track completions and decrement.
- `monitor_health` runs as an infinite loop; callers must `asyncio.create_task()` it explicitly and cancel it on shutdown.
- `predict_structure` returns `{"task_id": ..., "status": "submitted"}` — there is no polling mechanism implemented. Production should add `get_task_result(task_id)` with polling or a callback webhook.

---

## 3. Robotics and Lab Automation Integration

**File:** `src/integrations/robotics_nanda_integration.py`  
**Purpose:** Bridge AI-driven decisions to physical laboratory equipment

### Implemented Components

#### `RoboticsAutomationManager`

Controls automated lab instruments via the NANDA hardware protocol.

```python
manager = RoboticsAutomationManager({"endpoint": "http://lab-robot-1.local"})
result = await manager.execute_protocol(
    "ADJUST_SAMPLE_TREATMENT",
    {"sample_id": "SAM-99", "adjustment": "increase_dilution"}
)
```

**Current behaviour:** Simulates network latency (0.1s sleep) and returns a mock success response. The `# TODO` comment marks the integration point for a real NANDA hardware endpoint call.

**Planned protocols:**

| Protocol | Hardware | Trigger |
|----------|---------|---------|
| `ADJUST_SAMPLE_TREATMENT` | Liquid handler (Hamilton/Tecan) | High stress wearable alert |
| `INITIATE_SEQUENCING` | Illumina sequencer | Genomic variant call |
| `COMPOUND_DISPENSE` | Acoustic dispenser (ECHO) | Compound hit confirmed |
| `PLATE_READER_SCAN` | Biotek Neo2 | Endpoint assay trigger |
| `CULTURE_PASSAGE` | Automated cell culture | Cell viability drop |

#### `WearableDataStreamer`

Ingests real-time biometric data from clinical trial participant wearables.

```python
streamer = WearableDataStreamer(trial_id="TRIAL-2026-X", max_buffer_size=1000)
entry = await streamer.ingest_real_time_data(
    device_id="WATCH-123",
    data={"heart_rate": 110, "stress_level": "high"}
)
```

- Buffers up to `max_buffer_size` entries in memory (FIFO eviction)
- The `# TODO` marks the Kafka integration point: `kafka_producer.send("wearable-metrics", entry)`
- Triggering robotics from wearable events is demonstrated in the `__main__` example

### Integration Pattern: Wearable → Robotics Loop

```
WearableDataStreamer.ingest_real_time_data()
  → Kafka "wearable-metrics" topic (TODO)
  → SafetyMonitoringSystem consumes stream
  → If AE rate threshold crossed:
      → AdaptiveTrialDesign.check_stopping_rules()
      → If not stopping: adjust treatment
      → RoboticsAutomationManager.execute_protocol("ADJUST_SAMPLE_TREATMENT")
```

### Supported Lab Instrument Categories

| Category | Examples | Interface |
|----------|---------|-----------|
| Liquid handlers | Hamilton STAR, Tecan Fluent | NANDA hardware endpoint |
| High-throughput screening | Beckman Biomek, PerkinElmer JANUS | NANDA hardware endpoint |
| Sequencers | Illumina NovaSeq, PacBio Revio | FASTQ streaming API |
| Plate readers | Biotek Synergy, Molecular Devices SpectraMax | REST result callback |
| Cell imaging | Operetta CLS, ImageXpress | Image stream → ML model |
| Wearables | Apple Watch, Fitbit, ActiGraph | WebSocket / BLE bridge |

---

## 4. RP1 Spatial Internet Integration

**File:** `src/integrations/rp1_metaverse_integration.py`  
**Purpose:** Real-time 3D visualisation of research workflows in a collaborative virtual lab

See [RP1 Metaverse Integration](RP1-Metaverse-Integration.md) for the full guide.

### How It Fits with the Other Integrations

| Source | RP1 NSO target | What the researcher sees |
|--------|----------------|--------------------------|
| `NANDAAgentIntegration` | Agent Activity Feed | Scrolling agent task log with swarm icons |
| `AlphaFold3NANDAIntegration` | Protein Viewer | Rotating 3D ribbon diagram in the lab |
| `CompoundSearcher` | Compound Explorer | 3D molecular cards flying in |
| `AdaptiveTrialDesign` + `SafetyMonitoringSystem` | Trial Dashboard | Live allocation bars + AE rate gauge |
| `WearableDataStreamer` | Trial Dashboard | Participant count ticking up |

### RP1 Communication Stack

```
GenomicSpatialSession
  └── RP1SpatialIntegration
        ├── RP1SpatialClient   (REST: NSO CRUD, presence, event relay)
        └── RP1RealtimeStream  (Socket.IO: high-frequency event emission)
              └── NSO bindings (nso_type → nso_id map)
```

---

## Cross-Integration Comparison

| Dimension | NANDA Agent | AlphaFold3 | Robotics | RP1 |
|-----------|------------|-----------|---------|-----|
| **Direction** | Bidirectional | Outbound | Bidirectional | Outbound (events) + Inbound (NSO webhooks) |
| **Protocol** | HTTP REST | HTTP REST | HTTP REST | REST + Socket.IO |
| **Async model** | `asyncio.gather` | `asyncio + background loop` | `await asyncio.sleep` stub | `run_in_executor` |
| **Auth** | Anthropic API key | AlphaFold3 API key | NANDA hardware key | RP1 Bearer token |
| **Error handling** | `return_exceptions=True` | Status enum + failover | Try/except log | Warning + False return |
| **Real-time** | No (request/response) | No (submit/poll) | No (command/response) | Yes (Socket.IO) |
| **Redundancy** | No | 2x node dispatch | No | NSO registration retry |
| **State** | In-memory agent registry | In-memory task registry | Protocol list | NSO registry |
| **Scale** | 35+ swarms, ~75 agents | 2–N GPU nodes | N instruments | 5 NSOs |

---

## Shared Patterns Across All Integrations

### 1. Async-First

All integrations are designed for `asyncio`. I/O-bound calls either:
- Use `await asyncio.gather(...)` for parallelism
- Use `await asyncio.get_event_loop().run_in_executor(None, sync_fn)` to avoid blocking the event loop for synchronous libraries (e.g. `requests`)

### 2. Structured Logging

Every integration uses a module-level logger:
```python
logger = logging.getLogger(__name__)
```

Log levels are consistent:
- `INFO` — normal operation milestones
- `WARNING` — degraded operation (fallback used, NSO not bound, etc.)
- `ERROR` — failures that may require intervention

### 3. Dataclass Configuration

Configuration is expressed as typed `@dataclass` objects rather than raw dicts or environment lookups scattered through code. This makes testing easier (pass a config object with test values) and provides IDE autocompletion.

### 4. Graceful Degradation

Each integration is designed so that **its failure does not crash the research pipeline**:

| Integration | Failure behaviour |
|-------------|------------------|
| NANDA agent | Exception logged; other agents continue via `return_exceptions=True` |
| AlphaFold3 node | Tasks reassigned to surviving nodes |
| Robotics | Protocol failure logged; trial continues |
| RP1 stream | `emit_*` returns `False`; pipeline continues without visualisation |

---

## Integration Roadmap

| Integration | Current status | Planned enhancements |
|-------------|---------------|---------------------|
| NANDA Agent | ✅ Production-ready | Retry on task failure, UUID agent IDs |
| AlphaFold3 | ✅ Core flow ready | `get_task_result()` polling, load decrement on completion |
| Robotics | 🚧 Stub + framework | Real NANDA hardware endpoint calls, full instrument library |
| RP1 Spatial | ✅ Full implementation | python-socketio direct connection, RIA client-side components |

---

_Next: [RP1 Metaverse Integration](RP1-Metaverse-Integration.md) | [Modules Reference](Modules.md) | [Architecture](Architecture.md)_
