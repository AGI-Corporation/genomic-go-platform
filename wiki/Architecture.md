# Architecture

This page describes the system architecture of the Genomic.go Platform — its components, data flows, infrastructure, and design decisions.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        API Gateway (FastAPI)                    │
│          OAuth 2.0 · JWT · Rate Limiting · mTLS                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
  ┌───────▼──────┐  ┌────────▼───────┐  ┌──────▼──────────┐
  │  Agent Swarm │  │  Compound Lib  │  │ Clinical Trials  │
  │  Orchestrator│  │  (Qdrant DB)   │  │  Optimizer       │
  │  (NANDA SDK) │  │  Semantic      │  │  (Bayesian +     │
  │  CrewAI      │  │  Search        │  │   Kafka Stream)  │
  └───────┬──────┘  └────────┬───────┘  └──────┬──────────┘
          │                  │                  │
  ┌───────▼──────────────────▼──────────────────▼──────────┐
  │                   Kalibr LLM Router                     │
  │       GPT-4o  ·  Claude Sonnet 4  ·  Gemini 2.5 Pro    │
  └─────────────────────────────────────────────────────────┘
          │
  ┌───────▼────────────────────────────────────────────────┐
  │               External Integrations                    │
  │  AlphaFold3 · Robotics · FHIR APIs · Ethereum/web3    │
  └────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. API Gateway

The entry point for all external traffic.

- **Framework**: FastAPI (async, OpenAPI-compliant)
- **Authentication**: OAuth 2.0 with JWT Bearer tokens
- **Transport security**: TLS 1.3 / mTLS between services
- **Rate limiting**: Per-user and per-endpoint throttling
- **Key endpoints**: `/v1/agents/*`, `/v1/workflows/*` (see [API Reference](API-Reference.md))

---

### 2. NANDA Agent Swarm Orchestrator

Manages 35+ specialized agent swarms (~75 agents per swarm) through the NANDA SDK (Internet of Agents).

**Swarm Categories:**

| Swarm | Count | Purpose |
|-------|-------|---------|
| Literature Analysis | 3 agents | Scientific paper search and summarization |
| Compound Discovery | 5 agents | Lead identification and optimization |
| Genomics Analysis | 4 agents | GWAS, multi-omic analysis |
| Protocol Automation | 3 agents | Experimental design |
| Structure Prediction | 2 agents | AlphaFold3 coordination |

**Agent Lifecycle:**
```
deploy_research_agent() → NANDA Registry Registration
        ↓
send_task_to_agent()    → HTTP POST /api/tasks (timeout: 300s)
        ↓
distribute_workflow()   → asyncio.gather() across parallel agents
        ↓
shutdown_agent()        → POST /api/shutdown + cleanup
```

**Key files:**
- `src/integrations/nanda_agent_integration.py` — `NANDAAgentIntegration`, `GenomicResearchAgentSwarm`
- `src/integrations/alphafold3_nanda_integration.py` — `NANDAProtocolCoordinator`

---

### 3. Kalibr LLM Router

Intelligent multi-model routing layer that reduces LLM costs by up to 90%.

- Supported models: GPT-4o, GPT-4o-mini, Claude Sonnet 4, Gemini 2.5 Pro
- Automatic failover between providers
- Cost and latency optimization
- Real-time performance monitoring

---

### 4. Compound Library (Qdrant)

Semantic vector search over 150 million+ chemical compounds.

