"""Genomic.go Platform - Sequence Analysis Agent.

Provides BLAST-like analysis, variant calling, and multiple sequence
alignment using BioPython.
"""

import logging
from typing import Any, Dict, List, Optional

from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord

from src.agents.base import AgentStatus, GenomicAgent

logger = logging.getLogger(__name__)


class SequenceAnalysisAgent(GenomicAgent):
    """Agent for DNA/RNA sequence analysis.

    Performs BLAST-like sequence analysis, variant calling, and
    multiple sequence alignment using BioPython primitives.

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
            name="SequenceAnalysisAgent",
            agent_id=agent_id,
            redis_url=redis_url,
        )

    async def initialize(self) -> None:
        """Initialise the sequence analysis agent."""
        self.logger.info("SequenceAnalysisAgent initialised")

    async def start(self) -> None:
        """Start the sequence analysis agent."""
        self.logger.info("SequenceAnalysisAgent started")

    async def stop(self) -> None:
        """Stop the sequence analysis agent."""
        self._status = AgentStatus.STOPPED
        self.logger.info("SequenceAnalysisAgent stopped")

    async def health_check(self) -> bool:
        """Return True — no external dependencies required."""
        return True

    async def _execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run sequence analysis on the provided input.

        Args:
            input_data: Must contain ``sequence`` (str) and optionally
                        ``sequence_type`` (``"dna"`` or ``"rna"``).

        Returns:
            Analysis results dictionary.
        """
        sequence = input_data.get("sequence", "")
        seq_type = input_data.get("sequence_type", "dna")
        return self.analyze_sequence(sequence, seq_type)

    # ------------------------------------------------------------------
    # Public domain methods
    # ------------------------------------------------------------------

    def analyze_sequence(
        self,
        sequence: str,
        sequence_type: str = "dna",
    ) -> Dict[str, Any]:
        """Perform basic BLAST-like analysis on a nucleotide sequence.

        Computes GC content, identifies ORFs (for DNA), and reports
        basic sequence statistics.

        Args:
            sequence: Raw nucleotide sequence string.
            sequence_type: Either ``"dna"`` or ``"rna"``.

        Returns:
            Dictionary with ``length``, ``gc_content``, ``sequence_type``,
            and (for DNA) ``orfs``.
        """
        seq = Seq(sequence.upper())
        length = len(seq)
        if length == 0:
            return {"length": 0, "gc_content": 0.0, "sequence_type": sequence_type}

        gc_count = seq.count("G") + seq.count("C")
        gc_content = round(gc_count / length * 100, 2)

        result: Dict[str, Any] = {
            "length": length,
            "gc_content": gc_content,
            "sequence_type": sequence_type,
        }

        if sequence_type.lower() == "dna":
            result["complement"] = str(seq.complement())
            result["reverse_complement"] = str(seq.reverse_complement())
            result["orfs"] = self._find_orfs(str(seq))

        self.logger.info(
            "analyze_sequence: length=%d gc=%.1f%%", length, gc_content
        )
        return result

    def call_variants(
        self,
        reference: str,
        sample: str,
    ) -> Dict[str, Any]:
        """Identify variants between a reference and sample sequence.

        Performs a simple position-by-position comparison to detect
        single-nucleotide variants (SNVs) and report indels.

        Args:
            reference: Reference nucleotide sequence.
            sample: Sample nucleotide sequence to compare.

        Returns:
            Dictionary with ``snvs`` list and ``indel_detected`` flag.
        """
        ref = reference.upper()
        samp = sample.upper()
        snvs: List[Dict[str, Any]] = []
        min_len = min(len(ref), len(samp))
        for i, (r_base, s_base) in enumerate(zip(ref[:min_len], samp[:min_len])):
            if r_base != s_base:
                snvs.append({"position": i, "ref": r_base, "alt": s_base})
        result = {
            "snvs": snvs,
            "snv_count": len(snvs),
            "indel_detected": len(ref) != len(samp),
            "reference_length": len(ref),
            "sample_length": len(samp),
        }
        self.logger.info("call_variants: %d SNVs detected", len(snvs))
        return result

    def align_sequences(
        self,
        sequences: List[str],
    ) -> Dict[str, Any]:
        """Perform pairwise alignment statistics for a list of sequences.

        Uses a simple identity-based scoring approach.  For production
        use, integrate with BioPython's ``pairwise2`` or Clustal.

        Args:
            sequences: List of nucleotide sequence strings.

        Returns:
            Dictionary with ``sequence_count``, ``lengths``, and
            ``pairwise_identities``.
        """
        if not sequences:
            return {"sequence_count": 0, "lengths": [], "pairwise_identities": []}

        seq_objs = [Seq(s.upper()) for s in sequences]
        lengths = [len(s) for s in seq_objs]
        identities: List[Dict[str, Any]] = []

        for i in range(len(seq_objs)):
            for j in range(i + 1, len(seq_objs)):
                s1, s2 = str(seq_objs[i]), str(seq_objs[j])
                min_len = min(len(s1), len(s2))
                if min_len == 0:
                    identity = 0.0
                else:
                    matches = sum(a == b for a, b in zip(s1, s2))
                    identity = round(matches / min_len * 100, 2)
                identities.append(
                    {"seq_i": i, "seq_j": j, "identity_pct": identity}
                )

        self.logger.info(
            "align_sequences: %d sequences, %d pairs", len(sequences), len(identities)
        )
        return {
            "sequence_count": len(sequences),
            "lengths": lengths,
            "pairwise_identities": identities,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _find_orfs(sequence: str, min_length: int = 30) -> List[Dict[str, Any]]:
        """Find open reading frames in a DNA sequence.

        Args:
            sequence: Uppercase DNA sequence.
            min_length: Minimum ORF length in nucleotides (default 30).

        Returns:
            List of ORF dicts with ``start``, ``end``, and ``length``.
        """
        orfs: List[Dict[str, Any]] = []
        start_codon = "ATG"
        stop_codons = {"TAA", "TAG", "TGA"}
        for frame in range(3):
            i = frame
            orf_start: Optional[int] = None
            while i + 3 <= len(sequence):
                codon = sequence[i : i + 3]
                if codon == start_codon and orf_start is None:
                    orf_start = i
                elif codon in stop_codons and orf_start is not None:
                    orf_len = i + 3 - orf_start
                    if orf_len >= min_length:
                        orfs.append(
                            {"start": orf_start, "end": i + 3, "length": orf_len}
                        )
                    orf_start = None
                i += 3
        return orfs
