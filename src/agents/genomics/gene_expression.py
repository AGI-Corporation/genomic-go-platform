"""Genomic.go Platform - Gene Expression Agent.

RNA-seq analysis, differential expression, and count normalisation
using NumPy and pandas.
"""

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from src.agents.base import AgentStatus, GenomicAgent

logger = logging.getLogger(__name__)


class GeneExpressionAgent(GenomicAgent):
    """Agent for RNA-seq gene expression analysis.

    Performs differential expression analysis, TPM normalisation, and
    log2 fold-change computation from count matrices.

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
            name="GeneExpressionAgent",
            agent_id=agent_id,
            redis_url=redis_url,
        )

    async def initialize(self) -> None:
        """Initialise the gene expression agent."""
        self.logger.info("GeneExpressionAgent initialised")

    async def start(self) -> None:
        """Start the gene expression agent."""
        self.logger.info("GeneExpressionAgent started")

    async def stop(self) -> None:
        """Stop the gene expression agent."""
        self._status = AgentStatus.STOPPED
        self.logger.info("GeneExpressionAgent stopped")

    async def health_check(self) -> bool:
        """Return True — no external dependencies required."""
        return True

    async def _execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run differential expression analysis.

        Args:
            input_data: Must contain ``count_matrix`` (dict) and
                        ``conditions`` (list of condition labels).

        Returns:
            Differential expression results.
        """
        count_matrix = input_data.get("count_matrix", {})
        conditions = input_data.get("conditions", [])
        return self.analyze_rnaseq(count_matrix, conditions)

    # ------------------------------------------------------------------
    # Public domain methods
    # ------------------------------------------------------------------

    def analyze_rnaseq(
        self,
        count_matrix: Dict[str, List[float]],
        conditions: List[str],
    ) -> Dict[str, Any]:
        """Perform differential expression analysis on raw counts.

        Args:
            count_matrix: Dict mapping gene names to lists of raw read
                          counts (one count per sample).
            conditions: List of condition labels corresponding to each
                        sample column (e.g. ``["ctrl", "ctrl", "trt", "trt"]``).

        Returns:
            Dictionary with ``normalised_counts``, ``fold_changes``,
            and ``de_genes`` (differentially expressed genes).
        """
        if not count_matrix or not conditions:
            return {"normalised_counts": {}, "fold_changes": {}, "de_genes": []}

        df = pd.DataFrame(count_matrix).T
        df.columns = [f"sample_{i}" for i in range(df.shape[1])]

        normalised = self.normalize_counts(count_matrix, method="tpm")
        unique_conditions = list(dict.fromkeys(conditions))

        if len(unique_conditions) < 2:
            return {
                "normalised_counts": normalised,
                "fold_changes": {},
                "de_genes": [],
            }

        ctrl_label = unique_conditions[0]
        trt_label = unique_conditions[1]
        ctrl_cols = [i for i, c in enumerate(conditions) if c == ctrl_label]
        trt_cols = [i for i, c in enumerate(conditions) if c == trt_label]

        control: Dict[str, float] = {}
        treatment: Dict[str, float] = {}
        for gene, counts in count_matrix.items():
            counts_arr = np.array(counts, dtype=float)
            control[gene] = float(np.mean(counts_arr[ctrl_cols]))
            treatment[gene] = float(np.mean(counts_arr[trt_cols]))

        fold_changes = self.compute_fold_changes(control, treatment)
        de_genes = [g for g, fc in fold_changes.items() if abs(fc) >= 1.0]

        self.logger.info(
            "analyze_rnaseq: %d genes, %d DE genes", len(count_matrix), len(de_genes)
        )
        return {
            "normalised_counts": normalised,
            "fold_changes": fold_changes,
            "de_genes": de_genes,
            "conditions": {"control": ctrl_label, "treatment": trt_label},
        }

    def normalize_counts(
        self,
        count_matrix: Dict[str, List[float]],
        method: str = "tpm",
    ) -> Dict[str, List[float]]:
        """Normalise raw read counts per gene.

        Args:
            count_matrix: Dict mapping gene names to raw count lists.
            method: Normalisation method — ``"tpm"`` (transcripts per
                    million) or ``"cpm"`` (counts per million).

        Returns:
            Normalised count matrix with the same structure as input.
        """
        if not count_matrix:
            return {}

        genes = list(count_matrix.keys())
        matrix = np.array([count_matrix[g] for g in genes], dtype=float)
        n_samples = matrix.shape[1]
        normalised = np.zeros_like(matrix)

        for s in range(n_samples):
            col = matrix[:, s]
            total = col.sum()
            if total == 0:
                continue
            if method == "tpm":
                rpk = col / (1.0 + col) * 1e3
                scale = rpk.sum() / 1e6
                normalised[:, s] = rpk / scale if scale > 0 else rpk
            else:  # cpm
                normalised[:, s] = col / total * 1e6

        return {genes[i]: normalised[i].tolist() for i in range(len(genes))}

    def compute_fold_changes(
        self,
        control: Dict[str, float],
        treatment: Dict[str, float],
    ) -> Dict[str, float]:
        """Compute log2 fold changes between treatment and control.

        Args:
            control: Dict mapping gene name to mean control expression.
            treatment: Dict mapping gene name to mean treatment expression.

        Returns:
            Dict mapping gene name to log2 fold change.  Genes with zero
            control expression receive a pseudo-count of 1.
        """
        fold_changes: Dict[str, float] = {}
        for gene in control:
            ctrl_val = max(control.get(gene, 0.0), 1.0)
            trt_val = max(treatment.get(gene, 0.0), 1.0)
            fold_changes[gene] = round(float(np.log2(trt_val / ctrl_val)), 4)
        self.logger.debug("compute_fold_changes: %d genes", len(fold_changes))
        return fold_changes
