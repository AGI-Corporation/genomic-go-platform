# Modules Reference

Detailed documentation for every Python module in the `src/` directory.

---

## Module Map

```
src/
├── clinical_trials/
│   └── realtime_optimizer.py          ~427 lines
├── compound_library/
│   ├── compound_searcher.py           ~211 lines
│   └── init_compound_library.py       ~211 lines
└── integrations/
    ├── nanda_agent_integration.py     ~367 lines
    ├── alphafold3_nanda_integration.py ~156 lines
    └── robotics_nanda_integration.py  ~105 lines
```

Total core implementation: ~1,477 lines

---

## `src/clinical_trials/realtime_optimizer.py`

### Purpose

Real-time adaptive clinical trial management combining Bayesian statistics, vector search, Kafka event streaming, and machine learning.

---

### Class: `PatientProfile`

A `dataclass` representing a patient's clinical and genomic data.

| Field | Type | Description |
|-------|------|-------------|
| `patient_id` | `str` | Unique patient identifier |
| `age` | `int` | Patient age in years |
| `sex` | `str` | Biological sex |
| `genomic_variants` | `List[str]` | Relevant gene variants (e.g. `["APOE4", "BRCA1"]`) |
| `biomarkers` | `Dict[str, float]` | Quantitative biomarker values |
| `comorbidities` | `List[str]` | Current comorbid conditions |
| `medications` | `List[str]` | Current medications |
| `eligibility_criteria` | `Dict[str, Any]` | Trial-specific eligibility data |

---

### Class: `AdaptiveTrialDesign`

Implements a Bayesian adaptive randomized controlled trial with real-time monitoring.

**Constructor parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `trial_id` | `str` | — | Unique trial identifier |
| `arms` | `List[str]` | — | Treatment arm names |
| `kafka_servers` | `str` | `"localhost:9092"` | Kafka bootstrap servers |

**Context manager**: Use as `with AdaptiveTrialDesign(...) as trial:` to ensure Kafka producer cleanup.

#### Methods

**`allocate_patient(patient_id: str) -> str`**

Allocates a patient to a treatment arm using **Thompson sampling**.

- Samples from Beta(successes + 1, failures + 1) for each arm
- Returns the arm with the highest sampled value
- Publishes allocation event to Kafka topic `trial-allocations`

**`update_outcome(patient_id: str, arm: str, success: bool) -> None`**

Updates the Beta distribution posterior for the given arm.

- `success=True` increments `successes[arm]`
- `success=False` increments `failures[arm]`

**`check_stopping_rules() -> Tuple[bool, str]`**

Evaluates O'Brien-Fleming boundaries for early stopping.

Returns `(should_stop, reason)` where `reason` is one of:
- `"futility"` — arm success rate below 20%
- `"superiority"` — Z-test exceeds boundary 4.0
- `""` — no stopping condition met

**`get_allocation_ratios() -> Dict[str, float]`**

Returns current posterior mean for each arm:
```
successes[arm] / (successes[arm] + failures[arm])
```

---

### Class: `RealTimePatientMatcher`

Matches patients to open clinical trials using 768-dimensional vector embeddings and Qdrant.

**Constructor parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `qdrant_url` | `str` | `"http://localhost:6333"` | Qdrant instance URL |
| `collection` | `str` | `"clinical_trials_embeddings"` | Collection name |

#### Methods

**`async create_patient_embedding(patient: PatientProfile) -> List[float]`**

Creates a 768-dimensional vector embedding from patient attributes (age, sex, genomics, biomarkers, comorbidities, medications).

**`async find_matching_trials(patient: PatientProfile, limit: int = 20) -> List[Dict]`**

Full matching pipeline:
1. Creates patient embedding
2. Queries Qdrant with `score_threshold=0.7`
3. Applies hard eligibility filters:
   - Age: `min_age ≤ patient.age ≤ max_age`
   - Genomics: `patient.genomic_variants ⊇ trial.required_markers`
   - Exclusions: `patient.comorbidities ∩ trial.excluded_comorbidities = ∅`
4. Returns ranked list with similarity scores

---

### Class: `SafetyMonitoringSystem`

Consumes the Kafka `adverse-events` topic and raises alerts using Sequential Probability Ratio Test (SPRT).

**Constructor parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `trial_id` | `str` | — | Trial to monitor |
| `kafka_servers` | `str` | `"localhost:9092"` | Kafka bootstrap servers |
| `safety_threshold` | `float` | `0.15` | Maximum acceptable AE rate |

