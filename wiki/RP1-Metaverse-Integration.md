# RP1 Spatial Internet Integration

This page provides a comprehensive guide to the Genomic.go Platform's integration with **RP1** (https://rp1.com) — the world's first open-standard Spatial Internet browser and metaverse platform.

---

## What is RP1?

RP1 is a **Spatial Internet platform** that provides:

| Concept | Description |
|---------|-------------|
| **Spatial Fabric** | Persistent 3D environment registered on the Universal Spatial Fabric — discoverable by any RP1-compatible browser across VR, AR, mobile, and desktop |
| **Network Service Object (NSO)** | A backend service (REST or Socket.IO) that exposes real-time or stateless data to objects rendered inside the spatial fabric |
| **RP1 Integrated Activity (RIA)** | Client-side app component embedded in the metaverse that consumes NSO data and renders interactive content |
| **Universal Spatial Fabric** | Global coordinate system that connects all self-hosted spatial servers into a single navigable metaverse |
| **Proximity model** | Users interact with NSOs and other users based on physical proximity inside the 3D space |

Developer documentation: https://docs.rp1.com  
Developer tools: https://github.com/jl-codes/rp1-dev-mcp

---

## Why Integrate Genomic.go with RP1?

The Genomic.go Platform processes massive parallel research workloads across 35+ agent swarms. RP1 integration transforms this invisible computation into a **living, collaborative research environment** that scientists can walk through:

| Without RP1 | With RP1 |
|-------------|----------|
| API responses in JSON | 3D molecular structures floating in a virtual lab |
| Log lines from agent swarms | Animated activity feed visible to all researchers in the space |
| Table of trial allocation ratios | Animated bar chart mounted on the virtual wall, updating live |
| PDB file URL in a task result | Protein ribbon diagram rotating in mid-air |
| Multiple researchers querying the same API | Shared virtual lab with spatial awareness of collaborators |

---

## Architecture

```
Genomic.go Platform                         RP1 Spatial Internet
─────────────────────────────────────────   ──────────────────────────────────────
                                            
  CompoundSearcher                          ┌─ Compound Explorer NSO ─────────────┐
    .search("EGFR inhibitor")  ──REST──→   │  3D molecular cards, sortable        │
                                            │  by score, colored by MW range       │
  AdaptiveTrialDesign                       └─────────────────────────────────────┘
    .allocate_patient()  ───REST/Socket──→  ┌─ Trial Dashboard NSO ───────────────┐
    .update_outcome()                       │  Live allocation ratio bars          │
    SafetyMonitoringSystem                  │  AE rate gauge (green/yellow/red)    │
                                            └─────────────────────────────────────┘
  AlphaFold3NANDAIntegration                ┌─ Protein Viewer NSO ────────────────┐
    .predict_structure()  ─────REST──────→  │  Rotating 3D ribbon diagram          │
                                            │  Confidence coloring, residue labels │
                                            └─────────────────────────────────────┘
  GenomicResearchAgentSwarm                 ┌─ Agent Activity Feed NSO ───────────┐
    NANDA agent events  ──────Socket──────→ │  Scrolling event log with icons      │
                                            │  Per-agent task progress             │
                                            └─────────────────────────────────────┘
  Multiple researchers                      ┌─ Collaboration Hub NSO ─────────────┐
    shared session  ──────────Socket──────→ │  Presence tracking, spatial audio    │
                                            │  Shared molecular workspace          │
                                            └─────────────────────────────────────┘
```

### Communication Protocols

| Path | Protocol | When to use |
|------|----------|-------------|
| One-shot data push (compound found, structure ready) | REST POST | Low-frequency, triggered events |
| High-frequency updates (trial metrics, agent events) | Socket.IO | Continuous streams, <1s latency |
| Presence and fabric metadata | REST GET | Read-only queries |
| NSO registration and management | REST (CRUD) | Startup / teardown |

---

## Module Overview

**File:** `src/integrations/rp1_metaverse_integration.py`

### Class Hierarchy

```
RP1Config                     — Configuration (API key, fabric ID, URLs)
RP1SpatialClient              — Low-level HTTP client for RP1 REST API
RP1RealtimeStream             — Socket.IO event emitter (NSO bridge)
RP1SpatialIntegration         — Mid-level: NSO lifecycle + stream dispatch
GenomicSpatialSession         — High-level: research session coordinator
```

