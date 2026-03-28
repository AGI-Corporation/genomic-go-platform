# Getting Started

This page guides you through installing and running the Genomic.go Platform locally.

---

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.9+ (3.10+ recommended) | Core runtime |
| pip | Latest | Package manager |
| Docker | 20+ | For Qdrant and Kafka |
| Git | Any | Source control |
| Anthropic API key | — | Required for NANDA agents |
| OpenAI API key | — | Required for Kalibr router |

Optional but recommended:
- `virtualenv` or `conda` for environment isolation
- Docker Compose for multi-container setup

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/AGI-Corporation/genomic-go-platform.git
cd genomic-go-platform
```

### 2. Create a Python Virtual Environment

```bash
python -m venv venv
source venv/bin/activate        # Linux/macOS
# venv\Scripts\activate         # Windows
```

### 3. Install Dependencies

```bash
# Production dependencies
pip install -r requirements.txt

# Development/testing dependencies (optional)
pip install -r requirements-dev.txt
```

### 4. Configure Environment Variables

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your API keys and service URLs. See [Configuration](Configuration.md) for all available variables.

Minimum required variables:

```bash
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
QDRANT_URL=http://localhost:6333
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
```

---

## Starting Infrastructure Services

### Qdrant Vector Database

```bash
docker run -d \
  --name qdrant \
  -p 6333:6333 \
  -p 6334:6334 \
  -v $(pwd)/qdrant_storage:/qdrant/storage:z \
  qdrant/qdrant
```

Health check: `curl http://localhost:6333/healthz`

### Kafka & Zookeeper

```bash
docker-compose up -d kafka zookeeper
```

> If no `docker-compose.yml` is present, create a minimal one or use a managed Kafka service and point `KAFKA_BOOTSTRAP_SERVERS` at it.

---

## Initialize the Compound Library

Before running compound searches, you must populate the Qdrant collection:

```bash
python -m src.compound_library.init_compound_library
```

This will:
1. Create the `compound_library` Qdrant collection
2. Create filterable payload indexes
3. Upload compounds from `data/compounds.json` (JSONL format)
4. Print collection statistics on completion

Expected compound payload format:
```json
{
  "compound_id": "CHEMBL12345",
  "name": "Imatinib",
  "description": "Tyrosine kinase inhibitor for CML",
  "smiles": "CC1=C(C=C(C=C1)NC(=O)...",
  "molecular_weight": 493.6,
  "target_protein": "BCR-ABL",
  "mechanism": "Kinase inhibitor",
  "therapeutic_area": "Oncology",
  "clinical_phase": "Approved",
  "indications": ["CML", "GIST"]
}
```

---

## Running the Platform

```bash
# Start the API server (if configured)
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or run the main entry point directly
python main.py
```

---

## Quickstart Examples

### Compound Search

```python
import asyncio
from src.compound_library.compound_searcher import CompoundSearcher

async def main():
    searcher = CompoundSearcher()
    
    # Natural language semantic search
    results = await searcher.search(
        query="EGFR kinase inhibitor for lung cancer",
        limit=10,
        filters={
            "therapeutic_area": "Oncology",
            "clinical_phase": "Approved"
        }
    )
    
    for r in results:
        print(f"{r['name']} (score: {r['score']:.3f})")

asyncio.run(main())
```

### Drug Discovery Workflow (Full Pipeline)

```python
import asyncio
from src.integrations.nanda_agent_integration import (
    NANDAAgentConfig,
    GenomicResearchAgentSwarm
)

config = NANDAAgentConfig(
    anthropic_key="sk-ant-...",
    domain="genomic.agicorp.network"
)

async def main():
    swarm = GenomicResearchAgentSwarm(config)
    
    # Deploy all research agents
    await swarm.initialize_research_infrastructure()
    
    # Run full drug discovery pipeline for a target gene
    results = await swarm.run_drug_discovery_workflow("EGFR")
    print(results)

asyncio.run(main())
```

### Protein Structure Prediction

```python
import asyncio
from src.integrations.alphafold3_nanda_integration import (
    AlphaFold3NANDAIntegration,
    NANDAProtocolCoordinator
)

coordinator = NANDAProtocolCoordinator()
af3 = AlphaFold3NANDAIntegration(coordinator)

async def main():
    # Register compute nodes
    coordinator.register_node("node-1", {"gpu": True, "memory": "40GB"})
    coordinator.register_node("node-2", {"gpu": True, "memory": "40GB"})
    
    # Predict structure (uses redundancy factor 2)
    result = await af3.predict_structure("MKTIIALSYIFCLVFA...")
    print(result)

asyncio.run(main())
```

### Adaptive Clinical Trial

```python
from src.clinical_trials.realtime_optimizer import (
    AdaptiveTrialDesign,
    RealTimePatientMatcher,
    PatientProfile
)

# Create a trial
with AdaptiveTrialDesign(
    trial_id="TRIAL-001",
    arms=["treatment_A", "placebo"],
    kafka_servers="localhost:9092"
) as trial:
    # Allocate a patient
    arm = trial.allocate_patient("PATIENT-42")
    print(f"Patient allocated to: {arm}")
    
    # Update with outcome
    trial.update_outcome("PATIENT-42", arm, success=True)
    
    # Check stopping rules
    should_stop, reason = trial.check_stopping_rules()
    if should_stop:
        print(f"Trial stopped: {reason}")
```

---

## Running Tests

```bash
# Run all tests
pytest

# With coverage report
pytest --cov=src --cov-report=html

# Run a specific file verbosely
pytest tests/test_clinical_trials.py -v

# Run async tests only
pytest -m asyncio

# Run with output captured
pytest -s
```

---

## Linting and Type Checking

```bash
# Format code
black src/

# Check import order
isort src/

# Lint
flake8 src/
pylint src/

# Type checking
mypy src/

# Security scan
bandit -r src/
safety check
```

---

## Next Steps

- [Modules Reference](Modules.md) — understand each Python module in depth
- [Configuration](Configuration.md) — full list of environment variables
- [Architecture](Architecture.md) — how the components fit together
- [API Reference](API-Reference.md) — HTTP endpoints and Kafka topics
