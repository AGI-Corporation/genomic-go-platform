# Development Guide

Everything you need to contribute to the Genomic.go Platform: code standards, testing, linting, and the contribution workflow.

---

## Repository Setup

```bash
git clone https://github.com/AGI-Corporation/genomic-go-platform.git
cd genomic-go-platform
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

See [Getting Started](Getting-Started.md) for infrastructure setup (Qdrant, Kafka).

---

## Project Layout

```
src/
├── clinical_trials/
│   └── realtime_optimizer.py
├── compound_library/
│   ├── compound_searcher.py
│   └── init_compound_library.py
└── integrations/
    ├── nanda_agent_integration.py
    ├── alphafold3_nanda_integration.py
    └── robotics_nanda_integration.py

tests/
└── test_clinical_trials.py
```

All new source code goes under `src/`. All tests go under `tests/`.

---

## Code Standards

### Python Style

- **Formatter**: `black` (line length 88, default settings)
- **Import ordering**: `isort` (compatible with black)
- **Linter**: `flake8` + `pylint`
- **Type checker**: `mypy` (strict mode encouraged)

Run all formatters and linters before committing:

```bash
black src/ tests/
isort src/ tests/
flake8 src/ tests/
pylint src/
mypy src/
```

### Type Hints

All public functions and methods must include type hints:

```python
# Good
async def search(
    self,
    query: str,
    limit: int = 10,
    filters: Dict[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    ...

# Bad
async def search(self, query, limit=10, filters=None):
    ...
```

### Docstrings

Public classes and methods should have docstrings following Google style:

```python
def allocate_patient(self, patient_id: str) -> str:
    """Allocate a patient to a treatment arm via Thompson sampling.

    Args:
        patient_id: Unique identifier for the patient.

    Returns:
        The name of the allocated treatment arm.
    """
```

### Logging

Use module-level loggers — never `print()` in production code:

```python
import logging

logger = logging.getLogger(__name__)

# Use appropriate levels
logger.debug("Processing patient: %s", patient_id)
logger.info("Trial %s: patient allocated to %s", trial_id, arm)
logger.warning("AE rate approaching threshold: %.2f", rate)
logger.error("Failed to publish to Kafka: %s", exc)
```

Do **not** log sensitive data: patient IDs, API keys, genomic variants.

### Async Patterns

All I/O-bound operations must be async:

```python
# Correct: non-blocking
results = await asyncio.gather(*tasks, return_exceptions=True)

# Wrong: blocking call inside async function
results = [requests.get(url) for url in urls]  # blocks the event loop
```

Use `return_exceptions=True` in `asyncio.gather()` for resilient parallel execution.

### Error Handling

```python
# Re-raise after logging for upstream handling
try:
    result = await deploy_agent(agent_type, agent_id)
except Exception as exc:
    logger.error("Failed to deploy agent %s: %s", agent_id, exc)
    raise

# Non-fatal: log and continue (e.g. alerting failure)
try:
    producer.send("trial-alerts", payload)
except Exception as exc:
    logger.error("Failed to send Kafka alert: %s", exc)
    # Don't raise — alerting failure must not stop trial
```

### Dataclasses

Prefer `@dataclass` for configuration and data-transfer objects:

```python
from dataclasses import dataclass, field
from typing import List

@dataclass
class PatientProfile:
    patient_id: str
    age: int
    sex: str
    genomic_variants: List[str] = field(default_factory=list)
```

---

## Testing

### Test Framework

- `pytest` for all tests
- `pytest-asyncio` for async test functions
- `pytest-mock` for mocking
- `pytest-cov` for coverage reports

### Running Tests

```bash
# All tests
pytest

# Verbose output
pytest -v

# Specific module
pytest tests/test_clinical_trials.py

# With coverage
pytest --cov=src --cov-report=html
open htmlcov/index.html

# Async tests
pytest -m asyncio

# Show stdout
pytest -s
```

### Writing Tests

Every new module or significant function requires tests in `tests/`.

**Naming convention:**
- Test file: `tests/test_<module_name>.py`
- Test function: `test_<function_name>_<scenario>()`

**Example — async test:**

```python
import pytest
from unittest.mock import AsyncMock, patch
from src.compound_library.compound_searcher import CompoundSearcher

@pytest.mark.asyncio
async def test_search_returns_results_for_valid_query():
    searcher = CompoundSearcher(qdrant_url="http://localhost:6333")
    
    mock_results = [{"compound_id": "C1", "name": "Test", "score": 0.9}]
    with patch.object(searcher, "_client") as mock_client:
        mock_client.search = AsyncMock(return_value=mock_results)
        results = await searcher.search("EGFR inhibitor", limit=5)
    
    assert len(results) == 1
    assert results[0]["name"] == "Test"


@pytest.mark.asyncio
async def test_search_returns_empty_list_when_no_matches():
    searcher = CompoundSearcher()
    with patch.object(searcher, "_client") as mock_client:
        mock_client.search = AsyncMock(return_value=[])
        results = await searcher.search("nonexistent compound xyz")
    
    assert results == []
```

**Mocking Kafka:**

```python
from unittest.mock import MagicMock, patch

def test_allocate_patient_publishes_to_kafka():
    with patch("src.clinical_trials.realtime_optimizer.KafkaProducer") as mock_producer:
        mock_instance = MagicMock()
        mock_producer.return_value = mock_instance
        
        with AdaptiveTrialDesign("T1", ["A", "B"]) as trial:
            arm = trial.allocate_patient("PT-001")
        
        assert arm in ["A", "B"]
        mock_instance.send.assert_called_once()
```

### Coverage Targets

| Module | Target coverage |
|--------|----------------|
| `clinical_trials/` | ≥ 80% |
| `compound_library/` | ≥ 75% |
| `integrations/` | ≥ 70% |

---

## Contribution Workflow

### Branching Strategy

```
main            ← Production-stable
  └── develop   ← Integration branch
        └── feature/<short-description>
        └── fix/<short-description>
        └── chore/<short-description>
```

**Branch naming examples:**
- `feature/genomics-gwas-agent`
- `fix/kafka-producer-cleanup`
- `chore/update-qdrant-client`

### Commit Messages

Follow Conventional Commits:

```
feat: add GWAS analysis to genomics agent swarm
fix: close Kafka producer on AdaptiveTrialDesign.__exit__
docs: update compound library guide with filter examples
test: add unit tests for SafetyMonitoringSystem
chore: upgrade qdrant-client to 1.9.0
refactor: extract patient embedding logic into helper function
```

### Pull Request Process

1. Create feature branch from `develop`
2. Implement changes with tests
3. Run linters and tests locally — all must pass
4. Run `safety check` and `bandit -r src/`
5. Open PR against `develop`
6. Ensure CI checks pass
7. Request review from a maintainer
8. Address review comments
9. Squash-merge when approved

### CI Checks

All PRs must pass:
- `pytest --cov=src`
- `black --check src/ tests/`
- `flake8 src/ tests/`
- `mypy src/`
- `bandit -r src/ -ll`
- `safety check`

---

## Adding New Integrations

When adding a new integration under `src/integrations/`:

1. Create `src/integrations/<name>_integration.py`
2. Follow the NANDA pattern: dataclass config → integration class → high-level interface class
3. Use async methods for all I/O
4. Add corresponding `tests/test_<name>_integration.py`
5. Document the new module in [Modules Reference](Modules.md)
6. Document any new environment variables in [Configuration](Configuration.md)

---

## Load Testing

`locust` is included in dev dependencies for load testing the API:

```bash
locust -f tests/locustfile.py --host https://api.genomic.agicorp.network
```

---

## Documentation

- `sphinx` + `sphinx-rtd-theme` for auto-generated API docs from docstrings
- Build docs: `sphinx-build -b html docs/ docs/_build/`
- Wiki pages live in `wiki/` — update them when adding modules or changing APIs

---

_Next: [Deployment](Deployment.md) | [Home](Home.md)_
