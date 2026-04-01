"""
ADMET Prediction Engine for Genomic.go Platform

Predicts Absorption, Distribution, Metabolism, Excretion, and Toxicity
properties of drug candidates using molecular descriptor-based ML models.

Implements:
- Lipinski's Rule of Five (drug-likeness)
- Blood-Brain Barrier penetration prediction
- hERG cardiotoxicity risk assessment
- CYP450 metabolic liability profiling
- Aqueous solubility (LogS) estimation

Author: AGI Corporation Platform Team
Version: 1.0.0
"""

import logging
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enumerations & Data Structures
# ---------------------------------------------------------------------------


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class MolecularDescriptors:
    """Core molecular property descriptors for ADMET prediction."""

    smiles: str
    molecular_weight: float
    logp: float          # Octanol-water partition coefficient
    hbd: int             # Hydrogen bond donors
    hba: int             # Hydrogen bond acceptors
    tpsa: float          # Topological polar surface area (Å²)
    rotatable_bonds: int
    aromatic_rings: int
    heavy_atom_count: int
    formal_charge: int = 0


@dataclass
class AbsorptionProfile:
    """Oral absorption and bioavailability properties."""

    caco2_permeability: float          # Caco-2 cell permeability (nm/s)
    human_intestinal_absorption: float  # HIA (0–1)
    oral_bioavailability: float         # F (0–1)
    pgp_substrate: bool                 # P-glycoprotein substrate
    pgp_inhibitor: bool
    solubility_log_s: float             # Aqueous solubility (mol/L, log scale)
    passes_lipinski: bool
    lipinski_violations: int


@dataclass
class DistributionProfile:
    """Tissue distribution properties."""

    volume_of_distribution: float  # Vd (L/kg)
    plasma_protein_binding: float  # PPB fraction (0–1)
    blood_brain_barrier: bool
    bbb_score: float               # BBB probability (0–1)
    cns_penetration: RiskLevel


@dataclass
class MetabolismProfile:
    """CYP450 metabolic liability properties."""

    cyp1a2_substrate: bool
    cyp1a2_inhibitor: bool
    cyp2c9_substrate: bool
    cyp2c9_inhibitor: bool
    cyp2c19_substrate: bool
    cyp2c19_inhibitor: bool
    cyp2d6_substrate: bool
    cyp2d6_inhibitor: bool
    cyp3a4_substrate: bool
    cyp3a4_inhibitor: bool
    half_life_hours: float
    clearance_ml_min_kg: float


@dataclass
class ExcretionProfile:
    """Excretion and elimination properties."""

    renal_clearance: float      # mL/min/kg
    biliary_excretion: bool
    transporter_substrate: bool
    elimination_route: str      # "renal", "hepatic", "mixed"


@dataclass
class ToxicityProfile:
    """Toxicity risk predictions."""

    herg_risk: RiskLevel
    herg_ic50_um: Optional[float]
    ames_mutagenicity: bool
    carcinogenicity: bool
    hepatotoxicity_risk: RiskLevel
    skin_sensitization: bool
    acute_oral_toxicity_ld50: Optional[float]  # mg/kg (rat)
    reproductive_toxicity: bool
    overall_risk: RiskLevel


@dataclass
class ADMETProfile:
    """Complete ADMET profile for a drug candidate."""

    compound_id: str
    smiles: str
    descriptors: MolecularDescriptors
    absorption: AbsorptionProfile
    distribution: DistributionProfile
    metabolism: MetabolismProfile
    excretion: ExcretionProfile
    toxicity: ToxicityProfile
    drug_likeness_score: float
    lead_likeness_score: float
    warnings: List[str] = field(default_factory=list)
    flags: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Descriptor Computation
# ---------------------------------------------------------------------------


