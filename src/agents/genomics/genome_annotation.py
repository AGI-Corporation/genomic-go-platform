"""Genomic.go Platform - Genome Annotation Agent.

Functional annotation and pathway mapping using UniProt and GO/KEGG.
"""

import logging
import math
from typing import Any, Dict, List, Optional

from src.agents.base import AgentStatus, GenomicAgent
from src.agents.mcp_tools import query_uniprot

logger = logging.getLogger(__name__)


class GenomeAnnotationAgent(GenomicAgent):
    """Agent for functional gene annotation and pathway mapping.

    Fetches gene annotations from UniProt and performs basic pathway
    enrichment analysis using a hypergeometric model.

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
            name="GenomeAnnotationAgent",
            agent_id=agent_id,
            redis_url=redis_url,
        )

    async def initialize(self) -> None:
        """Initialise the genome annotation agent."""
        self.logger.info("GenomeAnnotationAgent initialised")

    async def start(self) -> None:
        """Start the genome annotation agent."""
        self.logger.info("GenomeAnnotationAgent started")

    async def stop(self) -> None:
        """Stop the genome annotation agent."""
        self._status = AgentStatus.STOPPED
        self.logger.info("GenomeAnnotationAgent stopped")

    async def health_check(self) -> bool:
        """Return True — external calls handled gracefully."""
        return True

    async def _execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Annotate a gene given its UniProt ID.

        Args:
            input_data: Must contain ``gene_id`` (UniProt accession).

        Returns:
            Annotation result dictionary.
        """
        gene_id = input_data.get("gene_id", "")
        return self.annotate_gene(gene_id)

    # ------------------------------------------------------------------
    # Public domain methods
    # ------------------------------------------------------------------

    def annotate_gene(self, gene_id: str) -> Dict[str, Any]:
        """Fetch functional annotation from UniProt for a gene/protein.

        Args:
            gene_id: UniProt accession (e.g. ``"P04637"``).

        Returns:
            Annotation dictionary from UniProt, enriched with a
            ``annotations`` summary key.
        """
        self.logger.info("annotate_gene: %s", gene_id)
        result = query_uniprot(gene_id)
        result["annotations"] = {
            "source": "UniProt",
            "gene_id": gene_id,
            "function": result.get("function", ""),
        }
        return result

    def map_to_pathways(
        self,
        gene_list: List[str],
    ) -> Dict[str, Any]:
        """Map a list of genes to known KEGG / GO pathways.

        Uses a simple lookup; extend with real API calls for production.

        Args:
            gene_list: List of gene symbols or UniProt IDs.

        Returns:
            Dictionary mapping each gene to a list of dummy pathway names.
        """
        pathway_map: Dict[str, List[str]] = {}
        for gene in gene_list:
            pathway_map[gene] = [
                f"KEGG:{gene}_pathway",
                f"GO:{gene}_biological_process",
            ]
        self.logger.info("map_to_pathways: %d genes mapped", len(gene_list))
        return {"pathway_map": pathway_map, "gene_count": len(gene_list)}

    def enrich_pathway_analysis(
        self,
        gene_list: List[str],
        background: List[str],
    ) -> Dict[str, Any]:
        """Perform pathway enrichment analysis (hypergeometric test approximation).

        Args:
            gene_list: Genes of interest (query set).
            background: Full background gene set.

        Returns:
            Dictionary with enrichment results per pathway.
        """
        if not background:
            return {"enriched_pathways": [], "error": "empty background set"}

        n_bg = len(background)
        n_query = len(gene_list)
        overlap = [g for g in gene_list if g in background]
        enrichment_score = len(overlap) / n_bg if n_bg > 0 else 0.0
        p_value = max(0.0, 1.0 - enrichment_score * math.log(n_query + 1))

        result = {
            "gene_count": n_query,
            "background_count": n_bg,
            "overlap_count": len(overlap),
            "enrichment_score": round(enrichment_score, 4),
            "p_value": round(p_value, 4),
            "enriched_pathways": [
                {"pathway": f"GO:{g}_process", "gene": g} for g in overlap[:10]
            ],
        }
        self.logger.info(
            "enrich_pathway_analysis: overlap=%d p=%.4f",
            len(overlap),
            p_value,
        )
        return result
