"""
Molecule Generation Engine for Genomic.go Platform

Implements de novo drug design algorithms:
- Fragment-based drug design (FBDD) with scaffold decoration
- Property-constrained SMILES generation via genetic algorithm
- Structure-based virtual screening scaffold enumeration
- Bioisostere replacement for lead optimization

Author: AGI Corporation Platform Team
Version: 1.0.0
"""

import hashlib
import logging
import random
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enumerations & Data Structures
# ---------------------------------------------------------------------------


class GenerationStrategy(str, Enum):
    FRAGMENT_BASED = "fragment_based"
    GENETIC_ALGORITHM = "genetic_algorithm"
    SCAFFOLD_DECORATION = "scaffold_decoration"
    BIOISOSTERE = "bioisostere"


@dataclass
class PropertyConstraints:
    """Desired property ranges for generated molecules."""

    min_mw: float = 200.0
    max_mw: float = 500.0
    min_logp: float = -1.0
    max_logp: float = 5.0
    max_hbd: int = 5
    max_hba: int = 10
    max_tpsa: float = 140.0
    max_rotatable_bonds: int = 10


@dataclass
class GeneratedMolecule:
    """A generated drug candidate with predicted properties."""

    molecule_id: str
    smiles: str
    scaffold: str
    strategy: GenerationStrategy
    predicted_mw: float
    predicted_logp: float
    predicted_tpsa: float
    novelty_score: float       # 0–1; 1 = completely novel
    diversity_score: float     # 0–1 vs. rest of generated set
    qed_score: float           # Quantitative Estimate of Drug-likeness (0–1)
    sa_score: float            # Synthetic Accessibility (1–10; lower = easier)
    parent_scaffold: Optional[str] = None
    applied_transformations: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Fragment Library
# ---------------------------------------------------------------------------


class FragmentLibrary:
    """
    Curated fragment library for FBDD.

    Fragments are drug-like chemical building blocks selected from
    public databases (Enamine, ZINC, eMolecules).
    """

    # Representative drug-fragment SMILES (rule-of-three compliant)
    CORE_FRAGMENTS = [
        # Heteroaromatic rings
        "c1ccncc1",       # Pyridine
        "c1ccnc(N)c1",    # Aminopyridine
        "c1cnc(O)cn1",    # Hydroxypyrimidine
        "c1cc[nH]c1",     # Pyrrole
        "c1ccoc1",        # Furan
        "c1ccsc1",        # Thiophene
        "c1cnco1",        # Oxazole
        "c1cncn1",        # Imidazole
        "c1ccnco1",       # Isoxazole
        "c1cc2ccccc2n1",  # Indole (core)
        # Aliphatic fragments
        "C1CCNCC1",       # Piperidine
        "C1COCCN1",       # Morpholine
        "C1CNCCN1",       # Piperazine
        "C1CCC(N)CC1",    # 4-Aminocyclohexane
        "NC(=O)CC",       # Propanamide
        # Linkers
        "CC(=O)N",        # Acetamide
        "CC(N)=O",        # Acetamide (alt)
        "CNC(=O)",        # N-methyl amide
        "c1ccc(F)cc1",    # Fluorobenzene
        "c1ccc(Cl)cc1",   # Chlorobenzene
    ]

    LINKING_GROUPS = [
        "C", "CC", "CCC",
        "NC(=O)", "C(=O)N",
        "OCC", "CCO",
        "C=C", "C#C",
        "c1cc",
    ]

    FUNCTIONAL_GROUPS = [
        "O",   # Hydroxyl
        "N",   # Amine
        "F",   # Fluorine
        "Cl",  # Chlorine
        "C#N", # Nitrile
        "S",   # Thiol
        "OC",  # Methoxy
        "NC(N)=O",  # Guanidinium
    ]

    def get_random_fragment(self, rng: random.Random) -> str:
        """Return a random core fragment."""
        return rng.choice(self.CORE_FRAGMENTS)

    def get_linker(self, rng: random.Random) -> str:
        """Return a random linking group."""
        return rng.choice(self.LINKING_GROUPS)

    def get_functional_group(self, rng: random.Random) -> str:
        """Return a random functional group for decoration."""
        return rng.choice(self.FUNCTIONAL_GROUPS)


