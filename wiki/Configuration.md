# Configuration

All environment variables and configuration options for the Genomic.go Platform.

---

## Setting Up Environment Variables

Copy `.env.example` to `.env` and populate each variable:

```bash
cp .env.example .env
```

Variables are loaded at runtime via `python-dotenv`. In production, prefer injecting secrets via Kubernetes Secrets or a secrets manager (e.g. GCP Secret Manager).

---

## Required Variables

These variables must be set for the platform to function.

### LLM Providers

| Variable | Description | Example |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API key (Claude models + NANDA agents) | `sk-ant-api03-...` |
| `OPENAI_API_KEY` | OpenAI API key (GPT-4o, Kalibr router) | `sk-proj-...` |

### Vector Database (Qdrant)

| Variable | Description | Default |
|----------|-------------|---------|
| `QDRANT_URL` | Qdrant instance HTTP URL | `http://localhost:6333` |

### Event Streaming (Kafka)

| Variable | Description | Default |
|----------|-------------|---------|
| `KAFKA_BOOTSTRAP_SERVERS` | Comma-separated Kafka broker list | `localhost:9092` |

---

## Optional Variables

### LLM Providers (Extended)

| Variable | Description |
|----------|-------------|
| `GOOGLE_API_KEY` | Google Gemini API key for Kalibr router |

### NANDA Agent SDK

| Variable | Description | Default |
|----------|-------------|---------|
| `NANDA_AGENT_ID` | Identifier for this platform's NANDA agent | — |
| `NANDA_REGISTRY_URL` | NANDA registry endpoint | `chat.nanda-registry.com` |
| `SMITHERY_KEY` | Smithery integration key (optional) | — |

### Qdrant Cloud

| Variable | Description | Default |
|----------|-------------|---------|
| `QDRANT_API_KEY` | API key for Qdrant Cloud deployments | — |
| `QDRANT_GRPC` | Use gRPC instead of HTTP | `False` |

### AlphaFold3

| Variable | Description |
|----------|-------------|
| `ALPHAFOLD3_ENDPOINT` | AlphaFold3 API endpoint URL |
| `ALPHAFOLD3_API_KEY` | Authentication key for AlphaFold3 service |

### Blockchain / DeSci

| Variable | Description | Example |
|----------|-------------|---------|
| `ETHEREUM_NETWORK` | Target network | `mainnet`, `sepolia` |
| `ETHEREUM_RPC_URL` | JSON-RPC endpoint | `https://mainnet.infura.io/v3/...` |
| `PRIVATE_KEY` | Wallet private key for IP-NFT minting | `0x...` (never commit) |
| `CONTRACT_ADDRESS` | IP-NFT smart contract address | `0x...` |

> ⚠️ **Security warning**: Never commit `PRIVATE_KEY` to source control. Use a secrets manager in production.

---

## Programmatic Configuration

Some components accept configuration via Python dataclasses rather than environment variables.

### `NANDAAgentConfig`

```python
from src.integrations.nanda_agent_integration import NANDAAgentConfig

config = NANDAAgentConfig(
    anthropic_key="sk-ant-...",          # required
    domain="genomic.agicorp.network",    # default
    registry_url="chat.nanda-registry.com",  # default
    port_start=8000,                     # default, incremented per agent
    smithery_key=None                    # optional
)
```

---

## Qdrant Collection Configuration

These values are baked into `init_compound_library.py`. To change them, modify the source before running initialization.

| Parameter | Value | Notes |
|-----------|-------|-------|
| Collection name | `compound_library` | `CompoundSearcher` default |
| Vector size | 384 | Fixed to `all-MiniLM-L6-v2` output |
| Distance metric | COSINE | |
| HNSW m | 16 | Edge count per node |
| HNSW ef_construct | 100 | Index build quality |
| Quantization | INT8 scalar | Memory reduction |
| On-disk storage | enabled | Supports large datasets |

---

## Kafka Configuration

| Topic | Direction | Default |
|-------|-----------|---------|
| `trial-allocations` | Write | Hardcoded in `AdaptiveTrialDesign` |
| `trial-alerts` | Write | Hardcoded in `SafetyMonitoringSystem` |
| `adverse-events` | Read | Hardcoded in `SafetyMonitoringSystem` |

Topic names can be updated in the respective class constructors.

---

## Safety Monitoring Thresholds

`SafetyMonitoringSystem` constructor parameters (not environment variables):

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `safety_threshold` | `float` | `0.15` | Max acceptable 7-day AE rate |

---

## Example `.env` File

```bash
# === LLM Providers (required) ===
ANTHROPIC_API_KEY=sk-ant-api03-REPLACE_ME
OPENAI_API_KEY=sk-proj-REPLACE_ME
GOOGLE_API_KEY=AIza-REPLACE_ME

# === Vector DB (required) ===
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=

# === Kafka (required) ===
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# === NANDA SDK ===
NANDA_AGENT_ID=genomic-platform-01
NANDA_REGISTRY_URL=chat.nanda-registry.com
SMITHERY_KEY=

# === AlphaFold3 ===
ALPHAFOLD3_ENDPOINT=https://alphafold3.api.example.com
ALPHAFOLD3_API_KEY=

# === Blockchain / DeSci ===
ETHEREUM_NETWORK=sepolia
ETHEREUM_RPC_URL=https://sepolia.infura.io/v3/REPLACE_ME
PRIVATE_KEY=0xREPLACE_ME
CONTRACT_ADDRESS=0xREPLACE_ME
```

---

_Next: [Security](Security.md) | [Deployment](Deployment.md)_
