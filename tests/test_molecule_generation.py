"""Tests for Molecule Generation Engine."""

import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from molecule_generation.generator import (
    FragmentLibrary,
    GeneratedMolecule,
    GenerationStrategy,
    MoleculeGenerator,
    PropertyConstraints,
    ScaffoldEnumerator,
    SMILESUtils,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def generator():
    return MoleculeGenerator(seed=42)


@pytest.fixture
def fragment_library():
    return FragmentLibrary()


@pytest.fixture
def smiles_utils():
    return SMILESUtils()


# ---------------------------------------------------------------------------
# FragmentLibrary Tests
# ---------------------------------------------------------------------------


class TestFragmentLibrary:
    def test_get_random_fragment(self, fragment_library):
        import random

        rng = random.Random(0)
        fragment = fragment_library.get_random_fragment(rng)
        assert isinstance(fragment, str)
        assert len(fragment) > 0

    def test_get_linker(self, fragment_library):
        import random

        rng = random.Random(0)
        linker = fragment_library.get_linker(rng)
        assert isinstance(linker, str)

    def test_get_functional_group(self, fragment_library):
        import random

        rng = random.Random(0)
        fg = fragment_library.get_functional_group(rng)
        assert isinstance(fg, str)

    def test_core_fragments_not_empty(self, fragment_library):
        assert len(fragment_library.CORE_FRAGMENTS) > 0

    def test_functional_groups_not_empty(self, fragment_library):
        assert len(fragment_library.FUNCTIONAL_GROUPS) > 0


# ---------------------------------------------------------------------------
# SMILESUtils Tests
# ---------------------------------------------------------------------------


class TestSMILESUtils:
    def test_estimate_mw_positive(self, smiles_utils):
        mw = smiles_utils.estimate_mw("CCO")
        assert mw > 0

    def test_estimate_logp_is_float(self, smiles_utils):
        logp = smiles_utils.estimate_logp("c1ccccc1")
        assert isinstance(logp, float)

    def test_estimate_tpsa_non_negative(self, smiles_utils):
        tpsa = smiles_utils.estimate_tpsa("CCO")
        assert tpsa >= 0

    def test_canonical_smiles_strips_whitespace(self, smiles_utils):
        result = smiles_utils.canonical_smiles("  CCO  ")
        assert result == "CCO"

    def test_molecule_fingerprint_deterministic(self, smiles_utils):
        fp1 = smiles_utils.molecule_fingerprint("CCO")
        fp2 = smiles_utils.molecule_fingerprint("CCO")
        assert fp1 == fp2

    def test_molecule_fingerprint_different_smiles(self, smiles_utils):
        fp1 = smiles_utils.molecule_fingerprint("CCO")
        fp2 = smiles_utils.molecule_fingerprint("CCCO")
        assert fp1 != fp2

    def test_tanimoto_identical_smiles(self, smiles_utils):
        sim = smiles_utils.tanimoto_similarity("CCO", "CCO")
        assert sim == pytest.approx(1.0, abs=0.01)

    def test_tanimoto_dissimilar_smiles(self, smiles_utils):
        sim = smiles_utils.tanimoto_similarity("CCO", "c1ccccc1C(=O)O")
        assert 0 <= sim < 1.0


# ---------------------------------------------------------------------------
# MoleculeGenerator Tests
# ---------------------------------------------------------------------------


class TestMoleculeGenerator:
    def test_generate_returns_list(self, generator):
        molecules = generator.generate(n_molecules=3)
        assert isinstance(molecules, list)

    def test_generate_respects_n_molecules(self, generator):
        molecules = generator.generate(n_molecules=5)
        assert len(molecules) <= 5

    def test_generate_returns_generated_molecule_objects(self, generator):
        molecules = generator.generate(n_molecules=3)
        for mol in molecules:
            assert isinstance(mol, GeneratedMolecule)

    def test_generated_molecule_has_smiles(self, generator):
        molecules = generator.generate(n_molecules=2)
        for mol in molecules:
            assert isinstance(mol.smiles, str)
            assert len(mol.smiles) > 0

    def test_generated_molecule_has_qed_score(self, generator):
        molecules = generator.generate(n_molecules=2)
        for mol in molecules:
            assert 0.0 <= mol.qed_score <= 1.0

    def test_generated_molecule_has_sa_score(self, generator):
        molecules = generator.generate(n_molecules=2)
        for mol in molecules:
            assert 1.0 <= mol.sa_score <= 10.0

    def test_strategy_fragment_based(self, generator):
        molecules = generator.generate(
            n_molecules=3, strategy=GenerationStrategy.FRAGMENT_BASED
        )
        for mol in molecules:
            assert mol.strategy == GenerationStrategy.FRAGMENT_BASED

    def test_strategy_genetic_algorithm(self, generator):
        molecules = generator.generate(
            n_molecules=3, strategy=GenerationStrategy.GENETIC_ALGORITHM
        )
        assert len(molecules) <= 3

    def test_strategy_scaffold_decoration(self, generator):
        molecules = generator.generate(
            n_molecules=3,
            strategy=GenerationStrategy.SCAFFOLD_DECORATION,
            scaffold="c1ccncc1",
        )
        assert len(molecules) <= 3

    def test_strategy_bioisostere_with_reference(self, generator):
        molecules = generator.generate(
            n_molecules=3,
            strategy=GenerationStrategy.BIOISOSTERE,
            reference_smiles="c1ccccc1",
        )
        assert len(molecules) <= 3

    def test_property_constraints_applied(self):
        constraints = PropertyConstraints(min_mw=200, max_mw=350, min_logp=-1, max_logp=3)
        generator = MoleculeGenerator(constraints=constraints, seed=7)
        molecules = generator.generate(n_molecules=5)
        for mol in molecules:
            assert constraints.min_mw <= mol.predicted_mw <= constraints.max_mw

    def test_sorted_by_qed_descending(self, generator):
        molecules = generator.generate(n_molecules=5)
        for i in range(len(molecules) - 1):
            assert molecules[i].qed_score >= molecules[i + 1].qed_score

    def test_optimize_returns_analogs(self, generator):
        analogs = generator.optimize("c1ccccc1", n_analogs=5)
        assert len(analogs) <= 5

    def test_novelty_score_range(self, generator):
        molecules = generator.generate(n_molecules=5)
        for mol in molecules:
            assert 0.0 <= mol.novelty_score <= 1.0

    def test_diversity_score_range(self, generator):
        molecules = generator.generate(n_molecules=5)
        for mol in molecules:
            assert 0.0 <= mol.diversity_score <= 1.0

    def test_unique_molecule_ids(self, generator):
        molecules = generator.generate(n_molecules=5)
        ids = [m.molecule_id for m in molecules]
        assert len(ids) == len(set(ids))  # All IDs should be unique


# ---------------------------------------------------------------------------
# ScaffoldEnumerator Tests
# ---------------------------------------------------------------------------


class TestScaffoldEnumerator:
    @pytest.fixture
    def enumerator(self):
        return ScaffoldEnumerator()

    def test_enumerate_returns_list(self, enumerator):
        analogs = enumerator.enumerate("c1ccncc1")
        assert isinstance(analogs, list)

    def test_enumerate_respects_max_analogs(self, enumerator):
        analogs = enumerator.enumerate("c1ccncc1", max_analogs=10)
        assert len(analogs) <= 10

    def test_enumerate_no_duplicates(self, enumerator):
        analogs = enumerator.enumerate("c1ccncc1")
        assert len(analogs) == len(set(analogs))

    def test_cluster_analogs_returns_dict(self, enumerator):
        smiles_list = ["CCO", "CCCO", "c1ccccc1", "c1ccncc1", "CCC"]
        clusters = enumerator.cluster_analogs(smiles_list, n_clusters=2)
        assert isinstance(clusters, dict)

    def test_cluster_analogs_all_assigned(self, enumerator):
        smiles_list = ["CCO", "CCCO", "c1ccccc1"]
        clusters = enumerator.cluster_analogs(smiles_list, n_clusters=2)
        total_assigned = sum(len(v) for v in clusters.values())
        assert total_assigned == len(smiles_list)

    def test_cluster_empty_list(self, enumerator):
        clusters = enumerator.cluster_analogs([], n_clusters=3)
        assert clusters == {}