Supporting dataclasses:
- `NSObjectType` — Enum of NSO categories
- `SpatialPosition` — 3D coordinates (x, y, z, rotation_y)
- `NetworkServiceObject` — Registered NSO metadata
- `CompoundVisualization` — Compound rendering payload
- `TrialDashboardUpdate` — Trial metrics payload
- `AgentActivityEvent` — Agent swarm event payload

---

## Network Service Objects

Five NSOs are registered when the virtual lab is initialised. Each maps to a physical location inside the 3D environment.

### 1. Compound Explorer NSO

**Purpose:** Renders compound discovery results as interactive 3D molecular cards.

**Position:** Left wing of the lab (x = -4.0)

**Event types received:**
- `compound_rendered` — Pushed by `CompoundSearcher.search()` results

**Payload:**
```json
{
  "compound_id": "CHEMBL475825",
  "name": "Erlotinib",
  "smiles": "C#Cc1cccc(Nc2ncnc3cc(OCC)c(OCC)cc23)c1",
  "similarity_score": 0.923,
  "molecular_weight": 393.4,
  "target_protein": "EGFR",
  "position": { "x": 1.0, "y": 0.0, "z": 2.0, "rotation_y": 0 },
  "color_hex": "#00BFFF"
}
```

**RIA behaviour:** New compounds fly in from the top of the compound wing and arrange themselves in a grid sorted by `similarity_score`. Clicking a compound card opens its SMILES structure, ADMET predictions, and a "dock to protein" button.

---

### 2. Trial Dashboard NSO

**Position:** Back wall of the lab (z = -3.0)

**Event types received:**
- `trial_metrics_updated` — Pushed after each patient allocation or outcome update

**Payload:**
```json
{
  "trial_id": "TRIAL-2026-EGFR",
  "arm_allocation_ratios": { "treatment_A": 0.68, "placebo": 0.32 },
  "enrolled_count": 142,
  "ae_rate_7day": 0.06,
  "safety_status": "green",
  "should_stop": false,
  "stopping_reason": null,
  "timestamp": "2026-03-28T08:00:00Z"
}
```

**Safety status mapping:**

| `ae_rate_7day` | `safety_status` | Dashboard colour |
|----------------|-----------------|-----------------|
| < 8% | `green` | Green glow |
| 8–15% | `yellow` | Amber pulse |
| > 15% | `red` | Red alarm flash |

**RIA behaviour:** Animated bar chart shows live allocation ratios per arm. AE rate gauge updates in real time. A red banner drops when `should_stop = true`.

---

### 3. Protein Viewer NSO

**Position:** Right wing of the lab (x = +4.0)

**Event types received:**
- `structure_available` — Pushed when `AlphaFold3NANDAIntegration.predict_structure()` completes

**Payload:**
```json
{
  "task_id": "af3-task-abc123",
  "sequence_preview": "MKTIIALSYIFCLVFA...",
  "pdb_url": "https://storage.agicorp.network/structures/af3-task-abc123.pdb",
  "position": { "x": 4.0, "y": 0.0, "z": 0.0, "rotation_y": 0 },
  "timestamp": "2026-03-28T08:01:30Z"
}
```

**RIA behaviour:** The PDB file is fetched and rendered as a ribbon diagram that slowly rotates. Residue confidence is colour-coded (pLDDT colouring). Researchers can walk around and inspect the structure. Multiple structures line up along the x-axis.

---

### 4. Agent Activity Feed NSO

**Position:** Ceiling-mounted display (y = +2.5)

**Event types received:**
- `agent_activity` — Pushed for task_started, task_completed, and task_failed events

**Payload:**
```json
{
  "agent_id": "compound-agent-03",
  "agent_type": "compound_discovery",
  "event_type": "task_completed",
  "description": "Screened 10,000 compounds against EGFR binding pocket",
  "timestamp": "2026-03-28T08:02:00Z",
  "metadata": { "top_hits": 23, "admet_passed": 8 }
}
```

**RIA behaviour:** Events scroll upward like a news ticker. Icons differentiate swarm types (🧪 compound, 🔬 genomics, 📚 literature, 🤖 structure). Completed tasks show a green checkmark; failed tasks show a red X with hover details.

---

### 5. Collaboration Hub NSO

**Position:** Centre of the lab (origin)

**Purpose:** Presence tracking and shared workspace coordination.

