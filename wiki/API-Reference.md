# API Reference

This page documents all HTTP endpoints, Kafka topics, and request/response schemas exposed by the Genomic.go Platform.

---

## HTTP Endpoints

The API gateway is built with FastAPI and served over HTTPS with JWT Bearer token authentication.

**Base URL:** `https://api.genomic.agicorp.network/v1`

**Authentication header:**
```
Authorization: Bearer <jwt_token>
```

---

### Agent Endpoints

#### `POST /v1/agents/compound-search`

Semantic search over the compound library.

**Request body:**
```json
{
  "query": "EGFR kinase inhibitor for lung cancer",
  "limit": 10,
  "filters": {
    "therapeutic_area": "Oncology",
    "clinical_phase": "Approved",
    "target_protein": "EGFR",
    "mw_min": 200,
    "mw_max": 700
  }
}
```

**Response:**
```json
{
  "results": [
    {
      "compound_id": "CHEMBL475825",
      "name": "Erlotinib",
      "score": 0.923,
      "smiles": "C#Cc1cccc(Nc2ncnc3cc(OCC)c(OCC)cc23)c1",
      "molecular_weight": 393.4,
      "target_protein": "EGFR",
      "mechanism": "Tyrosine kinase inhibitor",
      "therapeutic_area": "Oncology",
      "clinical_phase": "Approved"
    }
  ],
  "total": 10,
  "query_time_ms": 42
}
```

---

#### `POST /v1/agents/protein-predict`

Predict protein structure using AlphaFold3 via the NANDA distributed network.

**Request body:**
```json
{
  "sequence": "MKTIIALSYIFCLVFA...",
  "model_seeds": [1, 2, 3],
  "redundancy_factor": 2
}
```

**Response:**
```json
{
  "task_id": "af3-task-abc123",
  "status": "PROCESSING",
  "estimated_time_seconds": 120
}
```

Poll for result:
```
GET /v1/agents/protein-predict/{task_id}
```

---

#### `GET /v1/agents/compound-search/similar/{compound_id}`

Find compounds similar to a known reference compound.

**Path parameter:** `compound_id` — Qdrant point ID (e.g. `CHEMBL475825`)

**Query parameters:**
- `limit` (int, default 10) — number of results

**Response:** Same schema as compound-search results array.

---

### Workflow Endpoints

#### `POST /v1/workflows/drug-discovery`

Execute the complete drug discovery pipeline for a gene target.

**Request body:**
```json
{
  "target_gene": "EGFR",
  "therapeutic_area": "Oncology",
  "max_compounds": 50,
  "include_structure_prediction": true
}
```

**Response:**
```json
{
  "workflow_id": "wf-xyz789",
  "status": "running",
  "stages": [
    "literature_analysis",
    "compound_discovery",
    "genomics_analysis",
    "structure_prediction"
  ]
}
```

Poll:
```
GET /v1/workflows/drug-discovery/{workflow_id}
```

---

#### `GET /v1/workflows/drug-discovery/{workflow_id}`

Get the status and results of a running or completed workflow.

**Response:**
```json
{
  "workflow_id": "wf-xyz789",
  "status": "completed",
  "target_gene": "EGFR",
  "results": {
    "literature_summary": "...",
    "top_compounds": [...],
    "genomics_insights": "...",
    "predicted_structures": [...]
  },
  "ip_nft_tx": "0xabc123..."
}
```

---

### Clinical Trial Endpoints

#### `POST /v1/trials/{trial_id}/allocate`

Allocate a patient to a treatment arm using Thompson sampling.

**Request body:**
```json
{
  "patient_id": "PT-00042"
}
```

**Response:**
```json
{
  "patient_id": "PT-00042",
  "allocated_arm": "treatment_A",
  "allocation_ratios": {
    "treatment_A": 0.68,
    "placebo": 0.32
  }
}
```

---

#### `POST /v1/trials/{trial_id}/outcome`

Record a patient's outcome to update the Bayesian posterior.

**Request body:**
```json
{
  "patient_id": "PT-00042",
  "arm": "treatment_A",
  "success": true
}
```

**Response:**
```json
{
  "updated_ratios": {
    "treatment_A": 0.71,
    "placebo": 0.29
  },
  "should_stop": false,
  "stopping_reason": null
}
```

---

#### `POST /v1/trials/match-patient`

Find matching open clinical trials for a patient profile.

**Request body:**
```json
{
  "patient_id": "PT-00042",
  "age": 58,
  "sex": "F",
  "genomic_variants": ["APOE4", "BRCA1"],
  "biomarkers": {"PSA": 4.2, "CA-125": 35},
  "comorbidities": ["Hypertension"],
  "medications": ["Metformin"]
}
```

**Response:**
```json
{
  "matches": [
    {
      "trial_id": "NCT-001234",
      "title": "Phase III EGFR Inhibitor Study",
      "phase": "Phase III",
      "similarity_score": 0.89,
      "eligibility": "eligible"
    }
  ]
}
```

---

### Agent Management Endpoints

These endpoints are exposed on each individual NANDA agent process.

#### `GET /health`

Agent liveness check.

**Response:** `200 OK` if healthy.

#### `POST /api/tasks`

Submit a research task to the agent.

**Request body:**
```json
{
  "task_type": "literature_search",
  "payload": {
    "query": "EGFR inhibitor resistance mechanisms",
    "max_papers": 20
  }
}
```

**Response:**
```json
{
  "task_id": "task-abc",
  "status": "accepted"
}
```

#### `POST /api/shutdown`

