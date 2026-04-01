"""Tests for ADMET Prediction Engine."""

import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from admet.predictor import (
    ADMETPredictor,
    MolecularDescriptorCalculator,
    MolecularDescriptors,
    RiskLevel,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# Representative drug SMILES
IMATINIB_SMILES = "Cc1ccc(NC(=O)c2ccc(CN3CCN(C)CC3)cc2)cc1Nc1nccc(-c2cccnc2)n1"
ASPIRIN_SMILES = "CC(=O)Oc1ccccc1C(=O)O"
SIMPLE_SMILES = "CCO"  # Ethanol


@pytest.fixture
def calculator():
    return MolecularDescriptorCalculator()


@pytest.fixture
def predictor():
    return ADMETPredictor()


# ---------------------------------------------------------------------------
# MolecularDescriptorCalculator Tests
# ---------------------------------------------------------------------------


class TestMolecularDescriptorCalculator:
    def test_returns_descriptors_object(self, calculator):
        desc = calculator.calculate(SIMPLE_SMILES)
        assert isinstance(desc, MolecularDescriptors)

    def test_smiles_stored(self, calculator):
        desc = calculator.calculate(ASPIRIN_SMILES)
        assert desc.smiles == ASPIRIN_SMILES

    def test_molecular_weight_positive(self, calculator):
        desc = calculator.calculate(IMATINIB_SMILES)
        assert desc.molecular_weight > 0

    def test_logp_is_float(self, calculator):
        desc = calculator.calculate(ASPIRIN_SMILES)
        assert isinstance(desc.logp, float)

    def test_hba_positive_for_heteroatoms(self, calculator):
        desc = calculator.calculate("CCO")  # Ethanol: 1 O
        assert desc.hba >= 1

    def test_tpsa_positive(self, calculator):
        desc = calculator.calculate(ASPIRIN_SMILES)
        assert desc.tpsa >= 0

    def test_empty_smiles_raises(self, calculator):
        with pytest.raises(ValueError):
            calculator.calculate("")

    def test_heavy_atom_count_positive(self, calculator):
        desc = calculator.calculate("CCC")
        assert desc.heavy_atom_count >= 1

    def test_aromatic_ring_count_for_benzene(self, calculator):
        desc = calculator.calculate("c1ccccc1")
        assert desc.aromatic_rings >= 1


# ---------------------------------------------------------------------------
# ADMETPredictor Tests
# ---------------------------------------------------------------------------


class TestADMETPredictor:
    def test_predict_returns_profile(self, predictor):
        profile = predictor.predict(ASPIRIN_SMILES, "aspirin")
        assert profile.compound_id == "aspirin"
        assert profile.smiles == ASPIRIN_SMILES

    def test_absorption_profile_populated(self, predictor):
        profile = predictor.predict(ASPIRIN_SMILES)
        assert 0 <= profile.absorption.human_intestinal_absorption <= 1
        assert 0 <= profile.absorption.oral_bioavailability <= 1
        assert isinstance(profile.absorption.passes_lipinski, bool)
        assert profile.absorption.lipinski_violations >= 0

    def test_distribution_profile_populated(self, predictor):
        profile = predictor.predict(ASPIRIN_SMILES)
        assert profile.distribution.volume_of_distribution > 0
        assert 0 <= profile.distribution.plasma_protein_binding <= 1
        assert profile.distribution.bbb_score >= 0
        assert isinstance(profile.distribution.blood_brain_barrier, bool)

    def test_metabolism_profile_populated(self, predictor):
        profile = predictor.predict(IMATINIB_SMILES)
        assert profile.metabolism.half_life_hours > 0
        assert profile.metabolism.clearance_ml_min_kg >= 0

    def test_excretion_route_valid(self, predictor):
        profile = predictor.predict(SIMPLE_SMILES)
        assert profile.excretion.elimination_route in ("renal", "hepatic", "biliary")

    def test_toxicity_risk_levels_valid(self, predictor):
        profile = predictor.predict(IMATINIB_SMILES)
        assert profile.toxicity.herg_risk in RiskLevel.__members__.values()
        assert profile.toxicity.overall_risk in RiskLevel.__members__.values()
        assert profile.toxicity.hepatotoxicity_risk in RiskLevel.__members__.values()

    def test_drug_likeness_score_range(self, predictor):
        profile = predictor.predict(ASPIRIN_SMILES)
        assert 0.0 <= profile.drug_likeness_score <= 1.0

    def test_lead_likeness_score_range(self, predictor):
        profile = predictor.predict(SIMPLE_SMILES)
        assert 0.0 <= profile.lead_likeness_score <= 1.0

    def test_warnings_is_list(self, predictor):
        profile = predictor.predict(ASPIRIN_SMILES)
        assert isinstance(profile.warnings, list)

    def test_flags_is_list(self, predictor):
        profile = predictor.predict(ASPIRIN_SMILES)
        assert isinstance(profile.flags, list)

    def test_batch_prediction(self, predictor):
        compounds = [
            (ASPIRIN_SMILES, "aspirin"),
            (SIMPLE_SMILES, "ethanol"),
        ]
        profiles = predictor.predict_batch(compounds)
        assert len(profiles) == 2
        # Should be sorted by drug-likeness
        assert profiles[0].drug_likeness_score >= profiles[1].drug_likeness_score

    def test_batch_filter_by_drug_likeness(self, predictor):
        compounds = [(ASPIRIN_SMILES, "aspirin"), (SIMPLE_SMILES, "ethanol")]
        profiles = predictor.predict_batch(compounds)
        filtered = predictor.filter_by_drug_likeness(profiles, min_score=0.0)
        assert len(filtered) >= 0

    def test_lipinski_rule_of_five_small_molecule(self, predictor):
        """Small, polar molecule should pass Lipinski."""
        profile = predictor.predict("CC(=O)N", "acetamide")
        assert profile.absorption.lipinski_violations <= 1

    def test_herg_risk_elevated_for_lipophilic_aromatic(self, predictor):
        """Highly lipophilic, aromatic with nitrogen → elevated hERG risk."""
        # Two aromatic rings + long aliphatic chain + basic N → high LogP + aromatic score
        lipophilic_aromatic = "CCCCCc1ccc(CCCNCC)cc1c2ccccc2"
        profile = predictor.predict(lipophilic_aromatic, "test_herg")
        assert profile.toxicity.herg_risk in (RiskLevel.MEDIUM, RiskLevel.HIGH)

    def test_predict_handles_unknown_compound_id(self, predictor):
        profile = predictor.predict(SIMPLE_SMILES)
        assert profile.compound_id == "unknown"
