"""Compound Library Semantic Search Module

This module provides semantic search capabilities for drug compounds using Qdrant vector database.
Integrated from qdrant_demo for the Genomic.go Platform.

Key Features:
- Semantic search across compound descriptions
- Similarity-based compound discovery  
- Filter by compound properties (molecular weight, targets, mechanisms)
- Fast vector-based retrieval with ScalarQuantization
"""

import time
from typing import List, Optional, Dict
from qdrant_client import QdrantClient, models


class CompoundSearcher:
    """Semantic search engine for drug compounds using Qdrant vector database.
    
    This searcher enables researchers to find similar compounds based on:
    - Chemical descriptions
    - Mechanism of action
    - Biological targets
    - Therapeutic applications
    
    Attributes:
        collection_name (str): Name of the Qdrant collection storing compounds
        qdrant_client (QdrantClient): Client connection to Qdrant vector DB
        embeddings_model (str): Model used for text embeddings
    """
    
    def __init__(
        self,
        collection_name: str,
        qdrant_url: str,
        qdrant_api_key: Optional[str] = None,
        embeddings_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    ):
        """Initialize the compound searcher.
        
        Args:
            collection_name: Name of the Qdrant collection
            qdrant_url: URL to Qdrant instance
            qdrant_api_key: Optional API key for Qdrant Cloud
            embeddings_model: Model for generating embeddings
        """
        self.collection_name = collection_name
        self.embeddings_model = embeddings_model
        self.qdrant_client = QdrantClient(
            url=qdrant_url,
            api_key=qdrant_api_key,
            prefer_grpc=True
        )
        self.qdrant_client.set_model(embeddings_model)
    
    def search(
        self,
        query: str,
        filters: Optional[Dict] = None,
        limit: int = 10
    ) -> List[Dict]:
        """Perform semantic search for compounds.
        
        Args:
            query: Natural language query describing desired compounds
            filters: Optional filters for compound properties:
                - molecular_weight_range: [min, max]
                - target_protein: str
                - mechanism: str
                - therapeutic_area: str
            limit: Maximum number of results to return
        
        Returns:
            List of compound dictionaries with metadata and similarity scores
            
        Example:
            >>> searcher = CompoundSearcher("compounds", "http://localhost:6333")
            >>> results = searcher.search(
            ...     "kinase inhibitor for cancer",
            ...     filters={"therapeutic_area": "oncology"},
            ...     limit=5
            ... )
        """
        start_time = time.time()
        
        # Build Qdrant filter from provided filters
        query_filter = None
        if filters:
            query_filter = self._build_filter(filters)
        
        # Execute semantic search
        hits = self.qdrant_client.query_points(
            collection_name=self.collection_name,
            query=models.Document(
                text=query,
                model=self.embeddings_model,
            ),
            query_filter=query_filter,
            limit=limit,
            with_payload=True
        )
        
        search_time = time.time() - start_time
        print(f"Compound search took {search_time:.3f} seconds")
        print(f"Found {len(hits.points)} compounds")
        
        # Return compound data with scores
        results = []
        for hit in hits.points:
            compound = hit.payload.copy()
            compound['similarity_score'] = hit.score if hasattr(hit, 'score') else None
            results.append(compound)
        
        return results
    
    def _build_filter(self, filters: Dict) -> models.Filter:
        """Build Qdrant filter conditions from filter dictionary.
        
        Args:
            filters: Dictionary of filter conditions
            
        Returns:
            Qdrant Filter object
        """
        conditions = []
        
        # Molecular weight range filter
        if "molecular_weight_range" in filters:
            min_mw, max_mw = filters["molecular_weight_range"]
            conditions.append(
                models.FieldCondition(
                    key="molecular_weight",
                    range=models.Range(gte=min_mw, lte=max_mw)
                )
            )
        
        # Target protein filter
        if "target_protein" in filters:
            conditions.append(
                models.FieldCondition(
                    key="target_protein",
                    match=models.MatchValue(value=filters["target_protein"])
                )
            )
        
        # Mechanism of action filter
        if "mechanism" in filters:
            conditions.append(
                models.FieldCondition(
                    key="mechanism",
                    match=models.MatchValue(value=filters["mechanism"])
                )
            )
        
        # Therapeutic area filter
        if "therapeutic_area" in filters:
            conditions.append(
                models.FieldCondition(
                    key="therapeutic_area",
                    match=models.MatchValue(value=filters["therapeutic_area"])
                )
            )
        
        return models.Filter(must=conditions) if conditions else None
    
    def find_similar_compounds(
        self,
        compound_id: str,
        limit: int = 10
    ) -> List[Dict]:
        """Find compounds similar to a given compound.
        
        Args:
            compound_id: ID of the reference compound
            limit: Maximum number of similar compounds to return
            
        Returns:
            List of similar compound dictionaries
        """
        # Retrieve the reference compound vector
        reference = self.qdrant_client.retrieve(
            collection_name=self.collection_name,
            ids=[compound_id],
            with_vectors=True
        )
        
        if not reference:
            raise ValueError(f"Compound {compound_id} not found")
        
        # Search using the compound's vector
        hits = self.qdrant_client.search(
            collection_name=self.collection_name,
            query_vector=reference[0].vector,
            limit=limit + 1,  # +1 to exclude the compound itself
            with_payload=True
        )
        
        # Filter out the reference compound and return results
        results = []
        for hit in hits:
            if hit.id != compound_id:
                compound = hit.payload.copy()
                compound['similarity_score'] = hit.score
                results.append(compound)
        
        return results[:limit]
    
    def get_collection_stats(self) -> Dict:
        """Get statistics about the compound library.
        
        Returns:
            Dictionary with collection statistics
        """
        collection_info = self.qdrant_client.get_collection(
            collection_name=self.collection_name
        )
        
        return {
            "total_compounds": collection_info.points_count,
            "vector_size": collection_info.config.params.vectors.size,
            "distance_metric": collection_info.config.params.vectors.distance,
            "status": collection_info.status
        }
