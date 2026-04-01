"""Tests for GWAS Analysis Module."""

import math
import sys
import os

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from gwas.gwas_analyzer import (
    GWAS_SIGNIFICANCE_THRESHOLD,
    AssociationResult,
    AssociationTester,
    GWASAnalyzer,
    GWASLocus,
    LDClumper,
    MultipleTestingCorrector,
    QualityController,
    Variant,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_variant(
    variant_id: str = "rs123",
    chrom: str = "1",
    pos: int = 100_000,
    maf: float = 0.15,
    hwe_p: float = 0.5,
    missingness: float = 0.01,
) -> Variant:
    return Variant(
        variant_id=variant_id,
        chromosome=chrom,
        position=pos,
        ref_allele="A",
        alt_allele="G",
        minor_allele_frequency=maf,
        hwe_p_value=hwe_p,
        genotype_missingness=missingness,
    )


def _make_result(
    variant_id: str = "rs123",
    chrom: str = "1",
    pos: int = 100_000,
    p_value: float = 0.05,
    effect_size: float = 0.1,
) -> AssociationResult:
    return AssociationResult(
        variant_id=variant_id,
        chromosome=chrom,
        position=pos,
        ref_allele="A",
        alt_allele="G",
        minor_allele_frequency=0.15,
        effect_size=effect_size,
        standard_error=0.02,
        p_value=p_value,
    )


# ---------------------------------------------------------------------------
# QualityController
# ---------------------------------------------------------------------------


class TestQualityController:
    def test_all_pass(self):
        qc = QualityController()
        variants = [_make_variant(variant_id=f"rs{i}") for i in range(5)]
        passing, summary = qc.filter_variants(variants)
        assert len(passing) == 5
        assert summary["pass_rate"] == 1.0
        assert summary["failed_maf_filter"] == 0

    def test_maf_filter(self):
        qc = QualityController(maf_threshold=0.05)
        variants = [
            _make_variant("rs1", maf=0.02),  # fails
            _make_variant("rs2", maf=0.10),  # passes
        ]
        passing, summary = qc.filter_variants(variants)
        assert len(passing) == 1
        assert passing[0].variant_id == "rs2"
        assert summary["failed_maf_filter"] == 1

    def test_hwe_filter(self):
        qc = QualityController(hwe_threshold=0.001)
        variants = [
            _make_variant("rs1", hwe_p=0.0001),  # fails
            _make_variant("rs2", hwe_p=0.5),  # passes
        ]
        passing, summary = qc.filter_variants(variants)
        assert len(passing) == 1
        assert summary["failed_hwe_filter"] == 1

    def test_missingness_filter(self):
        qc = QualityController(missingness_threshold=0.05)
        variants = [
            _make_variant("rs1", missingness=0.10),  # fails
            _make_variant("rs2", missingness=0.01),  # passes
        ]
        passing, summary = qc.filter_variants(variants)
        assert len(passing) == 1
        assert summary["failed_missingness_filter"] == 1

    def test_empty_input(self):
        qc = QualityController()
        passing, summary = qc.filter_variants([])
        assert len(passing) == 0
        assert summary["pass_rate"] == 0.0


# ---------------------------------------------------------------------------
# AssociationTester
# ---------------------------------------------------------------------------


class TestAssociationTester:
    def test_chi_square_significant_association(self):
        tester = AssociationTester("chi_square")
        variant = _make_variant()
        # Strong association: many alt alleles in cases, few in controls
        case_counts = np.array([50, 950])
        ctrl_counts = np.array([900, 100])
        result = tester.run_association(variant, case_counts, ctrl_counts)
        assert result.p_value < 1e-10
        assert result.odds_ratio is not None
        assert result.odds_ratio < 1.0  # ref enriched in cases relative to controls

    def test_chi_square_no_association(self):
        tester = AssociationTester("chi_square")
        variant = _make_variant()
        # Equal distribution: no association
        case_counts = np.array([500, 500])
        ctrl_counts = np.array([500, 500])
        result = tester.run_association(variant, case_counts, ctrl_counts)
        assert result.p_value > 0.05

    def test_logistic_significant(self):
        tester = AssociationTester("logistic")
        variant = _make_variant()
        case_counts = np.array([100, 900])
        ctrl_counts = np.array([800, 200])
        result = tester.run_association(variant, case_counts, ctrl_counts)
        assert result.p_value < 0.001

    def test_logistic_no_association(self):
        tester = AssociationTester("logistic")
        variant = _make_variant()
        case_counts = np.array([500, 500])
        ctrl_counts = np.array([500, 500])
        result = tester.run_association(variant, case_counts, ctrl_counts)
        assert result.p_value > 0.05

    def test_invalid_method(self):
        with pytest.raises(ValueError, match="Unknown method"):
            AssociationTester("invalid")

    def test_batch_run_length(self):
        tester = AssociationTester("chi_square")
        variants = [_make_variant(f"rs{i}") for i in range(5)]
        case_c = [np.array([500, 500])] * 5
        ctrl_c = [np.array([500, 500])] * 5
        results = tester.batch_run(variants, case_c, ctrl_c)
        assert len(results) == 5

    def test_batch_run_length_mismatch(self):
        tester = AssociationTester()
        variants = [_make_variant()]
        with pytest.raises(ValueError):
            tester.batch_run(variants, [], [np.array([500, 500])])

    def test_null_result_zero_totals(self):
        tester = AssociationTester("chi_square")
        variant = _make_variant()
        result = tester.run_association(variant, np.array([0, 0]), np.array([0, 0]))
        assert result.p_value == 1.0

    def test_is_genome_wide_significant_flag(self):
        result = _make_result(p_value=1e-9)
        assert result.is_genome_wide_significant is True
        result_ns = _make_result(p_value=0.05)
        assert result_ns.is_genome_wide_significant is False

    def test_is_suggestive_flag(self):
        result = _make_result(p_value=1e-6)
        assert result.is_suggestive is True
        assert result.is_genome_wide_significant is False


# ---------------------------------------------------------------------------
# MultipleTestingCorrector
# ---------------------------------------------------------------------------


class TestMultipleTestingCorrector:
    def test_bonferroni_adjusts_p_values(self):
        results = [_make_result(p_value=0.01), _make_result(p_value=0.05)]
        corrected = MultipleTestingCorrector.bonferroni(results, alpha=0.05)
        assert len(corrected) == 2
        # Adjusted p = min(p * n, 1.0) = min(0.01*2, 1.0) = 0.02
        assert abs(corrected[0].p_value - 0.02) < 1e-12
        assert abs(corrected[1].p_value - 0.10) < 1e-12

    def test_bonferroni_caps_at_one(self):
        results = [_make_result(p_value=0.9)]
        corrected = MultipleTestingCorrector.bonferroni(results)
        assert corrected[0].p_value <= 1.0

    def test_bonferroni_empty(self):
        assert MultipleTestingCorrector.bonferroni([]) == []

    def test_bh_smaller_than_bonferroni(self):
        """BH correction should be less conservative than Bonferroni."""
        results = [_make_result(f"rs{i}", p_value=10 ** (-i - 3)) for i in range(10)]
        bonf = MultipleTestingCorrector.bonferroni(results)
        bh = MultipleTestingCorrector.benjamini_hochberg(results)
        sig_bonf = sum(1 for r in bonf if r.is_genome_wide_significant)
        sig_bh = sum(1 for r in bh if r.is_genome_wide_significant)
        assert sig_bh >= sig_bonf

    def test_bh_empty(self):
        assert MultipleTestingCorrector.benjamini_hochberg([]) == []

    def test_bh_monotone(self):
        """BH adjusted p-values should be non-decreasing when sorted by raw p-value."""
        results = [_make_result(f"rs{i}", p_value=10 ** (-i - 1)) for i in range(5)]
        bh = MultipleTestingCorrector.benjamini_hochberg(results)
        sorted_bh = sorted(bh, key=lambda r: r.p_value)
        for i in range(len(sorted_bh) - 1):
            assert sorted_bh[i].p_value <= sorted_bh[i + 1].p_value


# ---------------------------------------------------------------------------
# LDClumper
# ---------------------------------------------------------------------------


class TestLDClumper:
    def test_single_locus(self):
        clumper = LDClumper(window_kb=500)
        results = [
            _make_result("rs1", pos=1_000_000, p_value=1e-10),
            _make_result("rs2", pos=1_100_000, p_value=0.01),  # within 500kb window
        ]
        loci = clumper.clump(results, p_threshold=GWAS_SIGNIFICANCE_THRESHOLD)
        assert len(loci) == 1
        assert loci[0].lead_variant.variant_id == "rs1"

    def test_two_independent_loci(self):
        clumper = LDClumper(window_kb=500)
        results = [
            _make_result("rs1", chrom="1", pos=1_000_000, p_value=1e-10),
            _make_result("rs2", chrom="1", pos=10_000_000, p_value=1e-9),  # far away
        ]
        loci = clumper.clump(results, p_threshold=GWAS_SIGNIFICANCE_THRESHOLD)
        assert len(loci) == 2

    def test_no_significant_variants(self):
        clumper = LDClumper()
        results = [_make_result("rs1", p_value=0.5)]
        loci = clumper.clump(results)
        assert loci == []

    def test_locus_region_string(self):
        clumper = LDClumper(window_kb=500)
        results = [_make_result("rs1", chrom="3", pos=5_000_000, p_value=1e-10)]
        loci = clumper.clump(results)
        assert "3:" in loci[0].region

    def test_n_variants_in_locus(self):
        clumper = LDClumper(window_kb=1000)
        results = [
            _make_result("rs1", pos=1_000_000, p_value=1e-10),
            _make_result("rs2", pos=1_200_000, p_value=0.001),
            _make_result("rs3", pos=1_400_000, p_value=0.01),
        ]
        loci = clumper.clump(results)
        assert loci[0].n_variants_in_locus >= 1


# ---------------------------------------------------------------------------
# GWASAnalyzer (integration)
# ---------------------------------------------------------------------------


class TestGWASAnalyzer:
    def _make_strong_case_control(self, n: int = 20):
        """Generate variants with strong associations for some, noise for others."""
        variants = []
        cases = []
        controls = []
        for i in range(n):
            v = Variant(
                variant_id=f"rs{i}",
                chromosome="1",
                position=(i + 1) * 100_000,
                ref_allele="A",
                alt_allele="G",
                minor_allele_frequency=0.2,
                hwe_p_value=0.3,
                genotype_missingness=0.01,
            )
            variants.append(v)
            if i < 3:  # first 3 variants: strong association
                cases.append(np.array([100, 900]))
                controls.append(np.array([850, 150]))
            else:  # rest: no association
                cases.append(np.array([500, 500]))
                controls.append(np.array([500, 500]))
        return variants, cases, controls

    def test_run_returns_expected_keys(self):
        analyzer = GWASAnalyzer()
        variants, cases, controls = self._make_strong_case_control()
        output = analyzer.run(variants, cases, controls)
        assert "qc_summary" in output
        assert "results" in output
        assert "loci" in output
        assert "n_significant" in output

    def test_run_finds_significant_variants(self):
        analyzer = GWASAnalyzer(correction_method="bonferroni")
        variants, cases, controls = self._make_strong_case_control(n=20)
        output = analyzer.run(variants, cases, controls)
        assert output["n_significant"] > 0

    def test_bh_correction(self):
        analyzer = GWASAnalyzer(correction_method="bh")
        variants, cases, controls = self._make_strong_case_control(n=20)
        output = analyzer.run(variants, cases, controls)
        assert isinstance(output["results"], list)

    def test_results_to_dataframe(self):
        results = [_make_result(f"rs{i}", p_value=10 ** (-i - 1)) for i in range(5)]
        df = GWASAnalyzer.results_to_dataframe(results)
        assert len(df) == 5
        assert "neg_log10_p" in df.columns
        assert "genome_wide_significant" in df.columns

    def test_results_to_dataframe_neg_log10_p(self):
        results = [_make_result(p_value=1e-8)]
        df = GWASAnalyzer.results_to_dataframe(results)
        expected = -math.log10(1e-8)
        assert abs(df["neg_log10_p"].iloc[0] - expected) < 1e-6

    def test_manhattan_plot_data(self):
        results = [
            _make_result("rs1", chrom="1", pos=100_000, p_value=1e-9),
            _make_result("rs2", chrom="2", pos=200_000, p_value=0.05),
        ]
        df = GWASAnalyzer.manhattan_plot_data(results)
        assert "cumulative_position" in df.columns
        assert len(df) == 2
        # chr1 position should be smaller than chr2
        chr1_pos = df.loc[df["chromosome"] == "1", "cumulative_position"].iloc[0]
        chr2_pos = df.loc[df["chromosome"] == "2", "cumulative_position"].iloc[0]
        assert chr2_pos > chr1_pos

    def test_manhattan_plot_data_empty(self):
        df = GWASAnalyzer.manhattan_plot_data([])
        assert df.empty
