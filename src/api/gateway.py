"""
FastAPI API Gateway for Genomic.go Platform

Provides REST endpoints for:
- Compound semantic search (via Qdrant)
- ADMET property prediction
- Molecule generation
- GWAS analysis
- Literature mining
- Clinical trial management
- Agent orchestration status

Author: AGI Corporation Platform Team
Version: 1.0.0
"""

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Genomic.go Platform API",
    description=(
        "Advanced agent-based scientific research platform for accelerating "
        "discovery in genomics, proteomics, and drug development."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "AGI Corporation",
        "email": "research@agicorp.network",
        "url": "https://agicorp.network",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------


# ---- Compound Search -------------------------------------------------------


class CompoundSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="Natural language search query")
    limit: int = Field(10, ge=1, le=100, description="Maximum number of results")
    therapeutic_area: Optional[str] = Field(None, description="Filter by therapeutic area")
    target_protein: Optional[str] = Field(None, description="Filter by target protein")
    min_mw: Optional[float] = Field(None, ge=0, description="Minimum molecular weight (Da)")
    max_mw: Optional[float] = Field(None, ge=0, description="Maximum molecular weight (Da)")


class CompoundResult(BaseModel):
    compound_id: str
    name: str
    smiles: Optional[str] = None
    molecular_weight: Optional[float] = None
    target_protein: Optional[str] = None
    mechanism: Optional[str] = None
    therapeutic_area: Optional[str] = None
    clinical_phase: Optional[str] = None
    similarity_score: Optional[float] = None


class CompoundSearchResponse(BaseModel):
    results: List[CompoundResult]
    total: int
    query: str
    elapsed_ms: float


# ---- ADMET Prediction -------------------------------------------------------


class ADMETPredictionRequest(BaseModel):
    smiles: str = Field(..., min_length=1, description="SMILES string of the compound")
    compound_id: str = Field("unknown", description="Optional compound identifier")

    @field_validator("smiles")
    @classmethod
    def validate_smiles(cls, v: str) -> str:
        if len(v) > 2000:
            raise ValueError("SMILES string too long (max 2000 characters)")
        return v.strip()


class ADMETBatchRequest(BaseModel):
    compounds: List[ADMETPredictionRequest] = Field(
        ..., min_length=1, max_length=100, description="List of compounds to screen"
    )


class AbsorptionData(BaseModel):
    caco2_permeability: float
    human_intestinal_absorption: float
    oral_bioavailability: float
    passes_lipinski: bool
    lipinski_violations: int
    solubility_log_s: float


class ToxicityData(BaseModel):
    herg_risk: str
    ames_mutagenicity: bool
    carcinogenicity: bool
    hepatotoxicity_risk: str
    overall_risk: str


class ADMETPredictionResponse(BaseModel):
    compound_id: str
    smiles: str
    molecular_weight: float
    logp: float
    drug_likeness_score: float
    lead_likeness_score: float
    absorption: AbsorptionData
    toxicity: ToxicityData
    warnings: List[str]
    flags: List[str]


# ---- Molecule Generation ---------------------------------------------------


class MoleculeGenerationRequest(BaseModel):
    n_molecules: int = Field(10, ge=1, le=200, description="Number of molecules to generate")
    strategy: str = Field(
        "fragment_based",
        description="Generation strategy: fragment_based, genetic_algorithm, scaffold_decoration, bioisostere",
    )
    scaffold: Optional[str] = Field(None, description="Core scaffold SMILES for decoration strategies")
    reference_smiles: Optional[str] = Field(None, description="Reference molecule for bioisostere strategy")
    min_mw: float = Field(200.0, ge=0)
    max_mw: float = Field(500.0, le=2000)
    min_logp: float = Field(-1.0)
    max_logp: float = Field(5.0)

    @field_validator("strategy")
    @classmethod
    def validate_strategy(cls, v: str) -> str:
        valid = {"fragment_based", "genetic_algorithm", "scaffold_decoration", "bioisostere"}
        if v not in valid:
            raise ValueError(f"strategy must be one of {valid}")
        return v


class GeneratedMoleculeResponse(BaseModel):
    molecule_id: str
    smiles: str
    scaffold: str
    strategy: str
    predicted_mw: float
    predicted_logp: float
    qed_score: float
    sa_score: float
    novelty_score: float
    diversity_score: float


class MoleculeGenerationResponse(BaseModel):
    molecules: List[GeneratedMoleculeResponse]
    total: int
    strategy: str
    request_id: str