Gracefully shut down the agent.

---

## Kafka Topics

The platform uses Apache Kafka for real-time event streaming between the clinical trials module and monitoring systems.

### `trial-allocations`

**Direction:** Platform → Consumers  
**Schema:**
```json
{
  "trial_id": "TRIAL-001",
  "patient_id": "PT-00042",
  "allocated_arm": "treatment_A",
  "timestamp": "2026-03-28T07:16:50Z",
  "allocation_probabilities": {
    "treatment_A": 0.68,
    "placebo": 0.32
  }
}
```

---

### `trial-alerts`

**Direction:** Platform → Consumers  
**Schema:**
```json
{
  "trial_id": "TRIAL-001",
  "alert_type": "safety_threshold_exceeded",
  "severity": "high",
  "ae_rate_7day": 0.18,
  "threshold": 0.15,
  "timestamp": "2026-03-28T07:16:50Z",
  "recommended_action": "dsmb_review"
}
```

Alert types:
- `safety_threshold_exceeded` — AE rate above configured threshold
- `futility_boundary_crossed` — Trial unlikely to show effect
- `superiority_boundary_crossed` — Early stopping for efficacy

---

### `adverse-events`

**Direction:** External systems → Platform  
**Schema:**
```json
{
  "trial_id": "TRIAL-001",
  "patient_id": "PT-00042",
  "event_type": "grade_3_nausea",
  "severity": "grade_3",
  "timestamp": "2026-03-28T07:16:50Z",
  "reported_by": "site_001"
}
```

---

## Error Responses

All HTTP endpoints use standard error format:

```json
{
  "error": {
    "code": "COMPOUND_NOT_FOUND",
    "message": "Compound CHEMBL999999 not found in library",
    "request_id": "req-abc123"
  }
}
```

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| `200` | Success |
| `201` | Created |
| `400` | Bad request (invalid input) |
| `401` | Unauthorized (missing/invalid JWT) |
| `403` | Forbidden (insufficient permissions) |
| `404` | Resource not found |
| `429` | Rate limit exceeded |
| `500` | Internal server error |
| `503` | Service unavailable (agent down) |

---

## RP1 Spatial Internet — NSO Server Endpoints

The Genomic.go Platform self-hosts an **NSO (Network Service Object) server** at `RP1_NSO_HOST` that RP1 calls when users interact with objects in the virtual lab. These endpoints are distinct from the main API gateway — they are inbound calls from RP1, not outbound calls from clients.

All NSO endpoints must validate the `X-RP1-Signature` header to ensure requests originate from RP1.

### `POST /nso/compound_viewer`

Called when a user interacts with a 3D compound card.

**Request from RP1:**
```json
{
  "event": "user_interaction",
  "user_id": "rp1-user-abc",
  "compound_id": "CHEMBL475825",
  "interaction_type": "inspect"
}
```

`interaction_type` values: `inspect`, `share`, `pin`, `download_smiles`

**Response:**
```json
{
  "compound_detail": {
    "compound_id": "CHEMBL475825",
    "name": "Erlotinib",
    "admet": { "bioavailability": 0.82, "toxicity": "low" }
  },
  "similar_compounds_url": "/v1/agents/compound-search/similar/CHEMBL475825"
}
```

---

### `POST /nso/trial_dashboard`

Called when a user selects a trial arm or requests drill-down data.

**Request from RP1:**
```json
{
  "event": "arm_selected",
  "user_id": "rp1-user-abc",
  "trial_id": "TRIAL-2026-EGFR",
  "arm": "treatment_A"
}
```

**Response:**
```json
{
  "arm": "treatment_A",
  "successes": 48,
  "failures": 22,
  "posterior_mean": 0.686,
  "enrolled": 70
}
```

---

### `POST /nso/protein_viewer`

Called when a user annotates a residue or requests structure download.

**Request from RP1:**
```json
{
  "event": "structure_interaction",
  "task_id": "af3-task-abc123",
  "interaction_type": "annotate",
  "residue_index": 42,
  "annotation": "Active site residue"
}
```

**Response:**
```json
{
  "annotation_saved": true,
  "annotation_id": "ann-xyz"
}
```

---

### `GET /nso/agent_feed`

Polled by the RP1 RIA on join to populate initial event history.

**Response:**
```json
{
  "events": [
    {
      "agent_id": "compound-agent-03",
      "agent_type": "compound_discovery",
      "event_type": "task_completed",
      "description": "Screened 10,000 compounds against EGFR binding pocket",
      "timestamp": "2026-03-28T08:02:00Z",
      "metadata": { "top_hits": 23, "admet_passed": 8 }
    }
  ],
  "total": 1
}
```

Returns last 50 events, most recent first.

---

### `POST /nso/collaboration`

Called for presence events and shared object manipulation.

**Request from RP1 (object moved):**
```json
{
  "event": "object_moved",
  "user_id": "rp1-user-abc",
  "object_type": "compound_card",
  "object_id": "CHEMBL475825",
  "new_position": { "x": 2.0, "y": 0.0, "z": 1.5, "rotation_y": 45 }
}
```

**Request from RP1 (user joined):**
```json
{
  "event": "user_joined",
  "user_id": "rp1-user-abc",
  "display_name": "Dr. Chen",
  "position": { "x": 0.0, "y": 0.0, "z": 0.0, "rotation_y": 0 }
}
```

**Response:** `204 No Content`

---

_Next: [Algorithms](Algorithms.md) | [Configuration](Configuration.md) | [RP1 Metaverse Integration](RP1-Metaverse-Integration.md)_
