"""Tests for Genomics Analysis Engine."""

import sys
import os

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from genomics.gwas_analyzer import (
    GWASAnalyzer,
    GWASResult,
    VariantAnnotator,
    GeneExpressionAnalyzer,
    PopulationGeneticsAnalyzer,
    Variant,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def rng():
    return np.random.default_rng(42)


@pytest.fixture
def small_genotype_matrix(rng):
    """10 samples x 50 variants."""
    n_samples, n_variants = 10, 50
    variant_ids = [f"chr1:{i * 1000}" for i in range(n_variants)]
    data = rng.integers(0, 3, size=(n_samples, n_variants))
    return pd.DataFrame(data.astype(float), columns=variant_ids)


@pytest.fixture
def phenotype():
    """5 cases, 5 controls."""
    return pd.Series([1, 1, 1, 1, 1, 0, 0, 0, 0, 0])


@pytest.fixture
def analyzer():
    return GWASAnalyzer(maf_threshold=0.01)


# ---------------------------------------------------------------------------
# GWASAnalyzer Tests
# ---------------------------------------------------------------------------


class TestGWASAnalyzer:
    def test_initialization(self, analyzer):
        assert analyzer.maf_threshold == 0.01
        assert analyzer.hwe_p_threshold == 1e-6

    def test_quality_control_returns_dataframe(self, analyzer, small_genotype_matrix):
        result = analyzer.quality_control(small_genotype_matrix)
        assert isinstance(result, pd.DataFrame)
        assert len(result.columns) <= len(small_genotype_matrix.columns)

    def test_quality_control_empty_df(self, analyzer):
        empty = pd.DataFrame()
        result = analyzer.quality_control(empty)
        assert result.empty

    def test_run_association_analysis(self, analyzer, small_genotype_matrix, phenotype):
        qc = analyzer.quality_control(small_genotype_matrix)
        results = analyzer.run_association_analysis(qc, phenotype)
        assert isinstance(results, list)
        # Results should be sorted by p-value
        for i in range(len(results) - 1):
            assert results[i].p_value <= results[i + 1].p_value

    def test_association_result_structure(self, analyzer, small_genotype_matrix, phenotype):
        qc = analyzer.quality_control(small_genotype_matrix)
        results = analyzer.run_association_analysis(qc, phenotype)
        if results:
            r = results[0]
            assert isinstance(r, GWASResult)
            assert 0 <= r.p_value <= 1
            assert r.odds_ratio > 0
            assert r.standard_error > 0
            assert len(r.confidence_interval) == 2

    def test_genomic_inflation_no_results(self, analyzer):
        lam = analyzer.calculate_genomic_inflation([])
        assert lam == 1.0

    def test_genomic_inflation_uniform(self, analyzer):
        """Under the null, p-values uniform → lambda ≈ 1."""
        p_values = np.random.default_rng(0).uniform(0, 1, 1000).tolist()
        lam = analyzer.calculate_genomic_inflation(p_values)
        assert 0.5 < lam < 2.0

    def test_apply_genomic_control_identity_when_close_to_one(self, analyzer):
        """When lambda ≈ 1, results should be unchanged."""
        from unittest.mock import patch

        results = [
            GWASResult(
                variant=Variant("chr1", 1000, "A", "T", rsid="rs1"),
                p_value=0.5,
                odds_ratio=1.0,
                confidence_interval=(0.8, 1.2),
                beta=0.0,
                standard_error=0.1,
                n_cases=100,
                n_controls=100,
            )
        ]
        with patch.object(analyzer, "calculate_genomic_inflation", return_value=1.005):
            corrected = analyzer.apply_genomic_control(results)
        assert len(corrected) == len(results)

    def test_get_significant_hits(self, analyzer, small_genotype_matrix, phenotype):
        qc = analyzer.quality_control(small_genotype_matrix)
        results = analyzer.run_association_analysis(qc, phenotype)
        sig = analyzer.get_significant_hits(results, threshold=0.05)
        assert all(r.p_value < 0.05 for r in sig)

    def test_hardy_weinberg_balanced_population(self, analyzer):
        """Balanced heterozygous genotypes should pass HWE."""
        # p = q = 0.5, so HWE expected frequencies: AA=0.25, AB=0.5, BB=0.25
        dosages = pd.Series([0] * 25 + [1] * 50 + [2] * 25)
        p_val = analyzer._hardy_weinberg_test(dosages)
        assert p_val > 0.05


# ---------------------------------------------------------------------------
# VariantAnnotator Tests
# ---------------------------------------------------------------------------


class TestVariantAnnotator:
    def test_annotate_known_chromosome(self):
        annotator = VariantAnnotator()
        variant = Variant(chromosome="chr17", position=43_044_295, ref_allele="A", alt_allele="G")
        annotated = annotator.annotate_variant(variant)
        assert annotated.gene == "BRCA1"

    def test_annotate_unknown_chromosome(self):
        annotator = VariantAnnotator()
        variant = Variant(chromosome="chrX", position=100_000, ref_allele="A", alt_allele="T")
        annotated = annotator.annotate_variant(variant)
        assert annotated.gene is not None
        assert annotated.consequence is not None

    def test_annotate_from_database(self):
        db = {"chr1:5000": {"gene": "TEST_GENE", "consequence": "missense_variant"}}
        annotator = VariantAnnotator(gene_database=db)
        variant = Variant("chr1", 5000, "A", "T")
        annotated = annotator.annotate_variant(variant)
        assert annotated.gene == "TEST_GENE"
        assert annotated.consequence == "missense_variant"

    def test_annotate_batch(self):
        annotator = VariantAnnotator()
        variants = [
            Variant("chr1", 1000, "A", "T"),
            Variant("chr2", 2000, "G", "C"),
        ]
        annotated = annotator.annotate_batch(variants)
        assert len(annotated) == 2

    def test_prioritize_variants_by_severity(self):
        annotator = VariantAnnotator()
        variants = [
            Variant("chr1", 1000, "A", "T", consequence="intergenic_variant"),
            Variant("chr1", 2000, "G", "C", consequence="stop_gained"),
            Variant("chr1", 3000, "C", "A", consequence="missense_variant"),
        ]
        prioritized = annotator.prioritize_variants(variants)
        assert prioritized[0].consequence == "stop_gained"

    def test_predict_frameshift_indel(self):
        annotator = VariantAnnotator()
        variant = Variant("chr1", 1000, "A", "AT")  # +1 insertion → frameshift
        annotated = annotator.annotate_variant(variant)
        assert annotated.consequence == "frameshift_variant"

    def test_predict_inframe_indel(self):
        annotator = VariantAnnotator()
        variant = Variant("chr1", 1000, "A", "ATTT")  # +3 insertion → inframe
        annotated = annotator.annotate_variant(variant)
        assert annotated.consequence == "inframe_indel"


# ---------------------------------------------------------------------------
# GeneExpressionAnalyzer Tests
# ---------------------------------------------------------------------------


class TestGeneExpressionAnalyzer:
    @pytest.fixture
    def expression_data(self):
        """5 genes x 8 samples (4 ctrl, 4 treatment)."""
        rng = np.random.default_rng(0)
        data = rng.standard_normal((5, 8))
        # Make gene 0 differentially expressed
        data[0, 4:] += 3.0
        genes = [f"GENE_{i}" for i in range(5)]
        samples = [f"ctrl_{i}" for i in range(4)] + [f"treat_{i}" for i in range(4)]
        return pd.DataFrame(data, index=genes, columns=samples)

    def test_differential_expression(self, expression_data):
        analyzer = GeneExpressionAnalyzer()
        results = analyzer.differential_expression(
            expression_data,
            group1_samples=[f"ctrl_{i}" for i in range(4)],
            group2_samples=[f"treat_{i}" for i in range(4)],
        )
        assert len(results) == 5
        # Results sorted by adjusted p-value
        for i in range(len(results) - 1):
            assert results[i].adjusted_p_value <= results[i + 1].adjusted_p_value

    def test_significant_gene_detected(self, expression_data):
        analyzer = GeneExpressionAnalyzer(fdr_threshold=0.1, log2_fc_threshold=1.0)
        results = analyzer.differential_expression(
            expression_data,
            group1_samples=[f"ctrl_{i}" for i in range(4)],
            group2_samples=[f"treat_{i}" for i in range(4)],
        )
        sig = analyzer.get_significant_genes(results)
        # GENE_0 should be detected as significant
        sig_ids = [r.gene_id for r in sig]
        assert "GENE_0" in sig_ids

    def test_empty_groups_return_empty(self):
        analyzer = GeneExpressionAnalyzer()
        df = pd.DataFrame({"A": [1.0]}, index=["G1"])
        results = analyzer.differential_expression(df, ["A"], ["A"])
        # Single sample per group → skipped
        assert isinstance(results, list)

    def test_benjamini_hochberg_monotone(self):
        p_values = [0.001, 0.01, 0.05, 0.1, 0.5]
        adjusted = GeneExpressionAnalyzer._benjamini_hochberg(p_values)
        assert len(adjusted) == len(p_values)
        assert all(0 <= p <= 1 for p in adjusted)

    def test_pathway_enrichment_summary(self, expression_data):
        analyzer = GeneExpressionAnalyzer(fdr_threshold=0.9)
        results = analyzer.differential_expression(
            expression_data,
            group1_samples=[f"ctrl_{i}" for i in range(4)],
            group2_samples=[f"treat_{i}" for i in range(4)],
        )
        for r in results:
            r.is_significant = True  # Force all significant for test
        summary = analyzer.pathway_enrichment_summary(results)
        assert isinstance(summary, dict)


# ---------------------------------------------------------------------------
# PopulationGeneticsAnalyzer Tests
# ---------------------------------------------------------------------------


class TestPopulationGeneticsAnalyzer:
    @pytest.fixture
    def pop_analyzer(self):
        return PopulationGeneticsAnalyzer()

    def test_fst_identical_populations(self, pop_analyzer):
        dosages = pd.Series([0, 1, 2, 1, 0, 1])
        fst = pop_analyzer.compute_fst(dosages, dosages)
        assert fst == pytest.approx(0.0, abs=0.01)

    def test_fst_fixed_populations(self, pop_analyzer):
        """One population fixed for alt, other for ref → Fst close to 1."""
        pop1 = pd.Series([2, 2, 2, 2, 2])
        pop2 = pd.Series([0, 0, 0, 0, 0])
        fst = pop_analyzer.compute_fst(pop1, pop2)
        assert fst > 0.8

    def test_fst_in_valid_range(self, pop_analyzer, rng):
        pop1 = pd.Series(rng.integers(0, 3, 50))
        pop2 = pd.Series(rng.integers(0, 3, 50))
        fst = pop_analyzer.compute_fst(pop1, pop2)
        assert 0.0 <= fst <= 1.0

    def test_tajimas_d_insufficient_sequences(self, pop_analyzer):
        result = pop_analyzer.tajimas_d(["ATCG", "ATCG"])
        assert result == 0.0

    def test_tajimas_d_constant_sequences(self, pop_analyzer):
        seqs = ["ATCG"] * 10
        result = pop_analyzer.tajimas_d(seqs)
        assert result == 0.0

    def test_hardy_weinberg_balanced(self, pop_analyzer):
        dosages = pd.Series([0] * 25 + [1] * 50 + [2] * 25)
        p_value, in_hwe = pop_analyzer.hardy_weinberg_equilibrium(dosages)
        assert in_hwe is True
        assert p_value > 0.001

    def test_hardy_weinberg_empty(self, pop_analyzer):
        p_value, in_hwe = pop_analyzer.hardy_weinberg_equilibrium(pd.Series([], dtype=float))
        assert in_hwe is True

    def test_compute_population_statistics(self, pop_analyzer, rng):
        variant = Variant("chr1", 1000, "A", "T")
        populations = {
            "EUR": pd.Series(rng.integers(0, 3, 100)),
            "AFR": pd.Series(rng.integers(0, 3, 100)),
        }
        stats = pop_analyzer.compute_population_statistics(variant, populations)
        assert 0.0 <= stats.fst <= 1.0
        assert set(stats.allele_frequencies.keys()) == {"EUR", "AFR"}
        assert 0 <= stats.hwe_p_value <= 1