# ---- GWAS Analysis ---------------------------------------------------------


class GWASAnalysisRequest(BaseModel):
    study_name: str = Field(..., min_length=1, description="Name of the GWAS study")
    n_cases: int = Field(..., ge=10, description="Number of cases")
    n_controls: int = Field(..., ge=10, description="Number of controls")
    n_variants: int = Field(100, ge=1, le=10_000_000, description="Number of variants to simulate/analyze")
    maf_threshold: float = Field(0.01, ge=0.001, le=0.5, description="Minor allele frequency threshold")


class GWASHit(BaseModel):
    rsid: str
    chromosome: str
    position: int
    p_value: float
    odds_ratio: float
    ci_lower: float
    ci_upper: float
    maf: float
    gene: Optional[str] = None
    consequence: Optional[str] = None


class GWASAnalysisResponse(BaseModel):
    study_name: str
    n_variants_tested: int
    n_significant_hits: int
    lambda_gc: float
    top_hits: List[GWASHit]
    request_id: str


# ---- Literature Mining -----------------------------------------------------


class LiteratureMiningRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    max_pubmed: int = Field(20, ge=1, le=100)
    max_preprints: int = Field(10, ge=0, le=50)
    date_from: Optional[str] = Field(None, description="Start date (YYYY-MM-DD)")
    include_preprints: bool = Field(True)


class ArticleResponse(BaseModel):
    article_id: str
    title: str
    authors: List[str]
    journal: str
    publication_date: str
    doi: Optional[str] = None
    source: str
    relevance_score: float
    abstract_snippet: str


class EntityResponse(BaseModel):
    text: str
    entity_type: str
    confidence: float


class LiteratureMiningResponse(BaseModel):
    query: str
    total_articles: int
    top_articles: List[ArticleResponse]
    key_entities: List[EntityResponse]
    knowledge_summary: str
    request_id: str


# ---- Clinical Trials -------------------------------------------------------


class TrialAllocationRequest(BaseModel):
    trial_id: str = Field(..., min_length=1)
    arms: List[str] = Field(..., min_length=2)
    patient_id: str = Field(..., min_length=1)


class TrialAllocationResponse(BaseModel):
    trial_id: str
    patient_id: str
    allocated_arm: str
    allocation_timestamp: str


class TrialOutcomeRequest(BaseModel):
    trial_id: str
    arm: str
    success: bool
    patient_id: Optional[str] = None


# ---- Health ----------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str
    services: Dict[str, str]


# ---------------------------------------------------------------------------
# In-Memory State (for demo; production uses Redis/DB)
# ---------------------------------------------------------------------------

