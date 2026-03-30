"""Genomic.go Platform - Variant Interpretation Agent.

Clinical significance prediction and ACMG classification for genomic
variants using ClinVar and rule-based scoring.
"""

import logging
from typing import Any, Dict, Optional

from src.agents.base import AgentStatus, GenomicAgent
from src.agents.mcp_tools import classify_variant

logger = logging.getLogger(__name__)

_PATHOGENICITY_WEIGHTS: Dict[str, float] = {
    "population_frequency": -2.0,
    "conservation_score": 1.5,
    "functional_impact": 2.0,
    "splicing_effect": 1.8,
    "protein_domain": 1.2,
}


class VariantInterpretationAgent(GenomicAgent):
    """Agent for genomic variant clinical interpretation.

    Queries ClinVar, applies rule-based pathogenicity scoring, and
    produces ACMG-style classifications.

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
            name="VariantInterpretationAgent",
            agent_id=agent_id,
            redis_url=redis_url,
        )

    async def initialize(self) -> None:
        """Initialise the variant interpretation agent."""
        self.logger.info("VariantInterpretationAgent initialised")

    async def start(self) -> None:
        """Start the variant interpretation agent."""
        self.logger.info("VariantInterpretationAgent started")

    async def stop(self) -> None:
        """Stop the variant interpretation agent."""
        self._status = AgentStatus.STOPPED
        self.logger.info("VariantInterpretationAgent stopped")

    async def health_check(self) -> bool:
        """Return True — external calls handled gracefully."""
        return True

    async def _execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Interpret a variant from input data.

        Args:
            input_data: Must contain ``gene`` and ``variant`` keys.

        Returns:
            Interpretation result dictionary.
        """
        gene = input_data.get("gene", "")
        variant = input_data.get("variant", "")
        return self.interpret_variant(gene, variant)

    # ------------------------------------------------------------------
    # Public domain methods
    # ------------------------------------------------------------------

    def interpret_variant(self, gene: str, variant: str) -> Dict[str, Any]:
        """Retrieve ClinVar clinical significance for a variant.

        Args:
            gene: Gene symbol (e.g. ``"BRCA1"``).
            variant: Variant description (e.g. ``"c.5266dupC"``).

        Returns:
            ClinVar result enriched with an ``interpretation`` summary.
        """
        self.logger.info("interpret_variant: %s %s", gene, variant)
        result = classify_variant(gene, variant)
        result["interpretation"] = {
            "gene": gene,
            "variant": variant,
            "source": "ClinVar",
        }
        return result

    def predict_pathogenicity(
        self, variant_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply rule-based pathogenicity scoring.

        Scoring is based on weighted evidence criteria.  Positive weights
        increase pathogenicity likelihood; negative weights decrease it.

        Args:
            variant_data: Dictionary with optional keys matching
                          ``_PATHOGENICITY_WEIGHTS`` (values 0–1 for each
                          criterion).

        Returns:
            Dictionary with ``score`` (0–10) and ``prediction`` label.
        """
        score = 0.0
        for criterion, weight in _PATHOGENICITY_WEIGHTS.items():
            value = float(variant_data.get(criterion, 0.0))
            score += value * weight

        normalised = min(10.0, max(0.0, score + 5.0))
        if normalised >= 7.5:
            prediction = "likely_pathogenic"
        elif normalised >= 5.0:
            prediction = "uncertain_significance"
        else:
            prediction = "likely_benign"

        self.logger.info(
            "predict_pathogenicity: score=%.2f prediction=%s", normalised, prediction
        )
        return {
            "score": round(normalised, 2),
            "prediction": prediction,
            "criteria_evaluated": list(_PATHOGENICITY_WEIGHTS.keys()),
        }

    def classify_acmg(
        self, variant_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Classify a variant according to ACMG/AMP guidelines.

        Applies a simplified rule set based on evidence strength.

        Args:
            variant_data: Dict with boolean/numeric evidence flags:
                ``pathogenic_strong``, ``pathogenic_moderate``,
                ``benign_strong``, ``benign_supporting``.

        Returns:
            Dictionary with ``classification`` (one of: Pathogenic,
            Likely Pathogenic, VUS, Likely Benign, Benign) and
            ``evidence_summary``.
        """
        ps = int(variant_data.get("pathogenic_strong", 0))
        pm = int(variant_data.get("pathogenic_moderate", 0))
        bs = int(variant_data.get("benign_strong", 0))
        bp = int(variant_data.get("benign_supporting", 0))

        path_score = ps * 4 + pm * 2
        benign_score = bs * 4 + bp * 1

        if path_score >= 8:
            classification = "Pathogenic"
        elif path_score >= 5:
            classification = "Likely Pathogenic"
        elif benign_score >= 8:
            classification = "Benign"
        elif benign_score >= 5:
            classification = "Likely Benign"
        else:
            classification = "VUS"

        self.logger.info("classify_acmg: %s", classification)
        return {
            "classification": classification,
            "pathogenic_score": path_score,
            "benign_score": benign_score,
            "evidence_summary": {
                "pathogenic_strong": ps,
                "pathogenic_moderate": pm,
                "benign_strong": bs,
                "benign_supporting": bp,
            },
        }