**Features:**
- Shows avatars of all researchers currently in the lab
- Spatial audio zones for team discussions
- Shared molecular workspace: anyone can move compound cards or protein structures
- Annotation system: sticky notes on NSO objects

---

## Data Flow: Complete Drug Discovery Session

```
1. Researcher enters the RP1 virtual lab via spatial browser
       │
2. GenomicSpatialSession.start()
   → RP1SpatialIntegration.initialize_virtual_lab()
   → 5 NSOs registered on fabric
       │
3. GenomicResearchAgentSwarm.run_drug_discovery_workflow("EGFR")
       │
4. For each compound_discovery agent task:
   → NANDAAgentIntegration.send_task_to_agent()
   → session.on_agent_task_started("compound-agent-03", ...)   ─→ Agent Feed NSO
       │
5. CompoundSearcher.search("EGFR kinase inhibitor") returns top-k
   → session.on_compound_found(compound_dict)                  ─→ Compound Viewer NSO
       │  (compound card flies into lab, researcher clicks it)
       │
6. AlphaFold3NANDAIntegration.predict_structure(sequence) completes
   → session.on_structure_predicted(task_id, seq, pdb_url)     ─→ Protein Viewer NSO
       │  (3D ribbon diagram appears; researcher walks around it)
       │
7. AdaptiveTrialDesign.allocate_patient("PT-042")
   → session.on_trial_metrics(trial_id, ratios, enrolled, ae_rate)  ─→ Trial Dashboard NSO
       │  (allocation bar animates; enrolled counter ticks up)
       │
8. SafetyMonitoringSystem detects elevated AE rate
   → session.on_trial_metrics(..., ae_rate=0.16, ...)          ─→ Dashboard turns RED
       │
9. Researcher pins a compound and sends it to colleague's avatar
   → Collaboration Hub NSO broadcasts the shared object
       │
10. GenomicSpatialSession.stop()
    → All NSOs deregistered; lab session ends
```

---

## Configuration

Add the following to your `.env` file (see [Configuration wiki](Configuration.md)):

```bash
# === RP1 Spatial Internet ===
RP1_API_KEY=your-rp1-developer-key      # From dev.rp1.com
RP1_FABRIC_ID=fab-xxxxxxxx              # Created via RP1 CLI
RP1_API_BASE_URL=https://api.rp1.com/v1
RP1_SOCKET_URL=https://socket.rp1.com
RP1_NSO_HOST=https://nso.genomic.agicorp.network
```

### `RP1Config` Dataclass

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `api_key` | `str` | `$RP1_API_KEY` | RP1 developer API key |
| `fabric_id` | `str` | `$RP1_FABRIC_ID` | Spatial fabric identifier |
| `base_url` | `str` | `https://api.rp1.com/v1` | RP1 REST API base URL |
| `socket_url` | `str` | `https://socket.rp1.com` | RP1 Socket.IO endpoint |
| `nso_host` | `str` | `https://nso.genomic.agicorp.network` | Self-hosted NSO server public URL |
| `lab_space_name` | `str` | `"Genomic Research Lab"` | Display name in RP1 browser |

---

## Quickstart

### 1. Set Up Your RP1 Developer Account

```bash
# Install the RP1 developer CLI tools
git clone https://github.com/jl-codes/rp1-dev-mcp.git
cd rp1-dev-mcp && npm install && npm run build

# Create your spatial fabric (3D environment)
npm run create_fabric
# Note the fabric_id — add it to your .env as RP1_FABRIC_ID
```

### 2. Deploy Your NSO Server

The NSO server is the backend that RP1 calls when users interact with objects in the virtual lab. Deploy this alongside the main Genomic.go API:

```bash
# The NSO server can be a simple Express/FastAPI server that
# receives RP1 webhook calls and dispatches to your platform logic.
# Deploy to a publicly reachable URL and set RP1_NSO_HOST.
```

### 3. Start the Virtual Lab

```python
import asyncio
from src.integrations.rp1_metaverse_integration import RP1Config, GenomicSpatialSession

async def main():
    config = RP1Config()  # Reads from environment variables
    session = GenomicSpatialSession(config)
    
    # Initialize the lab and register all NSOs
    summary = await session.start()
    print(f"Lab ready: {summary['nso_count']} NSOs registered")
    
    return session

session = asyncio.run(main())
```