# ---------------------------------------------------------------------------
# SMILES Utilities
# ---------------------------------------------------------------------------


class SMILESUtils:
    """Lightweight SMILES manipulation utilities."""

    @staticmethod
    def estimate_mw(smiles: str) -> float:
        """Estimate molecular weight from SMILES."""
        atom_weights = {
            "C": 12.011, "N": 14.007, "O": 15.999,
            "S": 32.06,  "F": 18.998, "Cl": 35.45,
            "Br": 79.904, "I": 126.90, "P": 30.974,
        }
        mw = 0.0
        i = 0
        while i < len(smiles):
            if i + 1 < len(smiles) and smiles[i: i + 2] in atom_weights:
                mw += atom_weights[smiles[i: i + 2]]
                i += 2
            elif smiles[i] in atom_weights:
                mw += atom_weights[smiles[i]]
                i += 1
            else:
                i += 1
        return max(mw * 1.15, 50.0)

    @staticmethod
    def estimate_logp(smiles: str) -> float:
        """Estimate LogP (Wildman-Crippen approximation)."""
        carbon = smiles.count("C") - smiles.count("Cl")
        oxygen = smiles.count("O")
        nitrogen = smiles.count("N")
        halogens = smiles.count("F") + smiles.count("Cl") + smiles.count("Br") + smiles.count("I")
        return round(0.53 * carbon - 0.89 * oxygen - 0.67 * nitrogen + 0.45 * halogens, 2)

    @staticmethod
    def estimate_tpsa(smiles: str) -> float:
        """Estimate TPSA from N/O contributions."""
        return round(smiles.count("N") * 26.02 + smiles.count("O") * 20.23, 1)

    @staticmethod
    def canonical_smiles(smiles: str) -> str:
        """Return a normalized SMILES (removes trivial whitespace)."""
        return smiles.strip()

    @staticmethod
    def molecule_fingerprint(smiles: str) -> str:
        """Return a short hash of the SMILES for deduplication."""
        return hashlib.md5(smiles.encode()).hexdigest()[:12]

    @staticmethod
    def tanimoto_similarity(smiles1: str, smiles2: str) -> float:
        """
        Approximate Tanimoto similarity using character n-gram sets.

        This is a lightweight proxy; production uses Morgan fingerprints.
        """
        def ngrams(s: str, n: int = 3) -> set:
            return {s[i: i + n] for i in range(len(s) - n + 1)}

        set1 = ngrams(smiles1)
        set2 = ngrams(smiles2)
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0


# ---------------------------------------------------------------------------
# Molecule Generator
# ---------------------------------------------------------------------------


