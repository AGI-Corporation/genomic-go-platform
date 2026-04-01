"""Genomic.go Platform - FastAPI REST API

Provides HTTP endpoints for all core platform capabilities:
- Compound library semantic search
- Clinical trial management (adaptive design, patient matching)
- GWAS analysis
- Drug discovery agent workflows

Run locally:
    uvicorn src.api.main:app --reload --port 8000

Environment variables:
    QDRANT_URL          URL to Qdrant instance (default: http://localhost:6333)
    QDRANT_API_KEY      Optional Qdrant Cloud API key
    KAFKA_BOOTSTRAP     Kafka bootstrap servers (default: localhost:9092)
"""

import logging
import os
from typing import Any, Dict, List, Optional

import numpy as np
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Genomic.go Platform API",
    description=(
        "AI-powered genomic research platform providing compound search, "
        "clinical trial optimization, GWAS analysis, and multi-agent drug discovery."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# Pydantic request / response models
# ---------------------------------------------------------------------------


class CompoundSearchRequest(BaseModel):
    query: str = Field(..., min_length=3, description="Natural language compound query")
    filters: Optional[Dict[str, Any]] = Field(
        None,
        description=(
            "Optional filters: molecular_weight_range=[min,max], "
            "target_protein, mechanism, therapeutic_area"
        ),
    )
    limit: int = Field(10, ge=1, le=100, description="Maximum results to return")


class CompoundSearchResponse(BaseModel):
    query: str
    total_results: int
    compounds: List[Dict[str, Any]]
    search_time_ms: float


class TrialCreateRequest(BaseModel):
    trial_id: str = Field(..., min_length=1, description="Unique trial identifier")
    arms: List[str] = Field(
        ..., min_length=2, description="Trial arm names (minimum 2)"
    )

    @field_validator("arms")
    @classmethod
    def arms_must_be_unique(cls, v: List[str]) -> List[str]:
        if len(v) != len(set(v)):
            raise ValueError("arm names must be unique")
        return v


class TrialAllocationResponse(BaseModel):
    trial_id: str
    allocated_arm: str
    enrolled_counts: Dict[str, int]


class TrialOutcomeRequest(BaseModel):
    arm: str
    success: bool


class PatientEligibilityRequest(BaseModel):
    patient: Dict[str, Any] = Field(
        ...,
        description="Patient profile (age, sex, genomic_variants, comorbidities, etc.)",
    )
    trial: Dict[str, Any] = Field(
        ...,
        description="Trial eligibility criteria (min_age, max_age, required_markers, etc.)",
    )


class PatientEligibilityResponse(BaseModel):
    patient_id: str
    trial_id: str
    eligible: bool


class GWASRunRequest(BaseModel):
    variants: List[Dict[str, Any]] = Field(
        ...,
        description="List of variant objects (variant_id, chromosome, position, ref, alt, maf, hwe_p, missingness)",
    )
    case_allele_counts: List[List[int]] = Field(
        ..., description="Per-variant [ref_count, alt_count] for cases"
    )
    control_allele_counts: List[List[int]] = Field(
        ..., description="Per-variant [ref_count, alt_count] for controls"
    )
    correction_method: str = Field("bonferroni", description="'bonferroni' or 'bh'")
    association_method: str = Field(
        "chi_square", description="'chi_square' or 'logistic'"
    )

    @field_validator("correction_method")
    @classmethod
    def valid_correction(cls, v: str) -> str:
        if v not in ("bonferroni", "bh"):
            raise ValueError("correction_method must be 'bonferroni' or 'bh'")
        return v

    @field_validator("association_method")
    @classmethod
    def valid_association(cls, v: str) -> str:
        if v not in ("chi_square", "logistic"):
            raise ValueError("association_method must be 'chi_square' or 'logistic'")
        return v


class GWASRunResponse(BaseModel):
    n_variants_tested: int
    n_significant: int
    n_loci: int
    qc_summary: Dict[str, Any]
    top_hits: List[Dict[str, Any]]


class DrugDiscoveryRequest(BaseModel):
    disease: str = Field(..., min_length=3, description="Disease name to investigate")
    max_targets: int = Field(3, ge=1, le=10)
    max_candidates: int = Field(5, ge=1, le=20)


class AgentDescription(BaseModel):
    role: str
    focus: str
    tools: List[str]


class DrugDiscoveryResponse(BaseModel):
    disease: str
    status: str
    message: str
    agent_descriptions: List[AgentDescription]


# ---------------------------------------------------------------------------
# In-memory registry for demo trials (use a real DB in production)
# ---------------------------------------------------------------------------
_trial_registry: Dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get("/health", tags=["Platform"])
def health_check() -> Dict[str, str]:
    """Return platform health status."""
    return {"status": "healthy", "version": "1.0.0"}


# ---------------------------------------------------------------------------
# Compound Library endpoints
# ---------------------------------------------------------------------------


@app.post(
    "/v1/compounds/search", response_model=CompoundSearchResponse, tags=["Compounds"]
)
def search_compounds(request: CompoundSearchRequest) -> CompoundSearchResponse:
    """Perform semantic search across the compound library.

    Returns compounds ranked by semantic similarity to the query.
    Supports optional filters on molecular weight, target protein, mechanism,
    and therapeutic area.
    """
    import time

    from compound_library.compound_searcher import CompoundSearcher

    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")

    try:
        searcher = CompoundSearcher(
            collection_name="compound_library",
            qdrant_url=qdrant_url,
            qdrant_api_key=qdrant_api_key,
        )
    except Exception as exc:
        logger.error(f"Failed to connect to Qdrant: {exc}")
        raise HTTPException(
            status_code=503, detail="Compound library unavailable"
        ) from exc

    start = time.time()
    try:
        compounds = searcher.search(
            request.query, filters=request.filters, limit=request.limit
        )
    except Exception as exc:
        logger.error(f"Compound search failed: {exc}")
        raise HTTPException(
            status_code=500, detail=f"Search failed: {str(exc)}"
        ) from exc

    elapsed_ms = (time.time() - start) * 1000

    return CompoundSearchResponse(
        query=request.query,
        total_results=len(compounds),
        compounds=compounds,
        search_time_ms=round(elapsed_ms, 2),
    )


# ---------------------------------------------------------------------------
# Clinical Trials endpoints
# ---------------------------------------------------------------------------


@app.post("/v1/trials", response_model=Dict[str, str], tags=["Clinical Trials"])
def create_trial(request: TrialCreateRequest) -> Dict[str, str]:
    """Create a new adaptive clinical trial with Thompson sampling allocation."""
    from unittest.mock import patch

    from clinical_trials.realtime_optimizer import AdaptiveTrialDesign

    if request.trial_id in _trial_registry:
        raise HTTPException(
            status_code=409, detail=f"Trial {request.trial_id} already exists"
        )

    kafka_bootstrap = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")

    try:
        with patch("clinical_trials.realtime_optimizer.KafkaProducer"):
            trial = AdaptiveTrialDesign(
                trial_id=request.trial_id,
                arms=request.arms,
                kafka_bootstrap=kafka_bootstrap,
            )
        _trial_registry[request.trial_id] = trial
    except Exception as exc:
        logger.error(f"Failed to create trial: {exc}")
        raise HTTPException(
            status_code=500, detail=f"Trial creation failed: {str(exc)}"
        ) from exc

    return {
        "trial_id": request.trial_id,
        "status": "created",
        "arms": str(request.arms),
    }


@app.post(
    "/v1/trials/{trial_id}/allocate",
    response_model=TrialAllocationResponse,
    tags=["Clinical Trials"],
)
def allocate_patient(trial_id: str) -> TrialAllocationResponse:
    """Allocate the next patient to a trial arm using Thompson sampling."""
    trial = _trial_registry.get(trial_id)
    if trial is None:
        raise HTTPException(status_code=404, detail=f"Trial {trial_id} not found")

    try:
        allocated_arm = trial.allocate_next_patient()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return TrialAllocationResponse(
        trial_id=trial_id,
        allocated_arm=allocated_arm,
        enrolled_counts=dict(trial.enrolled),
    )


@app.post(
    "/v1/trials/{trial_id}/outcome",
    response_model=Dict[str, Any],
    tags=["Clinical Trials"],
)
def record_outcome(trial_id: str, request: TrialOutcomeRequest) -> Dict[str, Any]:
    """Record a patient outcome for a trial arm and update Bayesian posteriors."""
    trial = _trial_registry.get(trial_id)
    if trial is None:
        raise HTTPException(status_code=404, detail=f"Trial {trial_id} not found")

    if request.arm not in trial.arms:
        raise HTTPException(
            status_code=400, detail=f"Arm '{request.arm}' not in trial {trial_id}"
        )

    try:
        trial.update_outcome(request.arm, request.success)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "trial_id": trial_id,
        "arm": request.arm,
        "success": request.success,
        "updated_successes": dict(trial.successes),
        "updated_failures": dict(trial.failures),
    }


