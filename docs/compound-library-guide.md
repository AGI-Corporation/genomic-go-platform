# Compound Library Semantic Search Guide

## Overview

The Genomic.go Platform integrates **Qdrant vector database** for semantic search across drug compound libraries, enabling similarity-based compound discovery and intelligent filtering.

This integration is based on the [qdrant_demo](https://github.com/AGI-Corporation/qdrant_demo) implementation, adapted for pharmaceutical compound screening.

## Features

### 🔍 Semantic Search
- Natural language queries for compound discovery
- "Find kinase inhibitors for cancer treatment"
- "EGFR targeting compounds with low molecular weight"
- Similarity-based compound recommendations

### 🎯 Advanced Filtering
- **Molecular Weight Range**: Filter by compound size
- **Target Protein**: Search by biological target (e.g., "BCR-ABL", "EGFR")
- **Mechanism of Action**: Filter by mechanism (e.g., "kinase inhibitor")
- **Therapeutic Area**: Find compounds by indication (e.g., "oncology")
- **Clinical Phase**: Filter by development stage

### ⚡ Performance
- **ScalarQuantization**: Reduced memory usage with INT8 quantization
- **HNSW Indexing**: Fast approximate nearest neighbor search
- **Parallel Upload**: Multi-threaded compound ingestion
- **On-Disk Vectors**: Scalable storage for large libraries

## Installation

### 1. Install Dependencies

```bash
pip install qdrant-client sentence-transformers tqdm
```

### 2. Set Up Qdrant

**Option A: Docker (Recommended)**
```bash
docker run -p 6333:6333 -p 6334:6334 \
    -v $(pwd)/qdrant_storage:/qdrant/storage:z \
    qdrant/qdrant
```

**Option B: Qdrant Cloud**
```bash
export QDRANT_URL="https://your-cluster.qdrant.io"
export QDRANT_API_KEY="your-api-key"
```

### 3. Prepare Compound Data

Create `data/compounds.json` with compound information (one JSON object per line):

```json
{"compound_id": "CHEMBL12345", "name": "Imatinib", "description": "Tyrosine kinase inhibitor for chronic myeloid leukemia", "molecular_weight": 493.6, "smiles": "CC1=C(C=C(C=C1)NC(=O)C2=CC=C(C=C2)CN3CCN(CC3)C)NC4=NC=CC(=N4)C5=CN=CC=C5", "target_protein": "BCR-ABL", "mechanism": "Tyrosine kinase inhibitor", "therapeutic_area": "Oncology", "clinical_phase": "Approved", "indications": ["CML", "GIST"]}
{"compound_id": "CHEMBL67890", "name": "Gefitinib", "description": "EGFR tyrosine kinase inhibitor for NSCLC", "molecular_weight": 446.9, "smiles": "COC1=C(C=C2C(=C1)C(=NC=N2)NC3=CC(=C(C=C3)F)Cl)OCCCN4CCOCC4", "target_protein": "EGFR", "mechanism": "EGFR inhibitor", "therapeutic_area": "Oncology", "clinical_phase": "Approved", "indications": ["NSCLC"]}
```

### 4. Initialize Compound Library

```bash
python -m src.compound_library.init_compound_library
```

This will:
1. Create a Qdrant collection named `compound_library`
2. Generate embeddings using `sentence-transformers/all-MiniLM-L6-v2`
3. Create indexes for filterable fields
4. Upload all compounds with progress tracking

## Usage Examples

### Basic Semantic Search

```python
from src.compound_library.compound_searcher import CompoundSearcher

# Initialize searcher
searcher = CompoundSearcher(
    collection_name="compound_library",
    qdrant_url="http://localhost:6333"
)

# Search for compounds
results = searcher.search(
    query="EGFR inhibitor for lung cancer",
    limit=5
)

for compound in results:
    print(f"{compound['name']}: {compound['description']}")
    print(f"  Target: {compound['target_protein']}")
    print(f"  Similarity: {compound['similarity_score']:.3f}")
    print()
```

### Filtered Search

```python
# Find low molecular weight kinase inhibitors for oncology
results = searcher.search(
    query="kinase inhibitor",
    filters={
        "molecular_weight_range": [200, 500],
        "therapeutic_area": "Oncology",
        "clinical_phase": "Approved"
    },
    limit=10
)
```

### Find Similar Compounds

```python
# Find compounds similar to Imatinib
similar = searcher.find_similar_compounds(
    compound_id="CHEMBL12345",
    limit=10
)

for compound in similar:
    print(f"{compound['name']} (similarity: {compound['similarity_score']:.3f})")
```

### Collection Statistics

```python
stats = searcher.get_collection_stats()
print(f"Total compounds: {stats['total_compounds']}")
print(f"Vector size: {stats['vector_size']}")
print(f"Distance metric: {stats['distance_metric']}")
```

## Integration with Research Pipelines

### Example: Drug Discovery Workflow

```python
from genomic_platform import ResearchPipeline
from src.compound_library.compound_searcher import CompoundSearcher

# Initialize pipeline and compound searcher
pipeline = ResearchPipeline(domain="drug_discovery")
compound_searcher = CompoundSearcher(
    collection_name="compound_library",
    qdrant_url="http://localhost:6333"
)

# Find target protein
target_query = "Find overexpressed proteins in colorectal cancer"
targets = pipeline.execute(target_query, agents=10)

# Search for relevant compounds
for target in targets['proteins']:
    compounds = compound_searcher.search(
        query=f"inhibitor for {target['name']}",
        filters={"therapeutic_area": "Oncology"},
        limit=5
    )
    
    print(f"\nTop compounds for {target['name']}:")
    for compound in compounds:
        print(f"  - {compound['name']}: {compound['description']}")
```

## Performance Tuning

### Adjust HNSW Parameters

For faster search with slightly lower accuracy:

```python
hnsw_config=models.HnswConfigDiff(
    m=8,  # Lower m = faster, less accurate
    ef_construct=50  # Lower ef = faster indexing
)
```

For higher accuracy:

```python
hnsw_config=models.HnswConfigDiff(
    m=32,  # Higher m = more accurate, slower
    ef_construct=200  # Higher ef = better quality
)
```

### Batch Size and Parallelism

Adjust upload parameters in `init_compound_library.py`:

```python
client.upload_points(
    collection_name=collection_name,
    points=tqdm(read_compounds()),
    parallel=8,  # More threads for faster upload
    batch_size=32  # Larger batches
)
```

## Data Sources

### ChEMBL Database
Download compound data from [ChEMBL](https://www.ebi.ac.uk/chembl/):
```bash
wget https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/latest/chembl_32_sqlite.tar.gz
```

### PubChem
Query PubChem API for compound information:
```python
import requests

response = requests.get(
    "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/imatinib/JSON"
)
compound_data = response.json()
```

### DrugBank
Access [DrugBank](https://go.drugbank.com/) for approved and investigational compounds.

## Troubleshooting

### Connection Issues
```python
# Verify Qdrant is running
import requests
response = requests.get("http://localhost:6333/collections")
print(response.json())
```

### Embedding Model Issues
```python
# Test embeddings
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
embedding = model.encode("test query")
print(f"Embedding size: {len(embedding)}")
```

### Memory Issues
If running out of memory, enable more aggressive quantization:
```python
quantization_config=models.ScalarQuantization(
    scalar=models.ScalarQuantizationConfig(
        type=models.ScalarType.INT8,
        quantile=0.95,  # More aggressive
        always_ram=False  # Store on disk
    )
)
```

## Next Steps

- [Getting Started Guide](./getting-started.md)
- [API Reference](./api-reference.md)
- [Research Pipeline Integration](./pipeline-integration.md)
- [Qdrant Documentation](https://qdrant.tech/documentation/)

## Credits

This implementation is based on the [qdrant_demo](https://github.com/qdrant/qdrant_demo) by Qdrant, adapted for pharmaceutical compound screening in the Genomic.go Platform.

---

**Need help?** Contact research@agicorp.eth or open an issue on [GitHub](https://github.com/AGI-Corporation/genomic-go-platform/issues).
