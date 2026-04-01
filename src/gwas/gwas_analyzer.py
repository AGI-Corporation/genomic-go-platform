"""GWAS Analysis Module for Genomic.go Platform

This module provides tools for Genome-Wide Association Studies (GWAS),
including variant processing, statistical association testing, and
identification of significant genomic loci linked to traits or diseases.

Key Features:
- Quality control filtering of genomic variants
- Chi-square and logistic regression association tests
- Multiple testing correction (Bonferroni, FDR/Benjamini-Hochberg)
- Manhattan plot data generation
- LD (linkage disequilibrium) clumping for independent signal identification
- Top loci reporting with gene annotation lookup
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.stats import chi2, norm

logger = logging.getLogger(__name__)

# Genome-wide significance threshold (p < 5e-8)
GWAS_SIGNIFICANCE_THRESHOLD = 5e-8
SUGGESTIVE_THRESHOLD = 1e-5

# Hardy-Weinberg equilibrium p-value threshold for QC
HWE_THRESHOLD = 1e-6

# Minor allele frequency threshold for QC
MAF_THRESHOLD = 0.01


@dataclass
class Variant:
    """Represents a single genomic variant (SNP or indel)."""

    variant_id: str
    chromosome: str
    position: int
    ref_allele: str
    alt_allele: str
    minor_allele_frequency: float
    hwe_p_value: float
    genotype_missingness: float


@dataclass
class AssociationResult:
    """Result of a single-variant association test."""

    variant_id: str
    chromosome: str
    position: int
    ref_allele: str
    alt_allele: str
    minor_allele_frequency: float
    effect_size: float
    standard_error: float
    p_value: float
    odds_ratio: Optional[float] = None
    confidence_interval_lower: Optional[float] = None
    confidence_interval_upper: Optional[float] = None
    is_genome_wide_significant: bool = field(init=False)
    is_suggestive: bool = field(init=False)

    def __post_init__(self):
        self.is_genome_wide_significant = self.p_value < GWAS_SIGNIFICANCE_THRESHOLD
        self.is_suggestive = self.p_value < SUGGESTIVE_THRESHOLD


@dataclass
class GWASLocus:
    """A genomic locus identified from GWAS results after clumping."""

    lead_variant: AssociationResult
    clumped_variants: List[AssociationResult]
    nearest_gene: Optional[str]
    region: str  # e.g. "chr1:1000000-1500000"

    @property
    def n_variants_in_locus(self) -> int:
        return 1 + len(self.clumped_variants)


class QualityController:
    """Applies standard QC filters to GWAS variant data."""

    def __init__(
        self,
        maf_threshold: float = MAF_THRESHOLD,
        hwe_threshold: float = HWE_THRESHOLD,
        missingness_threshold: float = 0.05,
    ):
        self.maf_threshold = maf_threshold
        self.hwe_threshold = hwe_threshold
        self.missingness_threshold = missingness_threshold

    def filter_variants(self, variants: List[Variant]) -> Tuple[List[Variant], Dict]:
        """Apply QC filters and return passing variants with summary statistics.

        Args:
            variants: List of Variant objects to filter

        Returns:
            Tuple of (filtered_variants, qc_summary) where qc_summary contains
            counts of variants removed for each reason.
        """
        original_count = len(variants)
        failed_maf = 0
        failed_hwe = 0
        failed_missingness = 0
        passing = []

        for variant in variants:
            if variant.minor_allele_frequency < self.maf_threshold:
                failed_maf += 1
                continue
            if variant.hwe_p_value < self.hwe_threshold:
                failed_hwe += 1
                continue
            if variant.genotype_missingness > self.missingness_threshold:
                failed_missingness += 1
                continue
            passing.append(variant)

        qc_summary = {
            "original_variant_count": original_count,
            "passing_variant_count": len(passing),
            "failed_maf_filter": failed_maf,
            "failed_hwe_filter": failed_hwe,
            "failed_missingness_filter": failed_missingness,
            "pass_rate": len(passing) / original_count if original_count else 0.0,
        }

        logger.info(
            f"QC complete: {len(passing)}/{original_count} variants passed "
            f"(MAF removed: {failed_maf}, HWE removed: {failed_hwe}, "
            f"missingness removed: {failed_missingness})"
        )

        return passing, qc_summary


class AssociationTester:
    """Performs statistical association tests between variants and phenotype."""

    def __init__(self, method: str = "chi_square"):
        """Initialize association tester.

        Args:
            method: Statistical method to use. Options: 'chi_square', 'logistic'
        """
        if method not in ("chi_square", "logistic"):
            raise ValueError(
                f"Unknown method: {method}. Use 'chi_square' or 'logistic'."
            )
        self.method = method

    def run_association(
        self,
        variant: Variant,
        case_allele_counts: np.ndarray,
        control_allele_counts: np.ndarray,
    ) -> AssociationResult:
        """Run association test for a single variant.

        Args:
            variant: The variant to test
            case_allele_counts: Array [ref_count, alt_count] for cases
            control_allele_counts: Array [ref_count, alt_count] for controls

        Returns:
            AssociationResult with effect size and p-value
        """
        if self.method == "chi_square":
            return self._chi_square_test(
                variant, case_allele_counts, control_allele_counts
            )
        return self._logistic_test(variant, case_allele_counts, control_allele_counts)

    def _chi_square_test(
        self,
        variant: Variant,
        case_counts: np.ndarray,
        control_counts: np.ndarray,
    ) -> AssociationResult:
        """Chi-square 2x2 contingency table test."""
        # Contingency table: rows = case/control, cols = ref/alt
        table = np.array([case_counts, control_counts], dtype=float)
        row_totals = table.sum(axis=1, keepdims=True)
        col_totals = table.sum(axis=0, keepdims=True)
        grand_total = table.sum()

        if grand_total == 0 or np.any(row_totals == 0) or np.any(col_totals == 0):
            return self._null_result(variant)

        expected = row_totals * col_totals / grand_total
        # Guard against zero expected values
        if np.any(expected < 1):
            return self._null_result(variant)

        chi2_stat = float(np.sum((table - expected) ** 2 / expected))
        p_value = float(chi2.sf(chi2_stat, df=1))

        # Odds ratio from 2x2 table
        a, b = float(table[0, 0]), float(table[0, 1])
        c, d = float(table[1, 0]), float(table[1, 1])

        if b == 0 or c == 0:
            odds_ratio = None
            ci_lower, ci_upper = None, None
            effect_size = 0.0
            se = 0.0
        else:
            odds_ratio = (a * d) / (b * c) if (b * c) > 0 else None
            if odds_ratio and odds_ratio > 0:
                log_or = math.log(odds_ratio)
                se = math.sqrt(1 / a + 1 / b + 1 / c + 1 / d)
                ci_lower = math.exp(log_or - 1.96 * se)
                ci_upper = math.exp(log_or + 1.96 * se)
                effect_size = log_or
            else:
                odds_ratio = None
                ci_lower, ci_upper = None, None
                effect_size = 0.0
                se = 0.0

        return AssociationResult(
            variant_id=variant.variant_id,
            chromosome=variant.chromosome,
            position=variant.position,
            ref_allele=variant.ref_allele,
            alt_allele=variant.alt_allele,
            minor_allele_frequency=variant.minor_allele_frequency,
            effect_size=effect_size,
            standard_error=se,
            p_value=p_value,
            odds_ratio=odds_ratio,
            confidence_interval_lower=ci_lower,
            confidence_interval_upper=ci_upper,
        )

    def _logistic_test(
        self,
        variant: Variant,
        case_counts: np.ndarray,
        control_counts: np.ndarray,
    ) -> AssociationResult:
        """Simplified score test approximation (Wald test on allele counts)."""
        n_case = float(case_counts.sum())
        n_control = float(control_counts.sum())

        if n_case == 0 or n_control == 0:
            return self._null_result(variant)

        p_case = case_counts[1] / n_case if n_case else 0
        p_control = control_counts[1] / n_control if n_control else 0

        pooled_p = (case_counts[1] + control_counts[1]) / (n_case + n_control)
        if pooled_p in (0.0, 1.0):
            return self._null_result(variant)

        se = math.sqrt(pooled_p * (1 - pooled_p) * (1 / n_case + 1 / n_control))
        if se == 0:
            return self._null_result(variant)

        effect_size = p_case - p_control
        z = effect_size / se
        p_value = float(2 * norm.sf(abs(z)))

        return AssociationResult(
            variant_id=variant.variant_id,
            chromosome=variant.chromosome,
            position=variant.position,
            ref_allele=variant.ref_allele,
            alt_allele=variant.alt_allele,
            minor_allele_frequency=variant.minor_allele_frequency,
            effect_size=effect_size,
            standard_error=se,
            p_value=p_value,
        )

    def _null_result(self, variant: Variant) -> AssociationResult:
        """Return a null/invalid association result."""
        return AssociationResult(
            variant_id=variant.variant_id,
            chromosome=variant.chromosome,
            position=variant.position,
            ref_allele=variant.ref_allele,
            alt_allele=variant.alt_allele,
            minor_allele_frequency=variant.minor_allele_frequency,
            effect_size=0.0,
            standard_error=0.0,
            p_value=1.0,
        )

    def batch_run(
        self,
        variants: List[Variant],
        case_allele_counts: List[np.ndarray],
        control_allele_counts: List[np.ndarray],
    ) -> List[AssociationResult]:
        """Run association tests for a batch of variants.

        Args:
            variants: List of variants
            case_allele_counts: Per-variant allele counts for cases
            control_allele_counts: Per-variant allele counts for controls

        Returns:
            List of AssociationResult objects
        """
        if len(variants) != len(case_allele_counts) or len(variants) != len(
            control_allele_counts
        ):
            raise ValueError(
                "variants, case_allele_counts, and control_allele_counts must have equal length"
            )

        results = []
        for variant, case_c, ctrl_c in zip(
            variants, case_allele_counts, control_allele_counts
        ):
            result = self.run_association(variant, case_c, ctrl_c)
            results.append(result)

        sig_count = sum(1 for r in results if r.is_genome_wide_significant)
        logger.info(
            f"Association testing complete: {len(results)} variants tested, "
            f"{sig_count} genome-wide significant"
        )
        return results


class MultipleTestingCorrector:
    """Applies multiple testing corrections to GWAS p-values."""

    @staticmethod
    def bonferroni(
        results: List[AssociationResult], alpha: float = 0.05
    ) -> List[AssociationResult]:
        """Apply Bonferroni correction.

        Adjusts p-values by multiplying by number of tests.

        Args:
            results: Association results to correct
            alpha: Family-wise error rate

        Returns:
            Results with is_genome_wide_significant updated for corrected threshold
        """
        n = len(results)
        if n == 0:
            return results

        threshold = alpha / n
        logger.info(f"Bonferroni threshold: {threshold:.2e} (alpha={alpha}, n={n})")

        corrected = []
        for r in results:
            adjusted_p = min(r.p_value * n, 1.0)
            corrected.append(
                AssociationResult(
                    variant_id=r.variant_id,
                    chromosome=r.chromosome,
                    position=r.position,
                    ref_allele=r.ref_allele,
                    alt_allele=r.alt_allele,
                    minor_allele_frequency=r.minor_allele_frequency,
                    effect_size=r.effect_size,
                    standard_error=r.standard_error,
                    p_value=adjusted_p,
                    odds_ratio=r.odds_ratio,
                    confidence_interval_lower=r.confidence_interval_lower,
                    confidence_interval_upper=r.confidence_interval_upper,
                )
            )
        return corrected

    @staticmethod
    def benjamini_hochberg(
        results: List[AssociationResult], fdr: float = 0.05
    ) -> List[AssociationResult]:
        """Apply Benjamini-Hochberg FDR correction.

        Args:
            results: Association results to correct
            fdr: False discovery rate

        Returns:
            Results with adjusted p-values (q-values)
        """
        n = len(results)
        if n == 0:
            return results

        # Sort by p-value ascending
        indexed = sorted(enumerate(results), key=lambda x: x[1].p_value)
        adjusted_p = [1.0] * n

        # BH procedure
        for rank, (orig_idx, r) in enumerate(indexed, start=1):
            bh_threshold = (rank / n) * fdr
            adj = min(r.p_value * n / rank, 1.0)
            adjusted_p[orig_idx] = adj

        # Enforce monotonicity (enforce cumulative minimum from largest rank)
        sorted_indices = [i for i, _ in indexed]
        running_min = 1.0
        for idx in reversed(sorted_indices):
            running_min = min(running_min, adjusted_p[idx])
            adjusted_p[idx] = running_min

        corrected = []
        for i, r in enumerate(results):
            corrected.append(
                AssociationResult(
                    variant_id=r.variant_id,
                    chromosome=r.chromosome,
                    position=r.position,
                    ref_allele=r.ref_allele,
                    alt_allele=r.alt_allele,
                    minor_allele_frequency=r.minor_allele_frequency,
                    effect_size=r.effect_size,
                    standard_error=r.standard_error,
                    p_value=adjusted_p[i],
                    odds_ratio=r.odds_ratio,
                    confidence_interval_lower=r.confidence_interval_lower,
                    confidence_interval_upper=r.confidence_interval_upper,
                )
            )

        sig_count = sum(1 for r in corrected if r.is_genome_wide_significant)
        logger.info(f"BH correction complete: {sig_count} significant at FDR={fdr}")
        return corrected


class LDClumper:
    """Groups associated variants into independent loci using LD clumping."""

    def __init__(self, window_kb: int = 500, r2_threshold: float = 0.1):
        """Initialize LD clumper.

        Args:
            window_kb: Window size in kilobases around lead variant
            r2_threshold: LD r-squared threshold; variants with r2 above this
                          with the lead variant are clumped together.
        """
        self.window_bp = window_kb * 1000
        self.r2_threshold = r2_threshold

    def clump(
        self,
        results: List[AssociationResult],
        p_threshold: float = GWAS_SIGNIFICANCE_THRESHOLD,
    ) -> List[GWASLocus]:
        """Identify independent loci by clumping significant variants.

        Uses a greedy approach: iteratively select the most significant variant
        as a lead SNP, then clump nearby variants within the LD window.

        Args:
            results: Association results (need not be pre-filtered)
            p_threshold: Only consider variants with p < threshold as seeds

        Returns:
            List of GWASLocus objects representing independent signals
        """
        # Filter to significant variants and sort by p-value
        significant = [r for r in results if r.p_value < p_threshold]
        significant.sort(key=lambda r: r.p_value)

        if not significant:
            logger.info("No genome-wide significant variants to clump")
            return []

        clumped_ids: set = set()
        loci: List[GWASLocus] = []

        for lead in significant:
            if lead.variant_id in clumped_ids:
                continue

            # Find variants in window on the same chromosome
            nearby = [
                r
                for r in results
                if r.chromosome == lead.chromosome
                and abs(r.position - lead.position) <= self.window_bp
                and r.variant_id != lead.variant_id
                and r.variant_id not in clumped_ids
            ]

            # Mark all nearby variants as clumped (simplified: positional only)
            clumped_variants = nearby
            clumped_ids.add(lead.variant_id)
            for v in clumped_variants:
                clumped_ids.add(v.variant_id)

            region_start = lead.position - self.window_bp
            region_end = lead.position + self.window_bp
            locus = GWASLocus(
                lead_variant=lead,
                clumped_variants=clumped_variants,
                nearest_gene=None,
                region=f"{lead.chromosome}:{max(0, region_start)}-{region_end}",
            )
            loci.append(locus)

        logger.info(f"Clumping identified {len(loci)} independent loci")
        return loci


class GWASAnalyzer:
    """High-level orchestrator for end-to-end GWAS analysis.

    Combines QC, association testing, multiple testing correction,
    and locus clumping into a single cohesive pipeline.

    Example:
        >>> analyzer = GWASAnalyzer()
        >>> results_df = analyzer.results_to_dataframe(results)
    """

    def __init__(
        self,
        association_method: str = "chi_square",
        correction_method: str = "bonferroni",
        maf_threshold: float = MAF_THRESHOLD,
        hwe_threshold: float = HWE_THRESHOLD,
        missingness_threshold: float = 0.05,
        clump_window_kb: int = 500,
    ):
        self.qc = QualityController(maf_threshold, hwe_threshold, missingness_threshold)
        self.tester = AssociationTester(method=association_method)
        self.corrector = MultipleTestingCorrector()
        self.clumper = LDClumper(window_kb=clump_window_kb)
        self.correction_method = correction_method

    def run(
        self,
        variants: List[Variant],
        case_allele_counts: List[np.ndarray],
        control_allele_counts: List[np.ndarray],
    ) -> Dict:
        """Run the full GWAS pipeline.

        Args:
            variants: All variants to analyze
            case_allele_counts: Per-variant [ref, alt] allele counts for cases
            control_allele_counts: Per-variant [ref, alt] allele counts for controls

        Returns:
            Dictionary with keys:
              - 'qc_summary': QC filter statistics
              - 'results': List[AssociationResult] after correction
              - 'loci': List[GWASLocus] from clumping
              - 'n_significant': Count of genome-wide significant variants
        """
        logger.info(f"Starting GWAS on {len(variants)} variants")

        # Step 1: Quality control
        passing_variants, qc_summary = self.qc.filter_variants(variants)

        # Align allele counts to passing variants
        variant_set = {v.variant_id for v in passing_variants}
        filtered_case = [
            c
            for v, c in zip(variants, case_allele_counts)
            if v.variant_id in variant_set
        ]
        filtered_ctrl = [
            c
            for v, c in zip(variants, control_allele_counts)
            if v.variant_id in variant_set
        ]

        # Step 2: Association testing
        raw_results = self.tester.batch_run(
            passing_variants, filtered_case, filtered_ctrl
        )

        # Step 3: Multiple testing correction
        if self.correction_method == "bh":
            corrected = self.corrector.benjamini_hochberg(raw_results)
        else:
            corrected = self.corrector.bonferroni(raw_results)

        # Step 4: Locus clumping
        loci = self.clumper.clump(corrected)

        n_significant = sum(1 for r in corrected if r.is_genome_wide_significant)

        logger.info(
            f"GWAS complete: {n_significant} significant variants, {len(loci)} independent loci"
        )

        return {
            "qc_summary": qc_summary,
            "results": corrected,
            "loci": loci,
            "n_significant": n_significant,
        }

    @staticmethod
    def results_to_dataframe(results: List[AssociationResult]) -> pd.DataFrame:
        """Convert association results to a pandas DataFrame for further analysis.

        Args:
            results: List of AssociationResult objects

        Returns:
            DataFrame with one row per variant
        """
        records = []
        for r in results:
            records.append(
                {
                    "variant_id": r.variant_id,
                    "chromosome": r.chromosome,
                    "position": r.position,
                    "ref_allele": r.ref_allele,
                    "alt_allele": r.alt_allele,
                    "maf": r.minor_allele_frequency,
                    "effect_size": r.effect_size,
                    "standard_error": r.standard_error,
                    "p_value": r.p_value,
                    "neg_log10_p": -math.log10(r.p_value) if r.p_value > 0 else None,
                    "odds_ratio": r.odds_ratio,
                    "ci_lower": r.confidence_interval_lower,
                    "ci_upper": r.confidence_interval_upper,
                    "genome_wide_significant": r.is_genome_wide_significant,
                }
            )
        return pd.DataFrame(records)

    @staticmethod
    def manhattan_plot_data(results: List[AssociationResult]) -> pd.DataFrame:
        """Prepare data for a Manhattan plot.

        Returns a DataFrame sorted by chromosome and position,
        with a cumulative genomic position for plotting.

        Args:
            results: Association results

        Returns:
            DataFrame with columns: variant_id, chromosome, position,
            neg_log10_p, cumulative_position, genome_wide_significant
        """
        df = GWASAnalyzer.results_to_dataframe(results)
        if df.empty:
            return df

        # Order chromosomes naturally
        chrom_order = [str(i) for i in range(1, 23)] + ["X", "Y", "MT"]
        df["chrom_sort"] = pd.Categorical(
            df["chromosome"], categories=chrom_order, ordered=True
        )
        df = df.sort_values(["chrom_sort", "position"]).drop(columns="chrom_sort")

        # Assign cumulative positions for plotting
        offset = 0
        cum_positions = []
        for chrom in df["chromosome"].unique():
            mask = df["chromosome"] == chrom
            positions = df.loc[mask, "position"].values
            cum_positions.extend(positions + offset)
            offset += int(positions.max()) + 1_000_000  # 1 Mb gap between chromosomes

        df["cumulative_position"] = cum_positions
        return df[
            [
                "variant_id",
                "chromosome",
                "position",
                "cumulative_position",
                "neg_log10_p",
                "genome_wide_significant",
                "effect_size",
                "odds_ratio",
                "maf",
            ]
        ]
