"""Genomic.go Platform - Single-Cell RNA-seq Agent.

Cell clustering, UMAP dimensionality reduction, and trajectory
(pseudotime) inference using scikit-learn.
"""

import logging
from typing import Any, Dict, List, Optional

import numpy as np
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE

from src.agents.base import AgentStatus, GenomicAgent

logger = logging.getLogger(__name__)


class SingleCellAgent(GenomicAgent):
    """Agent for single-cell RNA-seq analysis.

    Provides cell clustering, UMAP-equivalent dimensionality reduction
    (via PCA + t-SNE), and simple pseudotime trajectory inference.

    Args:
        agent_id: Optional unique identifier.
        redis_url: Optional Redis URL for memory persistence.
    """

    def __init__(
        self,
        agent_id: Optional[str] = None,
        redis_url: Optional[str] = None,
    ) -> None:
        super().__init__(
            name="SingleCellAgent",
            agent_id=agent_id,
            redis_url=redis_url,
        )

    async def initialize(self) -> None:
        """Initialise the single-cell agent."""
        self.logger.info("SingleCellAgent initialised")

    async def start(self) -> None:
        """Start the single-cell agent."""
        self.logger.info("SingleCellAgent started")

    async def stop(self) -> None:
        """Stop the single-cell agent."""
        self._status = AgentStatus.STOPPED
        self.logger.info("SingleCellAgent stopped")

    async def health_check(self) -> bool:
        """Return True — no external dependencies required."""
        return True

    async def _execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Cluster cells from an expression matrix.

        Args:
            input_data: Must contain ``expression_matrix``
                        (list-of-lists, cells × genes) and optionally
                        ``n_clusters`` (int, default 10).

        Returns:
            Clustering result dictionary.
        """
        matrix = input_data.get("expression_matrix", [])
        n_clusters = int(input_data.get("n_clusters", 10))
        return self.cluster_cells(matrix, n_clusters)

    # ------------------------------------------------------------------
    # Public domain methods
    # ------------------------------------------------------------------

    def cluster_cells(
        self,
        expression_matrix: List[List[float]],
        n_clusters: int = 10,
    ) -> Dict[str, Any]:
        """Cluster cells using KMeans on the expression matrix.

        Args:
            expression_matrix: 2-D list (cells × genes) of expression
                               values.
            n_clusters: Number of clusters (default 10).

        Returns:
            Dictionary with ``cluster_labels`` and ``cluster_counts``.
        """
        if not expression_matrix:
            return {"cluster_labels": [], "cluster_counts": {}}

        X = np.array(expression_matrix, dtype=float)
        n_cells = X.shape[0]
        k = min(n_clusters, n_cells)

        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(X).tolist()

        cluster_counts: Dict[str, int] = {}
        for label in labels:
            cluster_counts[str(label)] = cluster_counts.get(str(label), 0) + 1

        self.logger.info("cluster_cells: %d cells → %d clusters", n_cells, k)
        return {
            "cluster_labels": labels,
            "cluster_counts": cluster_counts,
            "n_clusters": k,
            "n_cells": n_cells,
        }

    def compute_umap_embeddings(
        self,
        expression_matrix: List[List[float]],
        n_components: int = 2,
    ) -> Dict[str, Any]:
        """Compute low-dimensional embeddings via PCA + t-SNE.

        Full UMAP requires the ``umap-learn`` package.  This method uses
        PCA for initial dimensionality reduction followed by t-SNE.

        Args:
            expression_matrix: 2-D list (cells × genes).
            n_components: Number of output dimensions (default 2).

        Returns:
            Dictionary with ``embeddings`` (list of coordinate lists)
            and ``method`` used.
        """
        if not expression_matrix:
            return {"embeddings": [], "method": "pca+tsne"}

        X = np.array(expression_matrix, dtype=float)
        n_cells, n_genes = X.shape

        n_pca = min(50, n_genes, n_cells - 1)
        if n_pca < 2:
            embeddings = X[:, :n_components].tolist()
            return {"embeddings": embeddings, "method": "raw_slice"}

        pca = PCA(n_components=n_pca, random_state=42)
        X_pca = pca.fit_transform(X)

        perplexity = min(30, max(5, n_cells // 4))
        tsne = TSNE(
            n_components=n_components,
            perplexity=perplexity,
            random_state=42,
        )
        embeddings = tsne.fit_transform(X_pca).tolist()

        self.logger.info(
            "compute_umap_embeddings: %d cells, %d dims", n_cells, n_components
        )
        return {"embeddings": embeddings, "method": "pca+tsne", "n_cells": n_cells}

    def infer_trajectory(
        self,
        cell_embeddings: List[List[float]],
        start_cell: int,
    ) -> Dict[str, Any]:
        """Infer a simple pseudotime trajectory from cell embeddings.

        Orders cells by their Euclidean distance from a designated start
        cell, providing a naive pseudotime estimate.

        Args:
            cell_embeddings: 2-D list (cells × embedding dims).
            start_cell: Index of the root cell.

        Returns:
            Dictionary with ``pseudotime`` list and ``ordering`` (cell
            indices sorted by pseudotime).
        """
        if not cell_embeddings:
            return {"pseudotime": [], "ordering": []}

        X = np.array(cell_embeddings, dtype=float)
        n_cells = X.shape[0]
        start = min(start_cell, n_cells - 1)
        origin = X[start]
        distances = np.linalg.norm(X - origin, axis=1).tolist()
        ordering = sorted(range(n_cells), key=lambda i: distances[i])

        self.logger.info(
            "infer_trajectory: %d cells, start=%d", n_cells, start
        )
        return {
            "pseudotime": [round(d, 4) for d in distances],
            "ordering": ordering,
            "start_cell": start,
        }