@app.post(
    "/v1/trials/eligibility",
    response_model=PatientEligibilityResponse,
    tags=["Clinical Trials"],
)
def check_patient_eligibility(
    request: PatientEligibilityRequest,
) -> PatientEligibilityResponse:
    """Check whether a patient meets eligibility criteria for a trial."""
    from unittest.mock import patch

    from clinical_trials.realtime_optimizer import (
        PatientProfile,
        RealTimePatientMatcher,
    )

    patient_data = request.patient
    trial_data = request.trial

    try:
        patient = PatientProfile(
            patient_id=patient_data.get("patient_id", "unknown"),
            age=int(patient_data.get("age", 0)),
            sex=patient_data.get("sex", ""),
            genomic_variants=patient_data.get("genomic_variants", []),
            comorbidities=patient_data.get("comorbidities", []),
            biomarkers=patient_data.get("biomarkers", {}),
            medications=patient_data.get("medications", []),
            prior_trials=patient_data.get("prior_trials", []),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=422, detail=f"Invalid patient data: {exc}"
        ) from exc

    with patch("clinical_trials.realtime_optimizer.qdrant_client.QdrantClient"):
        matcher = RealTimePatientMatcher(qdrant_host="localhost", qdrant_port=6333)

    eligible = matcher.check_eligibility(patient, trial_data)

    return PatientEligibilityResponse(
        patient_id=patient.patient_id,
        trial_id=trial_data.get("trial_id", ""),
        eligible=eligible,
    )