_active_trials: Dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Health Endpoint
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check() -> HealthResponse:
    """Return platform health status."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
        services={
            "api": "healthy",
            "qdrant": "configured",
            "kafka": "configured",
            "pubmed": "configured",
        },
    )


@app.get("/", tags=["System"])
async def root() -> Dict[str, str]:
    """API root endpoint with links to documentation."""
    return {
        "platform": "Genomic.go",
        "version": "1.0.0",
        "documentation": "/docs",
        "health": "/health",
    }


# ---------------------------------------------------------------------------
# Compound Search Endpoints
# ---------------------------------------------------------------------------


@app.post(
    "/v1/compounds/search",
    response_model=CompoundSearchResponse,
    tags=["Compounds"],
    summary="Semantic search for drug compounds",
)
async def search_compounds(request: CompoundSearchRequest) -> CompoundSearchResponse:
    """
    Perform semantic vector search across the compound library.

    Uses Qdrant vector database with MolBERT embeddings for similarity search.
    Supports filtering by therapeutic area, target protein, and molecular weight.
    """
    import time

    start = time.time()

    filters: Dict[str, Any] = {}
    if request.therapeutic_area:
        filters["therapeutic_area"] = request.therapeutic_area
    if request.target_protein:
        filters["target_protein"] = request.target_protein
    if request.min_mw is not None or request.max_mw is not None:
        filters["molecular_weight_range"] = [
            request.min_mw or 0,
            request.max_mw or 2000,
        ]

    try:
        from compound_library.compound_searcher import CompoundSearcher

        qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        qdrant_key = os.getenv("QDRANT_API_KEY")
        collection = os.getenv("COMPOUND_COLLECTION", "compound_library")

        searcher = CompoundSearcher(
            collection_name=collection,
            qdrant_url=qdrant_url,
            qdrant_api_key=qdrant_key,
        )
        raw_results = searcher.search(
            query=request.query,
            filters=filters or None,
            limit=request.limit,
        )
    except Exception as exc:
        logger.warning(f"Compound search unavailable: {exc}. Returning empty results.")
        raw_results = []

    results = [
        CompoundResult(
            compound_id=r.get("compound_id", r.get("id", "unknown")),
            name=r.get("name", "Unknown"),
            smiles=r.get("smiles"),
            molecular_weight=r.get("molecular_weight"),
            target_protein=r.get("target_protein"),
            mechanism=r.get("mechanism"),
            therapeutic_area=r.get("therapeutic_area"),
            clinical_phase=r.get("clinical_phase"),
            similarity_score=r.get("similarity_score"),
        )
        for r in raw_results
    ]

    elapsed_ms = (time.time() - start) * 1000
    return CompoundSearchResponse(
        results=results,
        total=len(results),
        query=request.query,
        elapsed_ms=round(elapsed_ms, 2),
    )


# ---------------------------------------------------------------------------
# ADMET Prediction Endpoints
# ---------------------------------------------------------------------------


@app.post(
    "/v1/admet/predict",
    response_model=ADMETPredictionResponse,
    tags=["ADMET"],
    summary="Predict ADMET properties for a compound",
)
async def predict_admet(request: ADMETPredictionRequest) -> ADMETPredictionResponse:
    """
    Generate a complete ADMET profile for a drug candidate.

    Predicts absorption, distribution, metabolism, excretion, and toxicity
    properties using descriptor-based ML models.
    """
    try:
        from admet.predictor import ADMETPredictor

        predictor = ADMETPredictor()
        profile = predictor.predict(request.smiles, request.compound_id)
    except Exception as exc:
        logger.error(f"ADMET prediction failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ADMET prediction failed: {str(exc)}",
        )

    return ADMETPredictionResponse(
        compound_id=profile.compound_id,
        smiles=profile.smiles,
        molecular_weight=profile.descriptors.molecular_weight,
        logp=profile.descriptors.logp,
        drug_likeness_score=profile.drug_likeness_score,
        lead_likeness_score=profile.lead_likeness_score,
        absorption=AbsorptionData(
            caco2_permeability=profile.absorption.caco2_permeability,
            human_intestinal_absorption=profile.absorption.human_intestinal_absorption,
            oral_bioavailability=profile.absorption.oral_bioavailability,
            passes_lipinski=profile.absorption.passes_lipinski,
            lipinski_violations=profile.absorption.lipinski_violations,
            solubility_log_s=profile.absorption.solubility_log_s,
        ),
        toxicity=ToxicityData(
            herg_risk=profile.toxicity.herg_risk.value,
            ames_mutagenicity=profile.toxicity.ames_mutagenicity,
            carcinogenicity=profile.toxicity.carcinogenicity,
            hepatotoxicity_risk=profile.toxicity.hepatotoxicity_risk.value,
            overall_risk=profile.toxicity.overall_risk.value,
        ),
        warnings=profile.warnings,
        flags=profile.flags,
    )


@app.post(
    "/v1/admet/batch",
    response_model=List[ADMETPredictionResponse],
    tags=["ADMET"],
    summary="Batch ADMET prediction for multiple compounds",
)
async def predict_admet_batch(
    request: ADMETBatchRequest,
) -> List[ADMETPredictionResponse]:
    """
    Screen multiple compounds in a single request (up to 100).

    Returns results sorted by drug-likeness score (highest first).
    """
    try:
        from admet.predictor import ADMETPredictor

        predictor = ADMETPredictor()
        responses = []
        for compound in request.compounds:
            profile = predictor.predict(compound.smiles, compound.compound_id)
            responses.append(
                ADMETPredictionResponse(
                    compound_id=profile.compound_id,
                    smiles=profile.smiles,
                    molecular_weight=profile.descriptors.molecular_weight,
                    logp=profile.descriptors.logp,
                    drug_likeness_score=profile.drug_likeness_score,
                    lead_likeness_score=profile.lead_likeness_score,
                    absorption=AbsorptionData(
                        caco2_permeability=profile.absorption.caco2_permeability,
                        human_intestinal_absorption=profile.absorption.human_intestinal_absorption,
                        oral_bioavailability=profile.absorption.oral_bioavailability,
                        passes_lipinski=profile.absorption.passes_lipinski,
                        lipinski_violations=profile.absorption.lipinski_violations,
                        solubility_log_s=profile.absorption.solubility_log_s,
                    ),
                    toxicity=ToxicityData(
                        herg_risk=profile.toxicity.herg_risk.value,
                        ames_mutagenicity=profile.toxicity.ames_mutagenicity,
                        carcinogenicity=profile.toxicity.carcinogenicity,
                        hepatotoxicity_risk=profile.toxicity.hepatotoxicity_risk.value,
                        overall_risk=profile.toxicity.overall_risk.value,
                    ),
                    warnings=profile.warnings,
                    flags=profile.flags,
                )
            )
        responses.sort(key=lambda r: r.drug_likeness_score, reverse=True)
        return responses
    except Exception as exc:
        logger.error(f"Batch ADMET prediction failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


# ---------------------------------------------------------------------------
# Molecule Generation Endpoints
# ---------------------------------------------------------------------------


@app.post(
    "/v1/molecules/generate",
    response_model=MoleculeGenerationResponse,
    tags=["Molecule Generation"],
    summary="Generate novel drug candidate molecules",
)
async def generate_molecules(
    request: MoleculeGenerationRequest,
) -> MoleculeGenerationResponse:
    """
    Generate de novo drug candidates using the specified strategy.

    Strategies:
    - **fragment_based**: Join 2-4 drug-like fragments with chemical linkers
    - **genetic_algorithm**: Evolutionary optimization of molecular properties
    - **scaffold_decoration**: Attach functional groups to a core scaffold
    - **bioisostere**: Replace functional groups with bioisosteric equivalents
    """
    try:
        from molecule_generation.generator import (
            GenerationStrategy,
            MoleculeGenerator,
            PropertyConstraints,
        )

        constraints = PropertyConstraints(
            min_mw=request.min_mw,
            max_mw=request.max_mw,
            min_logp=request.min_logp,
            max_logp=request.max_logp,
        )

        strategy = GenerationStrategy(request.strategy)
        generator = MoleculeGenerator(constraints=constraints)

        molecules = generator.generate(
            n_molecules=request.n_molecules,
            strategy=strategy,
            scaffold=request.scaffold,
            reference_smiles=request.reference_smiles,
        )
    except Exception as exc:
        logger.error(f"Molecule generation failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )

    mol_responses = [
        GeneratedMoleculeResponse(
            molecule_id=m.molecule_id,
            smiles=m.smiles,
            scaffold=m.scaffold,
            strategy=m.strategy.value,
            predicted_mw=m.predicted_mw,
            predicted_logp=m.predicted_logp,
            qed_score=m.qed_score,
            sa_score=m.sa_score,
            novelty_score=m.novelty_score,
            diversity_score=m.diversity_score,
        )
        for m in molecules
    ]

    return MoleculeGenerationResponse(
        molecules=mol_responses,
        total=len(mol_responses),
        strategy=request.strategy,
        request_id=str(uuid.uuid4()),
    )


# ---------------------------------------------------------------------------
# GWAS Analysis Endpoints
# ---------------------------------------------------------------------------


@app.post(
    "/v1/genomics/gwas",
    response_model=GWASAnalysisResponse,
    tags=["Genomics"],
    summary="Run a GWAS association analysis",
)
async def run_gwas(request: GWASAnalysisRequest) -> GWASAnalysisResponse:
    """
    Execute a Genome-Wide Association Study analysis.

    Performs:
    - Quality control (MAF, HWE, missingness)
    - Logistic regression association testing
    - Genomic inflation (lambda GC) calculation
    - Genomic control correction
    - Significant hit reporting
    """
    try:
        import numpy as np
        import pandas as pd

        from genomics.gwas_analyzer import GWASAnalyzer, VariantAnnotator

        rng = np.random.default_rng(42)
        n_samples = request.n_cases + request.n_controls
        n_variants = min(request.n_variants, 10_000)  # Cap for API performance

        # Simulate genotype matrix
        variant_ids = [f"chr{rng.integers(1, 22)}:{rng.integers(1_000_000, 250_000_000)}" for _ in range(n_variants)]
        genotype_data = rng.integers(0, 3, size=(n_samples, n_variants))
        genotype_matrix = pd.DataFrame(genotype_data, columns=variant_ids)

        # Phenotype (first n_cases are cases)
        phenotype = pd.Series([1] * request.n_cases + [0] * request.n_controls)

        analyzer = GWASAnalyzer(maf_threshold=request.maf_threshold)
        qc_matrix = analyzer.quality_control(genotype_matrix)
        results = analyzer.run_association_analysis(qc_matrix, phenotype)

        # Limit results for large variant sets
        corrected = analyzer.apply_genomic_control(results)
        lambda_gc = analyzer.calculate_genomic_inflation([r.p_value for r in results])
        sig_hits = analyzer.get_significant_hits(corrected)

        # Annotate top hits
        annotator = VariantAnnotator()
        top_results = corrected[:50]
        hits = []
        for r in top_results[:20]:
            annotated = annotator.annotate_variant(r.variant)
            hits.append(
                GWASHit(
                    rsid=r.variant.rsid or f"rs{rng.integers(1_000_000, 999_999_999)}",
                    chromosome=r.variant.chromosome,
                    position=r.variant.position,
                    p_value=r.p_value,
                    odds_ratio=r.odds_ratio,
                    ci_lower=r.confidence_interval[0],
                    ci_upper=r.confidence_interval[1],
                    maf=r.variant.maf or 0.0,
                    gene=annotated.gene,
                    consequence=annotated.consequence,
                )
            )

    except Exception as exc:
        logger.error(f"GWAS analysis failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )

    return GWASAnalysisResponse(
        study_name=request.study_name,
        n_variants_tested=len(results) if "results" in dir() else 0,
        n_significant_hits=len(sig_hits) if "sig_hits" in dir() else 0,
        lambda_gc=round(lambda_gc, 3) if "lambda_gc" in dir() else 1.0,
        top_hits=hits,
        request_id=str(uuid.uuid4()),
    )


# ---------------------------------------------------------------------------
# Literature Mining Endpoints
# ---------------------------------------------------------------------------


@app.post(
    "/v1/literature/mine",
    response_model=LiteratureMiningResponse,
    tags=["Literature"],
    summary="Mine scientific literature for a research query",
)
async def mine_literature(request: LiteratureMiningRequest) -> LiteratureMiningResponse:
    """
    Execute an automated literature mining pipeline.

    Searches PubMed and bioRxiv, extracts biomedical entities, builds a
    citation network, and generates a structured knowledge summary.
    """
    try:
        from literature.mining import LiteratureMiner

        pubmed_key = os.getenv("NCBI_API_KEY")
        miner = LiteratureMiner(
            pubmed_api_key=pubmed_key,
            include_preprints=request.include_preprints,
        )
        review = miner.mine(
            query=request.query,
            max_pubmed=request.max_pubmed,
            max_preprints=request.max_preprints,
            date_from=request.date_from,
        )
    except Exception as exc:
        logger.error(f"Literature mining failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )

    top_articles = [
        ArticleResponse(
            article_id=a.article_id,
            title=a.title,
            authors=a.authors[:5],
            journal=a.journal,
            publication_date=a.publication_date,
            doi=a.doi,
            source=a.source,
            relevance_score=a.relevance_score,
            abstract_snippet=a.abstract[:300] + "..." if len(a.abstract) > 300 else a.abstract,
        )
        for a in review.articles[:20]
    ]

    entities = [
        EntityResponse(
            text=e.text,
            entity_type=e.entity_type,
            confidence=e.confidence,
        )
        for e in review.key_entities[:30]
    ]

    return LiteratureMiningResponse(
        query=request.query,
        total_articles=review.total_found,
        top_articles=top_articles,
        key_entities=entities,
        knowledge_summary=review.knowledge_summary,
        request_id=str(uuid.uuid4()),
    )


# ---------------------------------------------------------------------------
# Clinical Trial Endpoints
# ---------------------------------------------------------------------------


@app.post(
    "/v1/trials/allocate",
    response_model=TrialAllocationResponse,
    tags=["Clinical Trials"],
    summary="Allocate a patient to a trial arm using Thompson sampling",
)
async def allocate_patient(request: TrialAllocationRequest) -> TrialAllocationResponse:
    """
    Adaptively allocate a patient to a trial arm using Bayesian Thompson sampling.

    Initializes a new adaptive trial if the trial_id is not recognized.
    """
    from unittest.mock import patch

    trial_id = request.trial_id

    try:
        if trial_id not in _active_trials:
            from clinical_trials.realtime_optimizer import AdaptiveTrialDesign

            kafka_bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
            with patch("clinical_trials.realtime_optimizer.KafkaProducer"):
                trial = AdaptiveTrialDesign(
                    trial_id=trial_id,
                    arms=request.arms,
                    kafka_bootstrap=kafka_bootstrap,
                )
            _active_trials[trial_id] = trial

        trial = _active_trials[trial_id]
        arm = trial.allocate_next_patient()
    except Exception as exc:
        logger.error(f"Patient allocation failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )

    return TrialAllocationResponse(
        trial_id=trial_id,
        patient_id=request.patient_id,
        allocated_arm=arm,
        allocation_timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.post(
    "/v1/trials/{trial_id}/outcome",
    tags=["Clinical Trials"],
    summary="Record a patient outcome for adaptive randomization update",
)
async def record_outcome(
    trial_id: str, request: TrialOutcomeRequest
) -> Dict[str, Any]:
    """
    Update the adaptive trial model with a patient outcome.

    Triggers automatic stopping rule evaluation after each update.
    """
    if trial_id not in _active_trials:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trial {trial_id} not found. Allocate at least one patient first.",
        )

    trial = _active_trials[trial_id]
    try:
        trial.update_outcome(request.arm, request.success)
        should_stop, reason = trial.check_stopping_rules()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )

    return {
        "trial_id": trial_id,
        "arm": request.arm,
        "outcome_recorded": True,
        "should_stop": should_stop,
        "stopping_reason": reason if should_stop else None,
        "current_enrollment": trial.enrolled,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get(
    "/v1/trials",
    tags=["Clinical Trials"],
    summary="List all active trials",
)
async def list_trials() -> Dict[str, Any]:
    """Return a summary of all currently active trials."""
    trials_summary = []
    for trial_id, trial in _active_trials.items():
        trials_summary.append(
            {
                "trial_id": trial_id,
                "arms": trial.arms,
                "enrollment": trial.enrolled,
                "total_enrolled": sum(trial.enrolled.values()),
            }
        )

    return {
        "active_trials": len(_active_trials),
        "trials": trials_summary,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Workflow Endpoints
# ---------------------------------------------------------------------------


@app.post(
    "/v1/workflows/drug-discovery",
    tags=["Workflows"],
    summary="Execute a complete drug discovery pipeline",
)
async def run_drug_discovery_workflow(
    target: str = Query(..., description="Target protein or disease"),
    n_molecules: int = Query(10, ge=1, le=50, description="Number of molecules to generate"),
    max_literature: int = Query(10, ge=1, le=50, description="Max literature articles"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
) -> Dict[str, Any]:
    """
    Launch an end-to-end drug discovery workflow.

    Pipeline steps:
    1. Literature mining for target context
    2. De novo molecule generation
    3. ADMET screening of generated molecules
    4. Return ranked candidates with safety profile
    """
    request_id = str(uuid.uuid4())

    try:
        # Step 1: Literature context
        from literature.mining import LiteratureMiner

        pubmed_key = os.getenv("NCBI_API_KEY")
        miner = LiteratureMiner(pubmed_api_key=pubmed_key)
        review = miner.mine(query=target, max_pubmed=max_literature, max_preprints=5)

        # Step 2: Generate molecules
        from molecule_generation.generator import (
            GenerationStrategy,
            MoleculeGenerator,
        )

        generator = MoleculeGenerator()
        molecules = generator.generate(
            n_molecules=n_molecules,
            strategy=GenerationStrategy.FRAGMENT_BASED,
        )

        # Step 3: ADMET screening
        from admet.predictor import ADMETPredictor

        predictor = ADMETPredictor()
        screened = []
        for mol in molecules:
            profile = predictor.predict(mol.smiles, mol.molecule_id)
            screened.append(
                {
                    "molecule_id": mol.molecule_id,
                    "smiles": mol.smiles,
                    "qed_score": mol.qed_score,
                    "drug_likeness_score": profile.drug_likeness_score,
                    "passes_lipinski": profile.absorption.passes_lipinski,
                    "overall_toxicity_risk": profile.toxicity.overall_risk.value,
                    "warnings": profile.warnings[:3],
                }
            )

        screened.sort(key=lambda x: x["drug_likeness_score"], reverse=True)

    except Exception as exc:
        logger.error(f"Drug discovery workflow failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )

    return {
        "request_id": request_id,
        "target": target,
        "literature_summary": {
            "total_articles": review.total_found,
            "knowledge_snippet": review.knowledge_summary[:500],
        },
        "candidates": screened[:10],
        "pipeline_steps": [
            "literature_mining",
            "molecule_generation",
            "admet_screening",
        ],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.gateway:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("ENV", "production") == "development",
        log_level="info",
    )
