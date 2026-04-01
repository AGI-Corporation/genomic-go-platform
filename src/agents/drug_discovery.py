"""CrewAI Multi-Agent Drug Discovery Workflow for Genomic.go Platform

This module implements a specialized multi-agent system for autonomous
drug discovery using CrewAI. Agents collaborate sequentially to:
1. Identify therapeutic targets from GWAS/literature evidence
2. Mine the scientific literature for supporting evidence
3. Generate novel drug candidate molecules
4. Predict ADMET properties for safety/efficacy screening
5. Synthesize findings into a structured research report

Usage:
    from agents.drug_discovery import DrugDiscoveryPipeline

    pipeline = DrugDiscoveryPipeline(llm=your_llm)
    result = pipeline.run(disease="Alzheimer's disease")
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Guard against missing optional dependencies at import time
try:
    from crewai import Agent, Crew, Task
    from crewai.process import Process

    _CREWAI_AVAILABLE = True
except ImportError:  # pragma: no cover
    _CREWAI_AVAILABLE = False
    logger.warning(
        "crewai is not installed. DrugDiscoveryPipeline will be unavailable."
    )


@dataclass
class DrugDiscoveryConfig:
    """Configuration for the drug discovery multi-agent pipeline."""

    disease: str
    max_targets: int = 3
    max_candidates: int = 5
    verbose: bool = False
    # Optional human-readable context injected into agent backstories
    additional_context: str = ""


@dataclass
class DrugDiscoveryResult:
    """Structured output from the drug discovery pipeline."""

    disease: str
    targets: List[str] = field(default_factory=list)
    literature_summary: str = ""
    candidate_molecules: List[str] = field(default_factory=list)
    admet_summary: str = ""
    final_report: str = ""
    raw_crew_output: Optional[Any] = None


def _require_crewai():
    """Raise ImportError if crewai is not available."""
    if not _CREWAI_AVAILABLE:
        raise ImportError(
            "crewai is required for DrugDiscoveryPipeline. "
            "Install it with: pip install crewai"
        )


class TargetDiscoveryAgent:
    """Factory for the target discovery specialist agent."""

    @staticmethod
    def build(llm: Any, verbose: bool = False) -> "Agent":
        _require_crewai()
        return Agent(
            role="Target Discovery Specialist",
            goal=(
                "Identify the most promising therapeutic targets for the given disease "
                "by synthesizing GWAS findings, pathway analysis, and genetic evidence."
            ),
            backstory=(
                "You are an expert computational biologist with deep expertise in "
                "genome-wide association studies (GWAS), Mendelian randomization, "
                "and multi-omic data integration. You have published extensively on "
                "target identification and validation strategies for complex diseases."
            ),
            llm=llm,
            verbose=verbose,
            allow_delegation=False,
        )


class LiteratureMiningAgent:
    """Factory for the literature mining specialist agent."""

    @staticmethod
    def build(llm: Any, verbose: bool = False) -> "Agent":
        _require_crewai()
        return Agent(
            role="Scientific Literature Analyst",
            goal=(
                "Mine PubMed, bioRxiv, and clinical trial databases to identify "
                "supporting evidence for proposed therapeutic targets and synthesize "
                "key findings into actionable research intelligence."
            ),
            backstory=(
                "You are a biomedical informatician specializing in natural language "
                "processing for scientific literature. You rapidly extract structured "
                "information from unstructured research papers, identifying relevant "
                "mechanisms, prior clinical findings, and competitive landscape."
            ),
            llm=llm,
            verbose=verbose,
            allow_delegation=False,
        )


class MoleculeGenerationAgent:
    """Factory for the molecule generation specialist agent."""

    @staticmethod
    def build(llm: Any, verbose: bool = False) -> "Agent":
        _require_crewai()
        return Agent(
            role="Medicinal Chemist and Molecule Designer",
            goal=(
                "Design novel, drug-like molecules targeting the identified proteins, "
                "optimising for potency, selectivity, and synthetic accessibility."
            ),
            backstory=(
                "You are a computational medicinal chemist with expertise in de novo "
                "molecule generation, fragment-based drug design, and structure-based "
                "optimization. You apply Lipinski's Rule of Five and modern ADMET "
                "guidelines to ensure drug-likeness of candidates."
            ),
            llm=llm,
            verbose=verbose,
            allow_delegation=False,
        )


class ADMETPredictionAgent:
    """Factory for the ADMET prediction specialist agent."""

    @staticmethod
    def build(llm: Any, verbose: bool = False) -> "Agent":
        _require_crewai()
        return Agent(
            role="ADMET and Safety Pharmacologist",
            goal=(
                "Evaluate each drug candidate's Absorption, Distribution, Metabolism, "
                "Excretion, and Toxicity (ADMET) profile and rank compounds by their "
                "predicted safety and efficacy."
            ),
            backstory=(
                "You are a pharmacokineticist and toxicologist who uses computational "
                "models to predict in-vivo behavior of drug candidates. You integrate "
                "physicochemical properties, metabolic liabilities, hERG toxicity, and "
                "organ-specific distribution to flag unsuitable compounds early."
            ),
            llm=llm,
            verbose=verbose,
            allow_delegation=False,
        )


class ResearchReportAgent:
    """Factory for the orchestrating research report agent."""

    @staticmethod
    def build(llm: Any, verbose: bool = False) -> "Agent":
        _require_crewai()
        return Agent(
            role="Drug Discovery Research Director",
            goal=(
                "Synthesize all findings from target discovery, literature analysis, "
                "molecule design, and ADMET evaluation into a concise, investment-ready "
                "research report with clear next steps and risk assessment."
            ),
            backstory=(
                "You are a senior drug discovery director with 20+ years of experience "
                "advancing compounds from hit identification through IND filing. You "
                "distil complex multi-disciplinary findings into clear strategic "
                "recommendations for research leadership and investors."
            ),
            llm=llm,
            verbose=verbose,
            allow_delegation=False,
        )


def _build_tasks(
    config: DrugDiscoveryConfig,
    target_agent: "Agent",
    literature_agent: "Agent",
    molecule_agent: "Agent",
    admet_agent: "Agent",
    report_agent: "Agent",
) -> List["Task"]:
    """Construct the ordered task sequence for the drug discovery workflow."""
    disease = config.disease
    n_targets = config.max_targets
    n_candidates = config.max_candidates

    target_task = Task(
        description=(
            f"Identify the top {n_targets} therapeutic targets for {disease}. "
            "For each target: provide the gene name, protein product, mechanism of action, "
            "strength of genetic evidence (GWAS hits, eQTL support), and druggability assessment. "
            "Rank targets from most to least compelling."
        ),
        expected_output=(
            f"A ranked list of {n_targets} therapeutic targets with gene name, protein, "
            "mechanism, genetic evidence score (1-10), and druggability score (1-10)."
        ),
        agent=target_agent,
    )

    literature_task = Task(
        description=(
            f"Review the scientific literature for {disease} and the top therapeutic targets "
            "identified in the previous step. Summarise: key pathophysiology papers, "
            "failed clinical trials and their reasons, current standard of care, "
            "and any existing compounds modulating these targets."
        ),
        expected_output=(
            "A structured literature summary (max 500 words) covering: pathophysiology, "
            "prior drug attempts, current treatments, and competitive landscape."
        ),
        agent=literature_agent,
        context=[target_task],
    )

    molecule_task = Task(
        description=(
            f"Design {n_candidates} novel small-molecule drug candidates for the top-ranked "
            f"therapeutic target for {disease}. For each candidate provide: a SMILES string "
            "(or structural description), molecular weight, cLogP, H-bond donors/acceptors, "
            "predicted binding affinity, and key design rationale."
        ),
        expected_output=(
            f"A table of {n_candidates} drug candidates with: name, SMILES, MW, cLogP, "
            "HBD, HBA, predicted IC50, and design rationale."
        ),
        agent=molecule_agent,
        context=[target_task, literature_task],
    )

    admet_task = Task(
        description=(
            f"Predict the ADMET properties of the {n_candidates} drug candidates designed "
            "in the previous step. Evaluate: oral bioavailability, plasma protein binding, "
            "CYP metabolism liabilities, blood-brain barrier penetration (if relevant), "
            "hERG cardiotoxicity risk, and AMES mutagenicity. "
            "Rank candidates and recommend the top 2 for further development."
        ),
        expected_output=(
            "Per-compound ADMET scorecard and a final ranking with top 2 compounds "
            "recommended for progression, with a brief justification for each."
        ),
        agent=admet_agent,
        context=[molecule_task],
    )

    report_task = Task(
        description=(
            f"Write an executive research report on the drug discovery campaign for {disease}. "
            "Integrate target identification, literature evidence, lead molecules, and ADMET data. "
            "Structure the report as: Executive Summary, Target Rationale, Lead Compounds, "
            "Risk Assessment, Recommended Next Steps."
        ),
        expected_output=(
            "A concise research report (800-1200 words) structured with the five sections above, "
            "suitable for sharing with scientific leadership or biotech investors."
        ),
        agent=report_agent,
        context=[target_task, literature_task, molecule_task, admet_task],
    )

    return [target_task, literature_task, molecule_task, admet_task, report_task]


class DrugDiscoveryPipeline:
    """End-to-end multi-agent drug discovery pipeline powered by CrewAI.

    Orchestrates five specialized AI agents through a sequential workflow:
    target discovery → literature mining → molecule generation →
    ADMET prediction → research report synthesis.

    Args:
        llm: A LangChain-compatible LLM instance (e.g. from Kalibr or OpenAI)
        verbose: Whether to enable verbose agent logging

    Example:
        >>> from langchain_openai import ChatOpenAI
        >>> llm = ChatOpenAI(model="gpt-4o", temperature=0)
        >>> pipeline = DrugDiscoveryPipeline(llm=llm, verbose=True)
        >>> result = pipeline.run("Alzheimer's disease")
        >>> print(result.final_report)
    """

    def __init__(self, llm: Any, verbose: bool = False):
        _require_crewai()
        self.llm = llm
        self.verbose = verbose

    def _build_crew(self, config: DrugDiscoveryConfig) -> "Crew":
        """Instantiate all agents and tasks and return a configured Crew."""
        target_agent = TargetDiscoveryAgent.build(self.llm, self.verbose)
        literature_agent = LiteratureMiningAgent.build(self.llm, self.verbose)
        molecule_agent = MoleculeGenerationAgent.build(self.llm, self.verbose)
        admet_agent = ADMETPredictionAgent.build(self.llm, self.verbose)
        report_agent = ResearchReportAgent.build(self.llm, self.verbose)

        tasks = _build_tasks(
            config,
            target_agent,
            literature_agent,
            molecule_agent,
            admet_agent,
            report_agent,
        )

        return Crew(
            agents=[
                target_agent,
                literature_agent,
                molecule_agent,
                admet_agent,
                report_agent,
            ],
            tasks=tasks,
            process=Process.sequential,
            verbose=self.verbose,
        )

    def run(
        self, disease: str, max_targets: int = 3, max_candidates: int = 5
    ) -> DrugDiscoveryResult:
        """Execute the full drug discovery pipeline for a given disease.

        Args:
            disease: Disease name to investigate (e.g. "Parkinson's disease")
            max_targets: Maximum number of therapeutic targets to identify
            max_candidates: Maximum number of drug candidates to generate

        Returns:
            DrugDiscoveryResult with structured outputs from each agent stage
        """
        config = DrugDiscoveryConfig(
            disease=disease,
            max_targets=max_targets,
            max_candidates=max_candidates,
            verbose=self.verbose,
        )

        logger.info(f"Starting drug discovery pipeline for: {disease}")

        crew = self._build_crew(config)
        raw_output = crew.kickoff()

        result = DrugDiscoveryResult(
            disease=disease,
            raw_crew_output=raw_output,
            final_report=str(raw_output) if raw_output else "",
        )

        logger.info(f"Drug discovery pipeline completed for: {disease}")
        return result

    def get_agent_descriptions(self) -> List[Dict[str, str]]:
        """Return metadata about each agent in the pipeline.

        Useful for documentation, UI rendering, and audit logging.
        """
        return [
            {
                "role": "Target Discovery Specialist",
                "focus": "GWAS analysis and therapeutic target identification",
                "tools": [
                    "GWAS databases",
                    "pathway analysis",
                    "genetic evidence scoring",
                ],
            },
            {
                "role": "Scientific Literature Analyst",
                "focus": "PubMed and bioRxiv mining for disease evidence",
                "tools": ["PubMed API", "bioRxiv", "clinical trial registries"],
            },
            {
                "role": "Medicinal Chemist and Molecule Designer",
                "focus": "De novo drug candidate generation and optimization",
                "tools": ["RDKit", "structure-based design", "fragment libraries"],
            },
            {
                "role": "ADMET and Safety Pharmacologist",
                "focus": "Pharmacokinetic and toxicity profiling",
                "tools": ["SwissADME", "pkCSM", "hERG prediction models"],
            },
            {
                "role": "Drug Discovery Research Director",
                "focus": "Strategic synthesis and executive reporting",
                "tools": ["report generation", "risk assessment", "portfolio analysis"],
            },
        ]