# ---------------------------------------------------------------------------
# GWAS Analysis endpoints
# ---------------------------------------------------------------------------


@app.post("/v1/gwas/run", response_model=GWASRunResponse, tags=["GWAS"])
def run_gwas(request: GWASRunRequest) -> GWASRunResponse:
    """Run a full GWAS analysis pipeline on provided variant data.

    Includes QC filtering, association testing, multiple testing correction,
    and independent locus identification via LD clumping.
    """
    from gwas.gwas_analyzer import GWASAnalyzer, Variant

    if len(request.variants) != len(request.case_allele_counts):
        raise HTTPException(
            status_code=422,
            detail="variants and case_allele_counts must have the same length",
        )
    if len(request.variants) != len(request.control_allele_counts):
        raise HTTPException(
            status_code=422,
            detail="variants and control_allele_counts must have the same length",
        )

    try:
        variants = [
            Variant(
                variant_id=v["variant_id"],
                chromosome=str(v["chromosome"]),
                position=int(v["position"]),
                ref_allele=v["ref_allele"],
                alt_allele=v["alt_allele"],
                minor_allele_frequency=float(v["maf"]),
                hwe_p_value=float(v.get("hwe_p", 1.0)),
                genotype_missingness=float(v.get("missingness", 0.0)),
            )
            for v in request.variants
        ]
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=422, detail=f"Invalid variant data: {exc}"
        ) from exc

    case_counts = [np.array(c) for c in request.case_allele_counts]
    ctrl_counts = [np.array(c) for c in request.control_allele_counts]

    analyzer = GWASAnalyzer(
        association_method=request.association_method,
        correction_method=request.correction_method,
    )

    try:
        output = analyzer.run(variants, case_counts, ctrl_counts)
    except Exception as exc:
        logger.error(f"GWAS analysis failed: {exc}")
        raise HTTPException(status_code=500, detail=f"GWAS failed: {str(exc)}") from exc

    # Serialize top hits (up to 20 most significant)
    results_sorted = sorted(output["results"], key=lambda r: r.p_value)[:20]
    top_hits = [
        {
            "variant_id": r.variant_id,
            "chromosome": r.chromosome,
            "position": r.position,
            "ref_allele": r.ref_allele,
            "alt_allele": r.alt_allele,
            "maf": r.minor_allele_frequency,
            "p_value": r.p_value,
            "effect_size": r.effect_size,
            "odds_ratio": r.odds_ratio,
            "genome_wide_significant": r.is_genome_wide_significant,
        }
        for r in results_sorted
    ]

    return GWASRunResponse(
        n_variants_tested=output["qc_summary"]["passing_variant_count"],
        n_significant=output["n_significant"],
        n_loci=len(output["loci"]),
        qc_summary=output["qc_summary"],
        top_hits=top_hits,
    )