| Property | Value |
|----------|-------|
| Database | Qdrant |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` (384-dim) |
| Distance metric | Cosine similarity |
| Indexing | HNSW (m=16, ef_construct=100) |
| Quantization | Scalar INT8 (memory-efficient) |

Filterable payload indexes: `target_protein`, `therapeutic_area`, `clinical_phase`, `molecular_weight`

**Key files:**
- `src/compound_library/init_compound_library.py` — collection initialization
- `src/compound_library/compound_searcher.py` — `CompoundSearcher` class

---

### 5. Clinical Trials Module

Real-time adaptive clinical trial management with Bayesian design and safety monitoring.

**Subsystems:**

| Class | Role |
|-------|------|
| `AdaptiveTrialDesign` | Thompson sampling randomization, O'Brien-Fleming stopping rules |
| `RealTimePatientMatcher` | 768-dim vector search to match patients to trials |
| `SafetyMonitoringSystem` | SPRT-based adverse event monitoring via Kafka |
| `EndpointPredictor` | XGBoost ML model for outcome prediction |

**Key file:** `src/clinical_trials/realtime_optimizer.py`

---

### 6. Event Streaming (Kafka)

Apache Kafka handles all real-time event flows within the platform.

| Topic | Direction | Purpose |
|-------|-----------|---------|
| `trial-allocations` | Write | Patient randomization records |
| `trial-alerts` | Write | Safety signal notifications |
| `adverse-events` | Read | Incoming adverse event stream |

Used by: `AdaptiveTrialDesign`, `SafetyMonitoringSystem`

---

### 7. Blockchain / DeSci Layer

On-chain intellectual property management using Ethereum.

- **Library**: `web3.py`
- **Use case**: IP-NFT minting for research outputs
- **Networks**: Mainnet, Sepolia testnet
- **Configuration**: `ETHEREUM_RPC_URL`, `PRIVATE_KEY`, `CONTRACT_ADDRESS`

---

## Data Flow: Drug Discovery Workflow

```
1. User submits target gene (e.g. "EGFR")
        │
2. GenomicResearchAgentSwarm.run_drug_discovery_workflow("EGFR")
        │
3. Literature agents search PubMed / bioarXiv
        │
4. Compound agents query Qdrant:
   "EGFR kinase inhibitor" → 384-dim embedding → HNSW search
        │
5. Kalibr router selects optimal LLM for ADMET analysis
        │
6. Genomics agents run GWAS correlation analysis
        │
7. Structure prediction agents submit to AlphaFold3 via NANDA
        │
8. Results gathered via asyncio.gather() across all agents
        │
9. IP-NFT minted on Ethereum for the research output
        │
10. Results returned to user via API
```

---

## Data Stores

| Store | Technology | Purpose |
|-------|-----------|---------|
| Vector DB | Qdrant | Compound embeddings, trial embeddings |
| Relational | PostgreSQL | Users, projects, logs, billing |
| Document | MongoDB | Agent conversations, workflow configs |
| Event stream | Kafka | Real-time trial and safety events |
| Blockchain | Ethereum | IP-NFT records |

---

## Cloud Infrastructure (GKE)

Platform is deployed on Google Cloud Platform using Google Kubernetes Engine.

### Node Pools

| Pool | Purpose | Autoscaling |
|------|---------|-------------|
| Agent pool | NANDA agent workloads | HPA enabled |
| Database pool | Qdrant, PostgreSQL, MongoDB | Fixed |
| API pool | FastAPI gateway | HPA enabled |

### Monitoring Stack

- **Metrics**: Prometheus
- **Dashboards**: Grafana
- **Logging**: Structured JSON logs via Python `logging` module

### Infrastructure Costs

Estimated at ~$16,000/month at full production scale.

### Disaster Recovery

| Metric | Target |
|--------|--------|
| RTO (Recovery Time Objective) | 1 hour |
| RPO (Recovery Point Objective) | 15 minutes |
| Backup strategy | Multi-region Qdrant snapshots + PostgreSQL WAL |

---

## Async Architecture

The platform is built on Python `asyncio` throughout:

- `asyncio.gather()` for parallel agent task execution
- `aiokafka` for non-blocking Kafka consumption
- `asyncio.create_subprocess_exec()` for NANDA agent process management
- Context managers (`__enter__`/`__exit__`) for Kafka producer lifecycle

---

## Design Principles

1. **Agent-centric**: Research tasks decomposed into specialized agent swarms
2. **Async-first**: All I/O-bound operations are non-blocking
3. **Redundancy**: AlphaFold3 tasks deployed to 2+ nodes; first success wins
4. **Cost-aware**: Kalibr router minimizes LLM spend dynamically
5. **Compliance-first**: HIPAA, GDPR, SOC 2 Type II compliance built into data flows
6. **Observable**: Every component emits structured logs and Prometheus metrics

---

_Next: [Getting Started](Getting-Started.md) | [API Reference](API-Reference.md)_