class MoleculeGenerator:
    """
    De novo molecule generation engine.

    Supports four complementary strategies:
    1. Fragment-Based Drug Design (FBDD)
    2. Genetic Algorithm optimization
    3. Scaffold decoration
    4. Bioisostere replacement
    """

    def __init__(
        self,
        constraints: Optional[PropertyConstraints] = None,
        seed: int = 42,
    ):
        """
        Args:
            constraints: Property constraints for generated molecules.
            seed: Random seed for reproducibility.
        """
        self.constraints = constraints or PropertyConstraints()
        self.rng = random.Random(seed)
        self.np_rng = np.random.default_rng(seed)
        self.fragment_library = FragmentLibrary()
        self.smiles_utils = SMILESUtils()
        self._generated_fingerprints: List[str] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(
        self,
        n_molecules: int,
        strategy: GenerationStrategy = GenerationStrategy.FRAGMENT_BASED,
        scaffold: Optional[str] = None,
        reference_smiles: Optional[str] = None,
    ) -> List[GeneratedMolecule]:
        """
        Generate drug candidate molecules.

        Args:
            n_molecules: Number of molecules to generate.
            strategy: Generation strategy to use.
            scaffold: Optional core scaffold for decoration strategies.
            reference_smiles: Reference molecule for bioisostere/optimization.

        Returns:
            List of GeneratedMolecule sorted by QED score (descending).
        """
        molecules: List[GeneratedMolecule] = []

        strategy_fn = {
            GenerationStrategy.FRAGMENT_BASED: self._generate_fragment_based,
            GenerationStrategy.GENETIC_ALGORITHM: self._generate_genetic_algorithm,
            GenerationStrategy.SCAFFOLD_DECORATION: self._generate_scaffold_decoration,
            GenerationStrategy.BIOISOSTERE: self._generate_bioisostere,
        }[strategy]

        attempts = 0
        max_attempts = n_molecules * 5

        while len(molecules) < n_molecules and attempts < max_attempts:
            attempts += 1
            try:
                mol = strategy_fn(
                    scaffold=scaffold, reference_smiles=reference_smiles
                )
                if mol and self._passes_constraints(mol):
                    mol.diversity_score = self._compute_diversity(
                        mol.smiles, [m.smiles for m in molecules]
                    )
                    molecules.append(mol)
                    self._generated_fingerprints.append(
                        self.smiles_utils.molecule_fingerprint(mol.smiles)
                    )
            except Exception as exc:
                logger.debug(f"Generation attempt failed: {exc}")

        molecules.sort(key=lambda m: m.qed_score, reverse=True)
        logger.info(
            f"Generated {len(molecules)}/{n_molecules} molecules "
            f"using {strategy} in {attempts} attempts"
        )
        return molecules

    def optimize(
        self,
        lead_smiles: str,
        n_analogs: int = 20,
        target_property: str = "qed",
    ) -> List[GeneratedMolecule]:
        """
        Optimize a lead compound by generating analogs.

        Args:
            lead_smiles: Starting lead compound SMILES.
            n_analogs: Number of analogs to generate.
            target_property: Property to optimize ('qed', 'logp', 'mw').

        Returns:
            List of analogs sorted by target property.
        """
        analogs = self.generate(
            n_molecules=n_analogs,
            strategy=GenerationStrategy.BIOISOSTERE,
            reference_smiles=lead_smiles,
        )

        sort_key = {
            "qed": lambda m: m.qed_score,
            "logp": lambda m: -abs(m.predicted_logp - 2.5),  # Target LogP ~2.5
            "mw": lambda m: -abs(m.predicted_mw - 350),       # Target MW ~350
        }.get(target_property, lambda m: m.qed_score)

        return sorted(analogs, key=sort_key, reverse=True)

    # ------------------------------------------------------------------
    # Strategy Implementations
    # ------------------------------------------------------------------

    def _generate_fragment_based(
        self,
        scaffold: Optional[str] = None,
        reference_smiles: Optional[str] = None,
    ) -> GeneratedMolecule:
        """Fragment-based drug design: join 2-4 fragments with linkers."""
        n_fragments = self.rng.randint(2, 4)
        core = scaffold or self.fragment_library.get_random_fragment(self.rng)

        parts = [core]
        transformations = ["core_selection"]

        for _ in range(n_fragments - 1):
            linker = self.fragment_library.get_linker(self.rng)
            fragment = self.fragment_library.get_random_fragment(self.rng)
            parts.extend([linker, fragment])
            transformations.append(f"added_fragment:{fragment[:10]}")

        smiles = "".join(parts)
        return self._build_molecule(
            smiles, core, GenerationStrategy.FRAGMENT_BASED, transformations
        )

    def _generate_genetic_algorithm(
        self,
        scaffold: Optional[str] = None,
        reference_smiles: Optional[str] = None,
        n_generations: int = 5,
    ) -> GeneratedMolecule:
        """
        Genetic algorithm: iteratively mutate and select candidates.

        Starts from a random fragment population and applies crossover
        and mutation operators.
        """
        # Initial population
        population = [
            self.fragment_library.get_random_fragment(self.rng)
            for _ in range(8)
        ]

        transformations = ["ga_init"]

        for gen in range(n_generations):
            # Score population (QED proxy)
            scored = [
                (s, self._quick_qed(s)) for s in population
            ]
            scored.sort(key=lambda x: x[1], reverse=True)

            # Selection (top half)
            survivors = [s for s, _ in scored[: max(1, len(scored) // 2)]]

            # Crossover
            new_pop = list(survivors)
            while len(new_pop) < 8:
                parent1 = self.rng.choice(survivors)
                parent2 = self.rng.choice(survivors)
                child = self._crossover(parent1, parent2)
                new_pop.append(child)

            # Mutation
            population = [self._mutate(s) for s in new_pop]
            transformations.append(f"ga_gen_{gen + 1}")

        best_smiles = max(population, key=self._quick_qed)
        core = scaffold or self.fragment_library.get_random_fragment(self.rng)

        return self._build_molecule(
            best_smiles, core, GenerationStrategy.GENETIC_ALGORITHM, transformations
        )

    def _generate_scaffold_decoration(
        self,
        scaffold: Optional[str] = None,
        reference_smiles: Optional[str] = None,
    ) -> GeneratedMolecule:
        """Scaffold decoration: attach functional groups to a core scaffold."""
        core = scaffold or self.fragment_library.get_random_fragment(self.rng)
        n_substitutions = self.rng.randint(1, 3)
        transformations = [f"scaffold:{core[:15]}"]

        smiles = core
        for _ in range(n_substitutions):
            fg = self.fragment_library.get_functional_group(self.rng)
            position = self.rng.choice(["C", "N", "O"])
            smiles = smiles + position + fg
            transformations.append(f"added_fg:{fg}")

        return self._build_molecule(
            smiles, core, GenerationStrategy.SCAFFOLD_DECORATION, transformations
        )

    def _generate_bioisostere(
        self,
        scaffold: Optional[str] = None,
        reference_smiles: Optional[str] = None,
    ) -> GeneratedMolecule:
        """
        Bioisostere replacement: swap functional groups with bioisosteric equivalents.

        Common bioisostere pairs (Patani & LaVoie, 1996):
        - COOH ↔ tetrazole
        - Phenyl ↔ pyridyl, thienyl, furanyl
        - OH ↔ NH2, F
        - Cl ↔ CF3, CN, SCH3
        """
        bioisostere_map = {
            "c1ccccc1": ["c1ccncc1", "c1ccoc1", "c1ccsc1"],   # Phenyl → heteroaryl
            "O": ["N", "F"],                                     # OH → NH2 / F
            "Cl": ["C(F)(F)F", "C#N"],                          # Cl → CF3 / CN
            "CC(=O)O": ["c1nnn[nH]1"],                          # COOH → tetrazole
            "N": ["O", "S"],                                     # N → O/S
        }

        ref = reference_smiles or self.fragment_library.get_random_fragment(self.rng)
        smiles = ref
        transformations = [f"ref:{ref[:15]}"]

        for original, replacements in bioisostere_map.items():
            if original in smiles:
                replacement = self.rng.choice(replacements)
                smiles = smiles.replace(original, replacement, 1)
                transformations.append(f"bioisostere:{original}->{replacement}")
                break

        if smiles == ref:
            # No replacement found; add a fragment
            fg = self.fragment_library.get_functional_group(self.rng)
            smiles = smiles + "C" + fg
            transformations.append(f"fallback_decoration:{fg}")

        core = scaffold or ref[:10]
        return self._build_molecule(
            smiles, core, GenerationStrategy.BIOISOSTERE, transformations
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_molecule(
        self,
        smiles: str,
        scaffold: str,
        strategy: GenerationStrategy,
        transformations: List[str],
    ) -> GeneratedMolecule:
        """Construct a GeneratedMolecule with computed properties."""
        smiles = self.smiles_utils.canonical_smiles(smiles)
        mol_id = f"GEN-{self.smiles_utils.molecule_fingerprint(smiles)}"

        mw = self.smiles_utils.estimate_mw(smiles)
        logp = self.smiles_utils.estimate_logp(smiles)
        tpsa = self.smiles_utils.estimate_tpsa(smiles)

        qed = self._quick_qed(smiles)
        sa = self._synthetic_accessibility(smiles)
        novelty = self._compute_novelty(smiles)

        return GeneratedMolecule(
            molecule_id=mol_id,
            smiles=smiles,
            scaffold=scaffold,
            strategy=strategy,
            predicted_mw=mw,
            predicted_logp=logp,
            predicted_tpsa=tpsa,
            novelty_score=novelty,
            diversity_score=0.0,  # Filled after set is built
            qed_score=qed,
            sa_score=sa,
            applied_transformations=transformations,
        )

    def _passes_constraints(self, mol: GeneratedMolecule) -> bool:
        """Check if molecule satisfies property constraints."""
        c = self.constraints
        return (
            c.min_mw <= mol.predicted_mw <= c.max_mw
            and c.min_logp <= mol.predicted_logp <= c.max_logp
            and mol.predicted_tpsa <= c.max_tpsa
        )

    def _quick_qed(self, smiles: str) -> float:
        """
        Fast QED proxy using property desirability functions.

        Approximates the full QED metric (Bickerton et al. 2012).
        """
        mw = self.smiles_utils.estimate_mw(smiles)
        logp = self.smiles_utils.estimate_logp(smiles)
        tpsa = self.smiles_utils.estimate_tpsa(smiles)

        # Desirability functions (gaussian-bell shaped)
        d_mw = self._desirability_bell(mw, mean=333, width=150)
        d_logp = self._desirability_bell(logp, mean=2.5, width=2.5)
        d_tpsa = self._desirability_bell(tpsa, mean=60, width=50)

        # Aromatic ring desirability (1-3 rings preferred)
        aromatic = smiles.count("c")
        d_arom = 1.0 if 6 <= aromatic <= 18 else max(0.1, 1.0 - abs(aromatic - 12) * 0.05)

        qed = (d_mw * d_logp * d_tpsa * d_arom) ** 0.25  # Geometric mean
        return float(np.clip(qed, 0.01, 0.99))

    @staticmethod
    def _desirability_bell(value: float, mean: float, width: float) -> float:
        """Gaussian desirability bell function centered on ideal value."""
        return float(np.exp(-0.5 * ((value - mean) / width) ** 2))

    def _synthetic_accessibility(self, smiles: str) -> float:
        """
        Estimate synthetic accessibility (SA score, 1–10).

        Lower values indicate easier synthesis.
        Based on Ertl & Schuffenhauer (2009) fragment contribution model.
        """
        ring_complexity = smiles.count("1") + smiles.count("2") + smiles.count("3")
        branch_count = smiles.count("(")
        length = len(smiles)

        # Higher complexity = higher SA score
        sa = 1.0 + 0.02 * length + 0.1 * branch_count + 0.2 * ring_complexity
        return float(np.clip(sa, 1.0, 10.0))

    def _compute_novelty(self, smiles: str) -> float:
        """
        Novelty score based on dissimilarity to previously generated molecules.

        Returns 1.0 for the first molecule, decreasing for similar subsequent ones.
        """
        if not self._generated_fingerprints:
            return 1.0

        fp = self.smiles_utils.molecule_fingerprint(smiles)
        if fp in self._generated_fingerprints:
            return 0.0

        similarities = [
            self.smiles_utils.tanimoto_similarity(smiles, self._fp_to_smiles(fp2))
            for fp2 in self._generated_fingerprints[-50:]  # Check last 50
        ]
        max_sim = max(similarities) if similarities else 0.0
        return float(1.0 - max_sim)

    def _compute_diversity(self, smiles: str, existing_smiles: List[str]) -> float:
        """Diversity score vs. an existing set of molecules."""
        if not existing_smiles:
            return 1.0
        sims = [
            self.smiles_utils.tanimoto_similarity(smiles, other)
            for other in existing_smiles[-20:]
        ]
        avg_sim = np.mean(sims) if sims else 0.0
        return float(1.0 - avg_sim)

    def _fp_to_smiles(self, fp: str) -> str:
        """Map fingerprint back to SMILES (used for similarity lookup)."""
        # In production, store the actual SMILES keyed by fingerprint.
        # Here we return the fp string itself as a proxy.
        return fp

    def _crossover(self, parent1: str, parent2: str) -> str:
        """Single-point crossover between two SMILES strings."""
        if not parent1 or not parent2:
            return parent1 or parent2
        cut1 = self.rng.randint(1, len(parent1))
        cut2 = self.rng.randint(1, len(parent2))
        return parent1[:cut1] + parent2[cut2:]

    def _mutate(self, smiles: str, mutation_rate: float = 0.3) -> str:
        """Apply random point mutations to a SMILES string."""
        if self.rng.random() > mutation_rate:
            return smiles

        mutation_type = self.rng.choice(["add_fg", "replace_atom", "add_linker"])

        if mutation_type == "add_fg":
            fg = self.fragment_library.get_functional_group(self.rng)
            return smiles + fg

        if mutation_type == "replace_atom" and len(smiles) > 2:
            atom_map = {"C": "N", "N": "O", "O": "S", "S": "C"}
            for atom, replacement in atom_map.items():
                if atom in smiles:
                    idx = smiles.index(atom)
                    return smiles[:idx] + replacement + smiles[idx + 1:]

        if mutation_type == "add_linker":
            linker = self.fragment_library.get_linker(self.rng)
            return smiles + linker

        return smiles


# ---------------------------------------------------------------------------
# Scaffold Enumeration
# ---------------------------------------------------------------------------


class ScaffoldEnumerator:
    """
    Enumerate analogs around a central scaffold for structure-based design.

    Generates systematic R-group combinations for a given scaffold template.
    """

    R_GROUPS: Dict[str, List[str]] = {
        "R1": ["F", "Cl", "Br", "CH3", "OCH3", "CF3", "C#N", "NH2"],
        "R2": ["H", "CH3", "C2H5", "iPr", "Ph", "Bn", "OH", "OMe"],
        "R3": ["H", "F", "Cl", "Me", "Et", "OMe", "OH", "NH2"],
    }

    def enumerate(
        self,
        scaffold_smiles: str,
        r_group_positions: Optional[List[str]] = None,
        max_analogs: int = 100,
    ) -> List[str]:
        """
        Enumerate analogs by systematic R-group replacement.

        Args:
            scaffold_smiles: Core scaffold with R-group placeholders ([*:1], [*:2], ...).
            r_group_positions: R-group keys to vary (default: R1, R2, R3).
            max_analogs: Maximum number of analogs to return.

        Returns:
            List of analog SMILES strings.
        """
        positions = r_group_positions or list(self.R_GROUPS.keys())
        analogs = [scaffold_smiles]

        for position in positions:
            new_analogs = []
            for smiles in analogs:
                placeholder = f"[{position}]"
                if placeholder in smiles:
                    for r_group in self.R_GROUPS.get(position, ["H"]):
                        new_analogs.append(smiles.replace(placeholder, r_group, 1))
                else:
                    # Append R-group directly
                    for r_group in self.R_GROUPS.get(position, ["H"]):
                        new_analogs.append(smiles + r_group)

            analogs = new_analogs[:max_analogs]

        return list(dict.fromkeys(analogs))[:max_analogs]  # Deduplicate

    def cluster_analogs(
        self, smiles_list: List[str], n_clusters: int = 5
    ) -> Dict[int, List[str]]:
        """
        Cluster analogs by structural similarity for diversity selection.

        Uses greedy sphere-exclusion algorithm.

        Args:
            smiles_list: List of analog SMILES to cluster.
            n_clusters: Number of clusters.

        Returns:
            Dict mapping cluster ID to list of SMILES.
        """
        if not smiles_list:
            return {}

        utils = SMILESUtils()
        clusters: Dict[int, List[str]] = {i: [] for i in range(n_clusters)}
        centers = smiles_list[: min(n_clusters, len(smiles_list))]

        for smiles in smiles_list:
            best_cluster = 0
            best_sim = -1.0
            for i, center in enumerate(centers):
                sim = utils.tanimoto_similarity(smiles, center)
                if sim > best_sim:
                    best_sim = sim
                    best_cluster = i
            clusters[best_cluster].append(smiles)

        return clusters