# ---------------------------------------------------------------------------
# Drug Discovery agent workflow endpoint
# ---------------------------------------------------------------------------


@app.post(
    "/v1/drug-discovery/run",
    response_model=DrugDiscoveryResponse,
    tags=["Drug Discovery"],
)
def run_drug_discovery(request: DrugDiscoveryRequest) -> DrugDiscoveryResponse:
    """Launch the multi-agent drug discovery pipeline for a given disease.

    Returns pipeline metadata and agent descriptions. The full pipeline
    requires a configured LLM (set OPENAI_API_KEY or ANTHROPIC_API_KEY
    environment variables). In environments without LLM credentials the
    endpoint returns agent descriptions only.
    """
    from agents.drug_discovery import DrugDiscoveryPipeline, _CREWAI_AVAILABLE

    if not _CREWAI_AVAILABLE:
        return DrugDiscoveryResponse(
            disease=request.disease,
            status="unavailable",
            message="crewai is not installed. Install with: pip install crewai",
            agent_descriptions=[],
        )

    openai_key = os.getenv("OPENAI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    if not openai_key and not anthropic_key:
        # Return agent descriptions only without executing the pipeline
        pipeline = DrugDiscoveryPipeline.__new__(DrugDiscoveryPipeline)
        pipeline.llm = None
        pipeline.verbose = False
        return DrugDiscoveryResponse(
            disease=request.disease,
            status="pending_credentials",
            message=(
                "Drug discovery pipeline configured. Provide OPENAI_API_KEY or "
                "ANTHROPIC_API_KEY to execute the full multi-agent workflow."
            ),
            agent_descriptions=pipeline.get_agent_descriptions(),
        )

    try:
        if openai_key:
            from langchain_openai import ChatOpenAI

            llm = ChatOpenAI(model="gpt-4o", temperature=0, api_key=openai_key)
        else:
            from langchain_anthropic import ChatAnthropic

            llm = ChatAnthropic(
                model="claude-sonnet-4-20250514", temperature=0, api_key=anthropic_key
            )

        pipeline = DrugDiscoveryPipeline(llm=llm, verbose=False)
        result = pipeline.run(
            disease=request.disease,
            max_targets=request.max_targets,
            max_candidates=request.max_candidates,
        )

        return DrugDiscoveryResponse(
            disease=request.disease,
            status="completed",
            message=result.final_report[:2000],  # Truncate for HTTP response
            agent_descriptions=pipeline.get_agent_descriptions(),
        )
    except Exception as exc:
        logger.error(f"Drug discovery pipeline failed: {exc}")
        raise HTTPException(
            status_code=500, detail=f"Drug discovery pipeline failed: {str(exc)}"
        ) from exc


@app.get(
    "/v1/drug-discovery/agents",
    response_model=List[AgentDescription],
    tags=["Drug Discovery"],
)
def list_drug_discovery_agents() -> List[AgentDescription]:
    """List all specialized agents in the drug discovery pipeline."""
    from agents.drug_discovery import DrugDiscoveryPipeline, _CREWAI_AVAILABLE

    if not _CREWAI_AVAILABLE:
        raise HTTPException(status_code=503, detail="crewai is not installed")

    pipeline = DrugDiscoveryPipeline.__new__(DrugDiscoveryPipeline)
    pipeline.llm = None
    pipeline.verbose = False
    return pipeline.get_agent_descriptions()