### 4. Wire Up Platform Events

```python
# In your compound search flow:
results = await searcher.search("EGFR kinase inhibitor")
for compound in results:
    await session.on_compound_found(compound)

# In your AdaptiveTrialDesign loop:
arm = trial.allocate_patient(patient_id)
ratios = trial.get_allocation_ratios()
await session.on_trial_metrics(
    trial_id=trial.trial_id,
    arm_ratios=ratios,
    enrolled=sum(trial.enrolled.values()),
    ae_rate=safety_system.current_ae_rate,
)

# When AlphaFold3 prediction completes:
await session.on_structure_predicted(
    task_id=result["task_id"],
    protein_sequence=sequence,
    pdb_url=result["pdb_url"],
)

# When a NANDA agent completes a task:
await session.on_agent_task_completed(
    agent_id=agent_info["agent_id"],
    agent_type=agent_info["type"],
    description="Compound screening complete",
    result_summary={"hits": 23},
)
```

---

## NSO Endpoint Specification

Your self-hosted NSO server (`RP1_NSO_HOST`) must implement the following endpoints that RP1 calls when users interact with objects:

### `POST /nso/compound_viewer`

Called by RP1 when a user interacts with a compound card (click, inspect, share).

```json
{
  "event": "user_interaction",
  "user_id": "rp1-user-xyz",
  "compound_id": "CHEMBL475825",
  "interaction_type": "inspect"
}
```

Response:
```json
{
  "compound_detail": { ... },
  "admet_predictions": { ... },
  "similar_compounds_url": "/api/agents/compound-search/similar/CHEMBL475825"
}
```

### `POST /nso/trial_dashboard`

Called when a user selects a trial arm on the dashboard.

```json
{
  "event": "arm_selected",
  "user_id": "rp1-user-xyz",
  "trial_id": "TRIAL-2026-EGFR",
  "arm": "treatment_A"
}
```

### `POST /nso/protein_viewer`

Called when a user interacts with a 3D structure (rotate, annotate, download).

```json
{
  "event": "structure_interaction",
  "task_id": "af3-task-abc123",
  "interaction_type": "annotate",
  "residue_index": 42,
  "annotation": "Active site residue"
}
```

### `GET /nso/agent_feed`

Polled by RP1 RIA for initial event history on join.

Returns last 50 agent activity events sorted by timestamp descending.

### `POST /nso/collaboration`

Called for presence events: user join, leave, object move.

```json
{
  "event": "object_moved",
  "user_id": "rp1-user-xyz",
  "object_type": "compound_card",
  "object_id": "CHEMBL475825",
  "new_position": { "x": 2.0, "y": 0.0, "z": 1.5 }
}
```

---

## Security Considerations

- **API key**: Store `RP1_API_KEY` in GCP Secret Manager; never commit to source
- **NSO server**: Must validate that incoming requests originate from RP1 IPs (check `X-RP1-Signature` header)
- **Patient data**: Never include patient IDs or PHI in NSO payloads — use anonymised trial IDs only
- **Compound SMILES**: Can be included (not sensitive); proprietary structures should be watermarked
- **Presence data**: User identities from RP1 presence API are RP1 pseudonyms — no mapping to real names unless explicitly consented

---

## Testing

```python
# Mock the RP1 REST client for unit tests
from unittest.mock import MagicMock, patch, AsyncMock
from src.integrations.rp1_metaverse_integration import (
    RP1Config, GenomicSpatialSession, SpatialPosition
)

async def test_session_streams_compound():
    config = RP1Config(api_key="test", fabric_id="test-fab")
    session = GenomicSpatialSession(config)
    
    with patch.object(session._integration._client, "get_fabric", return_value={"name": "test"}), \
         patch.object(session._integration._client, "register_nso", return_value={"nso_id": "nso-1"}), \
         patch.object(session._integration._stream._client, "push_spatial_event", return_value=True):
        
        await session.start()
        
        compound = {
            "compound_id": "C1", "name": "Test", "smiles": "C", 
            "score": 0.9, "molecular_weight": 100.0, "target_protein": "EGFR"
        }
        await session.on_compound_found(compound, SpatialPosition(x=1, y=0, z=0))
        
        await session.stop()
```

---

_See also: [Integrations Deep Dive](Integrations-Deep-Dive.md) | [Architecture](Architecture.md) | [Configuration](Configuration.md)_