#### Methods

**`async start_monitoring() -> None`**

Starts async Kafka consumer on `adverse-events` topic. Processes events continuously, maintaining a 7-day rolling window.

**`async process_adverse_event(event: Dict) -> None`**

For each incoming event:
1. Increments adverse event counter
2. Calculates 7-day rolling rate
3. Publishes to `trial-alerts` if rate exceeds `safety_threshold`

---

### Class: `EndpointPredictor`

XGBoost-based predictor for clinical trial primary endpoints.

**Constructor parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model_path` | `str` | — | Path to pre-trained XGBoost model file |

#### Methods

**`predict(interim_data: Dict) -> Dict[str, float]`**

Returns:
```python
{
    "probability": 0.742,        # Predicted success probability
    "ci_lower": 0.681,           # 95% CI lower bound (bootstrap)
    "ci_upper": 0.803,           # 95% CI upper bound (bootstrap)
    "extrapolated_endpoint": 0.75 # Estimated final endpoint value
}
```

Uses 100 bootstrap iterations for confidence interval calculation.

---

## `src/compound_library/init_compound_library.py`

### Purpose

One-time initialization of the Qdrant `compound_library` collection from a JSONL data file.

### Functions

**`read_compounds(file_path: str) -> List[Dict]`**

Reads compound data from a JSONL file. Each line must be a valid JSON object.

Required fields per compound:
- `compound_id`, `name`, `description`, `smiles`, `molecular_weight`
- `target_protein`, `therapeutic_area`, `clinical_phase`

Optional: `mechanism`, `indications`

---

**`create_compound_collection(client: QdrantClient) -> None`**

Creates the Qdrant collection with:
- Vector size: 384
- Distance: COSINE
- HNSW index: m=16, ef_construct=100
- Scalar quantization: INT8
- On-disk storage: enabled

---

**`create_payload_indexes(client: QdrantClient) -> None`**

Creates filterable payload indexes:

| Field | Index type |
|-------|-----------|
| `description` | Text (WORD tokenizer, min_token=2) |
| `target_protein` | Keyword |
| `therapeutic_area` | Keyword |
| `clinical_phase` | Keyword |
| `molecular_weight` | Integer |

---

**`upload_compounds(client: QdrantClient, compounds: List[Dict]) -> None`**

Generates embeddings with `sentence-transformers/all-MiniLM-L6-v2` and uploads in batches with a progress bar.

---

## `src/compound_library/compound_searcher.py`

### Purpose

Semantic search engine over the compound library, supporting natural language queries and multi-filter operations.

---

### Class: `CompoundSearcher`

**Constructor parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `qdrant_url` | `str` | `"http://localhost:6333"` | Qdrant URL |
| `qdrant_api_key` | `str \| None` | `None` | API key for Qdrant Cloud |
| `collection` | `str` | `"compound_library"` | Collection name |

Embedding model is loaded on initialization: `sentence-transformers/all-MiniLM-L6-v2`

#### Methods

**`async search(query: str, limit: int = 10, filters: Dict = None) -> List[Dict]`**

Encodes the natural language query and performs ANN search.

`filters` supports:
```python
{
    "therapeutic_area": "Oncology",
    "clinical_phase": "Approved",
    "target_protein": "EGFR",
    "mw_min": 200,
    "mw_max": 600
}
```

Returns list of hits with `name`, `score`, `smiles`, `molecular_weight`, `target_protein`, etc.

---

**`async find_similar_compounds(compound_id: str, limit: int = 10) -> List[Dict]`**

Looks up the vector for `compound_id` and returns the top-k most similar compounds by cosine similarity.

---

**`async get_collection_stats() -> Dict`**

Returns:
```python
{
    "total_compounds": 150000000,
    "indexed_vectors": 150000000,
    "collection_status": "green"
}
```

---

## `src/integrations/nanda_agent_integration.py`

### Purpose

Integration layer with the NANDA SDK (Internet of Agents) for deploying and orchestrating distributed research agents.

---

### Dataclass: `NANDAAgentConfig`

Configuration for connecting to the NANDA registry and deploying agents.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `anthropic_key` | `str` | — | Anthropic API key for agents |
| `domain` | `str` | `"genomic.agicorp.network"` | Deployment domain |
| `registry_url` | `str` | `"chat.nanda-registry.com"` | NANDA registry endpoint |
| `port_start` | `int` | `8000` | Starting port for agents |
| `smithery_key` | `str \| None` | `None` | Optional Smithery key |

---

### Class: `NANDAAgentIntegration`

Core NANDA integration providing agent lifecycle management.

#### Methods

**`async deploy_research_agent(agent_type: str, agent_id: str) -> Dict`**

Deploys a NANDA agent subprocess and registers it with the NANDA registry.

Returns:
```python
{
    "agent_id": "literature-agent-1",
    "agent_type": "literature_analysis",
    "endpoint": "http://genomic.agicorp.network:8001",
    "status": "running"
}
```

**`async create_agent_swarm(swarm_type: str, size: int) -> List[Dict]`**

Deploys `size` agents of `swarm_type` in parallel using `asyncio.gather()`.

**`async send_task_to_agent(agent_id: str, task: Dict) -> Dict`**

HTTP POST to agent's `/api/tasks` endpoint with 300-second timeout.

**`async distribute_workflow(workflow_steps: List[Dict]) -> List[Dict]`**

Maps workflow steps to agents and gathers results in parallel.

**`async get_agent_status(agent_id: str) -> str`**

GET `/health` → returns `"healthy"`, `"unhealthy"`, or `"unreachable"`.

**`async shutdown_agent(agent_id: str) -> bool`**

POST `/api/shutdown` then terminates the subprocess.

---

### Class: `GenomicResearchAgentSwarm`

High-level interface for the full research infrastructure.

#### Methods

**`async initialize_research_infrastructure() -> None`**

Deploys all swarms in sequence:
1. 3 literature analysis agents
2. 5 compound discovery agents
3. 4 genomics analysis agents
4. 3 protocol automation agents
5. 2 structure prediction agents

**`async run_drug_discovery_workflow(target_gene: str) -> Dict`**

Orchestrates a complete drug discovery pipeline for the given gene target. Returns aggregated results from all agent swarms.

---

## `src/integrations/alphafold3_nanda_integration.py`

### Purpose

Distributed AlphaFold3 protein structure prediction with automatic redundancy and failover via the NANDA protocol.

---

### Enum: `AgentTaskStatus`

| Value | Meaning |
|-------|---------|
| `PENDING` | Task submitted, not yet dispatched |
| `PROCESSING` | Dispatched to one or more nodes |
| `COMPLETED` | At least one node returned a result |
| `FAILED` | All nodes failed |
| `RETRYING` | Failover in progress |

---

### Dataclass: `AlphaFoldTask`

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | `str` | Unique task UUID |
| `sequence` | `str` | Protein amino acid sequence |
| `model_seeds` | `List[int]` | Random seeds for prediction (default: `[1, 2, 3]`) |
| `status` | `AgentTaskStatus` | Current status |
| `retry_count` | `int` | Number of failover attempts |
| `assigned_node` | `str \| None` | Node ID currently executing the task |

---

### Class: `NANDAProtocolCoordinator`

Distributed task coordinator with health monitoring and failover.

#### Methods

**`register_node(node_id: str, capabilities: Dict) -> None`**

Registers a compute node with its capabilities (e.g., GPU type, memory).

**`async submit_task(sequence: str, redundancy_factor: int = 2) -> str`**

Creates an `AlphaFoldTask` and dispatches it to `redundancy_factor` nodes. Returns the `task_id`.

**`async monitor_health() -> None`**

Background coroutine that checks node heartbeats every 10 seconds with a 30-second timeout. Triggers `_handle_node_failure()` for unresponsive nodes.

**`async _handle_node_failure(node_id: str) -> None`**

Reassigns in-flight tasks from the failed node to available healthy nodes.

---

### Class: `AlphaFold3NANDAIntegration`

Thin wrapper providing a simple `predict_structure()` interface.

**`async predict_structure(sequence: str) -> Dict`**

Submits the sequence to the coordinator with default seeds `[1, 2, 3]` and `redundancy_factor=2`. Returns the structural prediction result from the first successful node.

---

## `src/integrations/robotics_nanda_integration.py`

### Purpose

Integration layer for laboratory robotics automation via the NANDA protocol.

> **Status**: Foundational implementation in place (~105 lines). Full robotics workflow automation is under active development.

Planned capabilities:
- Liquid handling automation
- Plate reader integration
- Compound dispensing workflows
- Experimental protocol execution

---

_Next: [API Reference](API-Reference.md) | [Algorithms](Algorithms.md)_
