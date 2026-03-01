"""Initialize Compound Library in Qdrant Vector Database

This script creates and populates a Qdrant collection with drug compound data,
enabling semantic search capabilities for compound discovery.

Based on qdrant_demo implementation, adapted for pharmaceutical compounds.
"""

import json
import os
from typing import Iterable, List, Dict
from qdrant_client import QdrantClient, models
from tqdm import tqdm

# Configuration
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = "compound_library"
EMBEDDINGS_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DATA_PATH = "data/compounds.json"


def read_compounds() -> Iterable[models.PointStruct]:
    """Read compound data and yield Qdrant points.

    Expected JSON format:
    {
        "compound_id": "CHEMBL12345",
        "name": "Imatinib",
        "description": "Tyrosine kinase inhibitor used for CML",
        "molecular_weight": 493.6,
        "smiles": "...",
        "target_protein": "BCR-ABL",
        "mechanism": "Kinase inhibitor",
        "therapeutic_area": "Oncology",
        "clinical_phase": "Approved",
        "indications": ["CML", "GIST"]
    }
    """
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(
            f"Compound data file not found: {DATA_PATH}\n"
            "Please add compounds.json to the data/ directory."
        )

    with open(DATA_PATH) as fd:
        for idx, line in enumerate(fd):
            compound = json.loads(line)

            # Create searchable text from compound data
            search_text = (
                f"{compound.get('name', '')} {compound.get('description', '')} "
            )
            search_text += f"{compound.get('mechanism', '')} {compound.get('therapeutic_area', '')}"

            # Create Qdrant point with embedding
            yield models.PointStruct(
                id=compound.get("compound_id", f"compound_{idx}"),
                vector=models.Document(
                    text=search_text,
                    model=EMBEDDINGS_MODEL,
                ),
                payload=compound,
            )


def create_compound_collection(
    client: QdrantClient, collection_name: str = COLLECTION_NAME
) -> None:
    """Create Qdrant collection optimized for compound search."""

    # Delete existing collection if present
    if client.collection_exists(collection_name):
        print(f"Collection {collection_name} already exists. Deleting...")
        client.delete_collection(collection_name)

    # Get embedding size
    embedding_size = client.get_embedding_size(EMBEDDINGS_MODEL)

    # Create collection with optimized settings
    client.create_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(
            size=embedding_size,
            distance=models.Distance.COSINE,
            on_disk=True,  # Store vectors on disk for large libraries
        ),
        # Enable scalar quantization for memory efficiency
        quantization_config=models.ScalarQuantization(
            scalar=models.ScalarQuantizationConfig(
                type=models.ScalarType.INT8, quantile=0.99, always_ram=True
            )
        ),
        # Enable HNSW indexing for fast approximate search
        hnsw_config=models.HnswConfigDiff(
            m=16,  # Number of edges per node
            ef_construct=100,  # Construction time parameter
        ),
    )

    print(f"Created collection: {collection_name}")


def create_payload_indexes(
    client: QdrantClient, collection_name: str = COLLECTION_NAME
) -> None:
    """Create indexes for filterable compound properties."""

    # Index for text search on description
    client.create_payload_index(
        collection_name=collection_name,
        field_name="description",
        field_schema=models.TextIndexParams(
            type=models.TextIndexType.TEXT,
            tokenizer=models.TokenizerType.WORD,
            min_token_len=2,
            max_token_len=20,
            lowercase=True,
        ),
    )
    print("Created text index on description")

    # Index for filtering by target protein
    client.create_payload_index(
        collection_name=collection_name,
        field_name="target_protein",
        field_schema=models.KeywordIndexParams(type=models.KeywordIndexType.KEYWORD),
    )
    print("Created keyword index on target_protein")

    # Index for filtering by therapeutic area
    client.create_payload_index(
        collection_name=collection_name,
        field_name="therapeutic_area",
        field_schema=models.KeywordIndexParams(type=models.KeywordIndexType.KEYWORD),
    )
    print("Created keyword index on therapeutic_area")

    # Index for filtering by clinical phase
    client.create_payload_index(
        collection_name=collection_name,
        field_name="clinical_phase",
        field_schema=models.KeywordIndexParams(type=models.KeywordIndexType.KEYWORD),
    )
    print("Created keyword index on clinical_phase")

    # Index for molecular weight filtering
    client.create_payload_index(
        collection_name=collection_name,
        field_name="molecular_weight",
        field_schema=models.IntegerIndexParams(type=models.IntegerIndexType.INTEGER),
    )
    print("Created integer index on molecular_weight")


def upload_compounds(
    client: QdrantClient, collection_name: str = COLLECTION_NAME
) -> None:
    """Upload compound data to Qdrant collection."""

    print(f"Uploading compounds to {collection_name}...")

    # Upload points with progress bar
    client.upload_points(
        collection_name=collection_name,
        points=tqdm(read_compounds(), desc="Uploading compounds"),
        parallel=4,  # Parallel upload for speed
        batch_size=16,
    )

    # Get collection info
    collection_info = client.get_collection(collection_name)
    print(f"\nSuccessfully uploaded {collection_info.points_count} compounds")


def main():
    """Main initialization workflow."""

    print("=" * 60)
    print("Initializing Compound Library for Genomic.go Platform")
    print("=" * 60)

    # Connect to Qdrant
    client = QdrantClient(
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY,
        prefer_grpc=True,
    )
    client.set_model(EMBEDDINGS_MODEL)
    print(f"Connected to Qdrant at {QDRANT_URL}")

    # Create collection
    create_compound_collection(client)

    # Create indexes
    create_payload_indexes(client)

    # Upload compounds
    upload_compounds(client)

    print("\n" + "=" * 60)
    print("Compound library initialized successfully!")
    print("=" * 60)
    print(f"\nCollection: {COLLECTION_NAME}")
    print(f"Embeddings Model: {EMBEDDINGS_MODEL}")
    print(f"Qdrant URL: {QDRANT_URL}")
    print("\nYou can now use CompoundSearcher to query the library.")


if __name__ == "__main__":
    main()