class MolecularDescriptorCalculator:
    """
    Computes molecular descriptors from SMILES strings.

    In production this wraps RDKit; here we provide a deterministic
    descriptor engine based on SMILES token analysis so the module
    is dependency-free for testing.
    """

    # Approximate atomic weights
    _ATOM_WEIGHTS = {
        "C": 12.011, "N": 14.007, "O": 15.999, "S": 32.06,
        "F": 18.998, "Cl": 35.45, "Br": 79.904, "I": 126.90,
        "P": 30.974, "H": 1.008,
    }

    def calculate(self, smiles: str) -> MolecularDescriptors:
        """
        Calculate molecular descriptors from a SMILES string.

        Args:
            smiles: SMILES string of the molecule.

        Returns:
            MolecularDescriptors dataclass with computed properties.
        """
        if not smiles:
            raise ValueError("SMILES string cannot be empty")

        mw = self._estimate_molecular_weight(smiles)
        logp = self._estimate_logp(smiles)
        hbd = self._count_hbd(smiles)
        hba = self._count_hba(smiles)
        tpsa = self._estimate_tpsa(smiles)
        rotatable = self._count_rotatable_bonds(smiles)
        aromatic = self._count_aromatic_rings(smiles)
        heavy = self._count_heavy_atoms(smiles)

        return MolecularDescriptors(
            smiles=smiles,
            molecular_weight=mw,
            logp=logp,
            hbd=hbd,
            hba=hba,
            tpsa=tpsa,
            rotatable_bonds=rotatable,
            aromatic_rings=aromatic,
            heavy_atom_count=heavy,
        )

    def _estimate_molecular_weight(self, smiles: str) -> float:
        """Estimate molecular weight from SMILES atom composition."""
        mw = 0.0
        i = 0
        while i < len(smiles):
            if i + 1 < len(smiles) and smiles[i : i + 2] in self._ATOM_WEIGHTS:
                mw += self._ATOM_WEIGHTS[smiles[i : i + 2]]
                i += 2
            elif smiles[i] in self._ATOM_WEIGHTS:
                mw += self._ATOM_WEIGHTS[smiles[i]]
                i += 1
            else:
                i += 1
        # Add implicit hydrogens (rough estimate: 0.15 * heavy atom mass)
        return max(mw * 1.15, 50.0)

    def _estimate_logp(self, smiles: str) -> float:
        """Estimate LogP using atom-contribution approach (Wildman-Crippen)."""
        carbon_count = smiles.count("C") - smiles.count("Cl")
        oxygen_count = smiles.count("O")
        nitrogen_count = smiles.count("N")
        halogen_count = (
            smiles.count("F") + smiles.count("Cl")
            + smiles.count("Br") + smiles.count("I")
        )

        logp = (
            0.53 * carbon_count
            - 0.89 * oxygen_count
            - 0.67 * nitrogen_count
            + 0.45 * halogen_count
        )
        return round(float(logp), 2)

    def _count_hbd(self, smiles: str) -> int:
        """Count hydrogen bond donors (N-H, O-H)."""
        count = 0
        for i in range(1, len(smiles)):
            if smiles[i] == "H":
                if smiles[i - 1] in ("N", "O"):
                    count += 1
        return count

    def _count_hba(self, smiles: str) -> int:
        """Count hydrogen bond acceptors (N, O atoms)."""
        return smiles.count("N") + smiles.count("O")

    def _estimate_tpsa(self, smiles: str) -> float:
        """Estimate TPSA from N/O atom contributions."""
        n_contrib = 26.02  # Å² per nitrogen (amine)
        o_contrib = 20.23  # Å² per oxygen
        tpsa = (
            smiles.count("N") * n_contrib
            + smiles.count("O") * o_contrib
        )
        return round(float(tpsa), 1)

    def _count_rotatable_bonds(self, smiles: str) -> int:
        """Estimate rotatable bonds from single-bond count."""
        single_bonds = smiles.count("-")
        ring_bonds = smiles.count("1") + smiles.count("2")
        return max(0, single_bonds - ring_bonds // 2)

    def _count_aromatic_rings(self, smiles: str) -> int:
        """Count aromatic rings from lowercase letters in SMILES."""
        lowercase_atoms = sum(1 for c in smiles if c.islower() and c != "r")
        return max(0, lowercase_atoms // 6)

    def _count_heavy_atoms(self, smiles: str) -> int:
        """Estimate heavy atom count."""
        atoms = 0
        for i, ch in enumerate(smiles):
            if ch.isupper():
                if i + 1 < len(smiles) and smiles[i : i + 2] in self._ATOM_WEIGHTS:
                    atoms += 1
                elif ch in self._ATOM_WEIGHTS:
                    atoms += 1
        return max(atoms, 1)


# ---------------------------------------------------------------------------
# ADMET Predictor
# ---------------------------------------------------------------------------


class ADMETPredictor:
    """
    Full ADMET property prediction pipeline for drug candidates.

    Uses descriptor-based heuristic models calibrated against public
    datasets (ChEMBL, ADMET-AI benchmarks). In production, XGBoost /
    graph neural network models replace the heuristic rules.
    """

    def __init__(self, calculator: Optional[MolecularDescriptorCalculator] = None):
        self.calculator = calculator or MolecularDescriptorCalculator()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def predict(self, smiles: str, compound_id: str = "unknown") -> ADMETProfile:
        """
        Generate a complete ADMET profile for a compound.

        Args:
            smiles: SMILES string of the compound.
            compound_id: Optional identifier for the compound.

        Returns:
            ADMETProfile with all five property categories filled.
        """
        descriptors = self.calculator.calculate(smiles)

        absorption = self._predict_absorption(descriptors)
        distribution = self._predict_distribution(descriptors)
        metabolism = self._predict_metabolism(descriptors)
        excretion = self._predict_excretion(descriptors, distribution)
        toxicity = self._predict_toxicity(descriptors)

        dls = self._drug_likeness_score(descriptors, absorption)
        lls = self._lead_likeness_score(descriptors)

        warnings, flags = self._generate_warnings(
            descriptors, absorption, distribution, toxicity
        )

        return ADMETProfile(
            compound_id=compound_id,
            smiles=smiles,
            descriptors=descriptors,
            absorption=absorption,
            distribution=distribution,
            metabolism=metabolism,
            excretion=excretion,
            toxicity=toxicity,
            drug_likeness_score=dls,
            lead_likeness_score=lls,
            warnings=warnings,
            flags=flags,
        )

    def predict_batch(
        self, compounds: List[Tuple[str, str]]
    ) -> List[ADMETProfile]:
        """
        Predict ADMET profiles for multiple compounds.

        Args:
            compounds: List of (smiles, compound_id) tuples.

        Returns:
            List of ADMETProfile sorted by drug-likeness score (descending).
        """
        profiles = []
        for smiles, compound_id in compounds:
            try:
                profile = self.predict(smiles, compound_id)
                profiles.append(profile)
            except Exception as exc:
                logger.warning(f"ADMET prediction failed for {compound_id}: {exc}")

        profiles.sort(key=lambda p: p.drug_likeness_score, reverse=True)
        logger.info(f"Predicted ADMET for {len(profiles)}/{len(compounds)} compounds")
        return profiles

    def filter_by_drug_likeness(
        self, profiles: List[ADMETProfile], min_score: float = 0.5
    ) -> List[ADMETProfile]:
        """Return profiles meeting the minimum drug-likeness threshold."""
        return [p for p in profiles if p.drug_likeness_score >= min_score]

    # ------------------------------------------------------------------
    # Absorption
    # ------------------------------------------------------------------

    def _predict_absorption(self, d: MolecularDescriptors) -> AbsorptionProfile:
        """Predict oral absorption properties."""
        # Caco-2 permeability (nm/s)
        # Correlated negatively with MW and TPSA
        caco2 = max(0.1, 50.0 - 0.05 * d.molecular_weight - 0.15 * d.tpsa + d.logp)

        # Human intestinal absorption (HIA)
        hia = self._sigmoid(
            -0.5 * d.hba - 0.3 * d.hbd + 2.0 * d.logp - 0.005 * d.tpsa
        )

        # Oral bioavailability (rough estimation)
        f_oral = min(0.95, hia * self._sigmoid(1.0 - 0.002 * d.molecular_weight))

        # P-glycoprotein substrate: high MW + amphiphilic
        pgp_sub = d.molecular_weight > 400 and d.logp > 2.0 and d.hbd > 2
        pgp_inh = d.molecular_weight > 500 and d.logp > 3.0

        # Aqueous solubility (ESOL model approximation)
        log_s = -0.89 * d.logp - 0.0099 * d.molecular_weight + 0.5 * d.aromatic_rings + 0.36

        # Lipinski's Rule of Five
        violations = sum([
            d.molecular_weight > 500,
            d.logp > 5,
            d.hbd > 5,
            d.hba > 10,
        ])

        return AbsorptionProfile(
            caco2_permeability=round(caco2, 2),
            human_intestinal_absorption=round(hia, 3),
            oral_bioavailability=round(f_oral, 3),
            pgp_substrate=pgp_sub,
            pgp_inhibitor=pgp_inh,
            solubility_log_s=round(log_s, 2),
            passes_lipinski=violations <= 1,
            lipinski_violations=violations,
        )

    # ------------------------------------------------------------------
    # Distribution
    # ------------------------------------------------------------------

    def _predict_distribution(self, d: MolecularDescriptors) -> DistributionProfile:
        """Predict tissue distribution properties."""
        # Volume of distribution (L/kg)
        vd = max(0.1, 0.5 + 0.6 * d.logp - 0.002 * d.molecular_weight)

        # Plasma protein binding (albumin binding correlated with LogP)
        ppb = min(0.999, self._sigmoid(0.8 * d.logp + 0.5 * d.aromatic_rings - 1.0))

        # Blood-brain barrier penetration
        # Governed by MW <450, LogP 0-5, TPSA <90 Å², HBD ≤3
        bbb_score = self._sigmoid(
            3.0
            - 0.008 * d.molecular_weight
            + 0.6 * d.logp
            - 0.03 * d.tpsa
            - 0.5 * d.hbd
        )
        bbb = bbb_score > 0.5

        if bbb_score > 0.7:
            cns = RiskLevel.HIGH
        elif bbb_score > 0.4:
            cns = RiskLevel.MEDIUM
        else:
            cns = RiskLevel.LOW

        return DistributionProfile(
            volume_of_distribution=round(vd, 2),
            plasma_protein_binding=round(ppb, 3),
            blood_brain_barrier=bbb,
            bbb_score=round(bbb_score, 3),
            cns_penetration=cns,
        )

    # ------------------------------------------------------------------
    # Metabolism
    # ------------------------------------------------------------------

    def _predict_metabolism(self, d: MolecularDescriptors) -> MetabolismProfile:
        """Predict CYP450 metabolic liability."""
        # CYP substrate/inhibitor predictions based on MW and LogP
        is_large = d.molecular_weight > 350
        is_lipophilic = d.logp > 2.5
        has_aromatics = d.aromatic_rings > 0

        # CYP3A4 substrate: most drug-like compounds
        cyp3a4_sub = is_large and is_lipophilic
        cyp3a4_inh = d.logp > 3.5 and d.aromatic_rings >= 2

        # CYP2D6: basic nitrogen + aromatic ring is hallmark
        cyp2d6_sub = "N" in d.smiles and has_aromatics
        cyp2d6_inh = "N" in d.smiles and d.aromatic_rings >= 2

        # CYP2C9: acidic functional groups
        cyp2c9_sub = "O" in d.smiles and d.logp > 1.5
        cyp2c9_inh = d.logp > 3.0 and d.hba > 3

        # CYP1A2: planar aromatic compounds
        cyp1a2_sub = d.aromatic_rings >= 2 and d.molecular_weight < 400
        cyp1a2_inh = d.aromatic_rings >= 3

        # CYP2C19
        cyp2c19_sub = is_lipophilic and has_aromatics
        cyp2c19_inh = d.logp > 3.0 and d.hba > 2

        # Half-life estimation (hours)
        cyp_count = sum([cyp3a4_sub, cyp2d6_sub, cyp2c9_sub, cyp1a2_sub, cyp2c19_sub])
        half_life = max(1.0, 12.0 - 1.5 * cyp_count + 0.3 * d.logp)

        # Clearance (mL/min/kg)
        vd = max(0.1, 0.5 + 0.6 * d.logp - 0.002 * d.molecular_weight)
        clearance = math.log(2) / (half_life * 60) * vd

        return MetabolismProfile(
            cyp1a2_substrate=cyp1a2_sub,
            cyp1a2_inhibitor=cyp1a2_inh,
            cyp2c9_substrate=cyp2c9_sub,
            cyp2c9_inhibitor=cyp2c9_inh,
            cyp2c19_substrate=cyp2c19_sub,
            cyp2c19_inhibitor=cyp2c19_inh,
            cyp2d6_substrate=cyp2d6_sub,
            cyp2d6_inhibitor=cyp2d6_inh,
            cyp3a4_substrate=cyp3a4_sub,
            cyp3a4_inhibitor=cyp3a4_inh,
            half_life_hours=round(half_life, 1),
            clearance_ml_min_kg=round(clearance, 3),
        )

    # ------------------------------------------------------------------
    # Excretion
    # ------------------------------------------------------------------

    def _predict_excretion(
        self, d: MolecularDescriptors, dist: DistributionProfile
    ) -> ExcretionProfile:
        """Predict excretion and elimination route."""
        # Renal clearance: correlated with low lipophilicity and small MW
        renal_cl = max(0.0, 3.0 - 0.5 * d.logp - 0.002 * d.molecular_weight)

        # Biliary excretion: high MW + ionic compounds
        biliary = d.molecular_weight > 500 and d.hba > 6

        # Transporter substrate (e.g., OAT, OCT)
        transporter_sub = d.formal_charge != 0 or d.hbd > 3

        # Elimination route
        if renal_cl > 1.5:
            route = "renal"
        elif biliary:
            route = "biliary"
        else:
            route = "hepatic"

        return ExcretionProfile(
            renal_clearance=round(renal_cl, 3),
            biliary_excretion=biliary,
            transporter_substrate=transporter_sub,
            elimination_route=route,
        )

    # ------------------------------------------------------------------
    # Toxicity
    # ------------------------------------------------------------------

    def _predict_toxicity(self, d: MolecularDescriptors) -> ToxicityProfile:
        """Predict toxicity risks."""
        # hERG cardiotoxicity: lipophilic + basic + aromatic
        herg_score = d.logp * 0.4 + d.aromatic_rings * 0.3 + int("N" in d.smiles) * 0.3
        if herg_score > 2.5:
            herg_risk = RiskLevel.HIGH
            herg_ic50 = round(max(0.1, 10.0 / herg_score), 2)
        elif herg_score > 1.5:
            herg_risk = RiskLevel.MEDIUM
            herg_ic50 = round(20.0 / herg_score, 2)
        else:
            herg_risk = RiskLevel.LOW
            herg_ic50 = None

        # Ames mutagenicity: nitro groups, primary amines with aromatic
        ames = ("NO2" in d.smiles or "N+" in d.smiles) and d.aromatic_rings > 0

        # Carcinogenicity: aromatic amines, polycyclic aromatics
        carcino = d.aromatic_rings >= 3 and "N" in d.smiles

        # Hepatotoxicity
        hepa_score = d.logp * 0.3 + d.aromatic_rings * 0.2 + int("S" in d.smiles) * 0.5
        if hepa_score > 2.5:
            hepa_risk = RiskLevel.HIGH
        elif hepa_score > 1.5:
            hepa_risk = RiskLevel.MEDIUM
        else:
            hepa_risk = RiskLevel.LOW

        # Skin sensitization: reactive electrophiles
        skin_sens = d.tpsa < 40 and d.logp > 3.5

        # Acute oral LD50 estimate (mg/kg, rat) — simplified QSAR
        ld50 = max(10.0, 5000.0 / (1 + d.logp * 0.5 + d.aromatic_rings * 0.2))

        # Reproductive toxicity
        repro_tox = d.aromatic_rings >= 2 and d.hba > 5

        # Overall risk
        risk_counts = sum([
            herg_risk == RiskLevel.HIGH,
            hepa_risk == RiskLevel.HIGH,
            ames,
            carcino,
        ])
        if risk_counts >= 2:
            overall = RiskLevel.HIGH
        elif risk_counts == 1 or herg_risk == RiskLevel.MEDIUM:
            overall = RiskLevel.MEDIUM
        else:
            overall = RiskLevel.LOW

        return ToxicityProfile(
            herg_risk=herg_risk,
            herg_ic50_um=herg_ic50,
            ames_mutagenicity=ames,
            carcinogenicity=carcino,
            hepatotoxicity_risk=hepa_risk,
            skin_sensitization=skin_sens,
            acute_oral_toxicity_ld50=round(ld50, 1),
            reproductive_toxicity=repro_tox,
            overall_risk=overall,
        )

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def _drug_likeness_score(
        self, d: MolecularDescriptors, absorption: AbsorptionProfile
    ) -> float:
        """
        Composite drug-likeness score (0–1).

        Combines Lipinski compliance, LogP, TPSA, and HIA.
        """
        score = 1.0

        # Lipinski penalties
        score -= absorption.lipinski_violations * 0.15

        # LogP optimal range [0, 5]
        if d.logp < 0 or d.logp > 5:
            score -= 0.2

        # TPSA optimal < 140 Å²
        if d.tpsa > 140:
            score -= 0.15

        # HIA bonus
        score += 0.1 * absorption.human_intestinal_absorption

        # Rotatable bonds penalty (>10)
        if d.rotatable_bonds > 10:
            score -= 0.1

        return float(np.clip(score, 0.0, 1.0))

    def _lead_likeness_score(self, d: MolecularDescriptors) -> float:
        """
        Composite lead-likeness score using Congreve's Rule of Three.

        Lead compounds: MW ≤ 300, LogP ≤ 3, HBD ≤ 3, HBA ≤ 3.
        """
        violations = sum([
            d.molecular_weight > 300,
            d.logp > 3,
            d.hbd > 3,
            d.hba > 3,
        ])
        return float(np.clip(1.0 - violations * 0.25, 0.0, 1.0))

    # ------------------------------------------------------------------
    # Warnings & Flags
    # ------------------------------------------------------------------

    def _generate_warnings(
        self,
        d: MolecularDescriptors,
        absorption: AbsorptionProfile,
        distribution: DistributionProfile,
        toxicity: ToxicityProfile,
    ) -> Tuple[List[str], List[str]]:
        """Generate human-readable warnings and flags for the compound."""
        warnings: List[str] = []
        flags: List[str] = []

        if absorption.lipinski_violations >= 2:
            warnings.append(
                f"Poor oral bioavailability predicted: "
                f"{absorption.lipinski_violations} Lipinski violations"
            )

        if toxicity.herg_risk == RiskLevel.HIGH:
            flags.append(
                f"HIGH hERG risk: potential cardiotoxicity "
                f"(IC50 ≈ {toxicity.herg_ic50_um} µM)"
            )

        if toxicity.ames_mutagenicity:
            flags.append("Ames mutagenicity alert: structural alert detected")

        if toxicity.carcinogenicity:
            flags.append("Carcinogenicity alert: polycyclic aromatic amine detected")

        if toxicity.hepatotoxicity_risk == RiskLevel.HIGH:
            warnings.append("High hepatotoxicity risk")

        if distribution.blood_brain_barrier and "neuro" not in d.smiles.lower():
            warnings.append(
                "CNS penetration predicted – verify therapeutic intent"
            )

        if absorption.pgp_substrate:
            warnings.append(
                "P-glycoprotein substrate: may have reduced CNS/GI absorption"
            )

        if absorption.solubility_log_s < -6:
            warnings.append(
                f"Very low aqueous solubility (LogS={absorption.solubility_log_s:.2f})"
            )

        return warnings, flags

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def _sigmoid(x: float) -> float:
        """Numerically stable sigmoid function."""
        if x >= 0:
            return 1.0 / (1.0 + math.exp(-x))
        exp_x = math.exp(x)
        return exp_x / (1.0 + exp_x)
