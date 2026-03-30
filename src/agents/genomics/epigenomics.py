"""Genomic.go Platform - Epigenomics Agent.

Methylation analysis, differentially methylated region (DMR) detection,
and ATAC-seq chromatin accessibility assessment.
"""

import logging
from typing import Any, Dict, List, Optional

import numpy as np

from src.agents.base import AgentStatus, GenomicAgent

logger = logging.getLogger(__name__)


class EpigenomicsAgent(GenomicAgent):
    """Agent for epigenomics data analysis.

    Processes DNA methylation arrays and ATAC-seq data to identify
    epigenetic alterations associated with biological conditions.

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
            name="EpigenomicsAgent",
            agent_id=agent_id,
            redis_url=redis_url,
        )

    async def initialize(self) -> None:
        """Initialise the epigenomics agent."""
        self.logger.info("EpigenomicsAgent initialised")

    async def start(self) -> None:
        """Start the epigenomics agent."""
        self.logger.info("EpigenomicsAgent started")

    async def stop(self) -> None:
        """Stop the epigenomics agent."""
        self._status = AgentStatus.STOPPED
        self.logger.info("EpigenomicsAgent stopped")

    async def health_check(self) -> bool:
        """Return True — no external dependencies required."""
        return True

    async def _execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyse methylation data from input.

        Args:
            input_data: Must contain ``methylation_data`` (dict mapping
                        region names to beta-value lists).

        Returns:
            Methylation analysis result.
        """
        methylation_data = input_data.get("methylation_data", {})
        return self.analyze_methylation(methylation_data)

    # ------------------------------------------------------------------
    # Public domain methods
    # ------------------------------------------------------------------

    def analyze_methylation(
        self,
        methylation_data: Dict[str, List[float]],
    ) -> Dict[str, Any]:
        """Compute per-region methylation statistics from beta values.

        Args:
            methylation_data: Dict mapping genomic region names to lists
                              of beta values (0–1).

        Returns:
            Dictionary with per-region mean, standard deviation, and
            an ``overall_mean`` summary.
        """
        if not methylation_data:
            return {"regions": {}, "overall_mean": 0.0}

        region_stats: Dict[str, Any] = {}
        all_means: List[float] = []

        for region, beta_values in methylation_data.items():
            arr = np.array(beta_values, dtype=float)
            mean_beta = float(np.mean(arr))
            std_beta = float(np.std(arr))
            region_stats[region] = {
                "mean_beta": round(mean_beta, 4),
                "std_beta": round(std_beta, 4),
                "n_cpg": len(beta_values),
                "hypermethylated": mean_beta >= 0.7,
                "hypomethylated": mean_beta <= 0.3,
            }
            all_means.append(mean_beta)

        overall_mean = float(np.mean(all_means)) if all_means else 0.0
        self.logger.info(
            "analyze_methylation: %d regions, overall_mean=%.4f",
            len(methylation_data),
            overall_mean,
        )
        return {
            "regions": region_stats,
            "overall_mean": round(overall_mean, 4),
        }

    def call_dmr(
        self,
        control_methylation: Dict[str, List[float]],
        treatment_methylation: Dict[str, List[float]],
        delta_threshold: float = 0.2,
    ) -> Dict[str, Any]:
        """Identify differentially methylated regions (DMRs).

        Args:
            control_methylation: Beta values per region for controls.
            treatment_methylation: Beta values per region for treated samples.
            delta_threshold: Minimum |Δbeta| to call a DMR (default 0.2).

        Returns:
            Dictionary with ``dmrs`` list and summary counts.
        """
        dmrs: List[Dict[str, Any]] = []
        common_regions = set(control_methylation) & set(treatment_methylation)

        for region in common_regions:
            ctrl_mean = float(np.mean(control_methylation[region]))
            trt_mean = float(np.mean(treatment_methylation[region]))
            delta = trt_mean - ctrl_mean
            if abs(delta) >= delta_threshold:
                dmrs.append(
                    {
                        "region": region,
                        "control_mean": round(ctrl_mean, 4),
                        "treatment_mean": round(trt_mean, 4),
                        "delta_beta": round(delta, 4),
                        "direction": "hyper" if delta > 0 else "hypo",
                    }
                )

        self.logger.info("call_dmr: %d DMRs detected", len(dmrs))
        return {
            "dmrs": dmrs,
            "dmr_count": len(dmrs),
            "hyper_count": sum(1 for d in dmrs if d["direction"] == "hyper"),
            "hypo_count": sum(1 for d in dmrs if d["direction"] == "hypo"),
        }

    def assess_chromatin_accessibility(
        self,
        atac_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Assess chromatin accessibility from ATAC-seq peak data.

        Args:
            atac_data: Dictionary with ``peaks`` (list of dicts with
                       ``region``, ``score``) and optional ``total_reads``.

        Returns:
            Summary of accessible chromatin regions.
        """
        peaks = atac_data.get("peaks", [])
        total_reads = atac_data.get("total_reads", 1)

        if not peaks:
            return {"accessible_regions": 0, "peaks": []}

        scored_peaks = sorted(peaks, key=lambda p: p.get("score", 0), reverse=True)
        accessible = [p for p in scored_peaks if p.get("score", 0) >= 5]

        self.logger.info(
            "assess_chromatin_accessibility: %d peaks, %d accessible",
            len(peaks),
            len(accessible),
        )
        return {
            "total_peaks": len(peaks),
            "accessible_regions": len(accessible),
            "top_peaks": scored_peaks[:10],
            "frip_estimate": round(
                sum(p.get("score", 0) for p in peaks) / max(total_reads, 1), 4
            ),
        }
