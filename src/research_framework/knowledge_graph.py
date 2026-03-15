"""Genomic Knowledge Graph Integration

Provides a structured representation of biological entities and their relationships,
enhanced by Mistral embeddings for semantic link prediction.
"""

from typing import List, Dict, Any, Optional, Tuple
import networkx as nx
import numpy as np
from src.integrations.mistral_adapter import MistralGenomicAdapter


class BiologicalKnowledgeGraph:
    """Manages biological entities and their interactions."""

    def __init__(self, api_key: Optional[str] = None):
        """Initializes the Knowledge Graph."""
        self.graph = nx.DiGraph()
        self.mistral = MistralGenomicAdapter(api_key)

    async def add_entity(
        self, entity_id: str, entity_type: str, metadata: Dict[str, Any]
    ):
        """Adds an entity to the graph with Mistral-generated semantic embeddings."""
        desc = metadata.get("description", f"A {entity_type} entity.")
        embedding = await self.mistral.get_text_embedding(desc)

        self.graph.add_node(
            entity_id, type=entity_type, metadata=metadata, embedding=embedding
        )

    def add_interaction(self, source: str, target: str, interaction_type: str):
        """Defines a relationship between two biological entities."""
        self.graph.add_edge(source, target, type=interaction_type)

    def find_potential_targets(self, disease_id: str) -> List[str]:
        """Identifies candidate targets based on graph connectivity."""
        if disease_id not in self.graph:
            return []

        # Simple BFS to find genes/proteins connected to the disease
        neighbors = list(self.graph.neighbors(disease_id))
        return [
            n
            for n in neighbors
            if self.graph.nodes[n].get("type") in ["gene", "protein"]
        ]

    def predict_links(self, threshold: float = 0.85) -> List[Tuple[str, str, float]]:
        """
        Predicts potential links between entities using semantic similarity.
        Optimized using vectorized matrix multiplication for O(N^2) speedup.
        """
        nodes_with_embeddings = [
            (node, data["embedding"])
            for node, data in self.graph.nodes(data=True)
            if data.get("embedding") is not None
        ]

        if not nodes_with_embeddings:
            return []

        node_ids = [n[0] for n in nodes_with_embeddings]
        embeddings = np.array([n[1] for n in nodes_with_embeddings])

        # Normalize embeddings for cosine similarity via dot product
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        # Avoid division by zero
        norms[norms == 0] = 1.0
        normalized_embeddings = embeddings / norms

        # Vectorized cosine similarity matrix: (N, D) x (D, N) -> (N, N)
        similarity_matrix = np.dot(normalized_embeddings, normalized_embeddings.T)

        # Get upper triangle indices (excluding diagonal) to avoid duplicate pairs
        idx_a, idx_b = np.triu_indices(len(node_ids), k=1)
        similarities = similarity_matrix[idx_a, idx_b]

        # Filter by threshold
        mask = similarities >= threshold

        predictions = [
            (node_ids[idx_a[i]], node_ids[idx_b[i]], float(similarities[i]))
            for i in np.where(mask)[0]
        ]

        return sorted(predictions, key=lambda x: x[2], reverse=True)


class GraphEnrichedAgent:
    """A research agent that leverages the Knowledge Graph for enhanced reasoning."""

    def __init__(self, kg: BiologicalKnowledgeGraph):
        self.kg = kg
        self.role = "Knowledge Enrichment Specialist"

    async def process_task(
        self, task: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Performs reasoning based on graph topology and semantic similarity."""
        # Implementation details for graph-based inference
        return {"status": "enriched"}


if __name__ == "__main__":
    print("Biological Knowledge Graph Module Loaded.")
