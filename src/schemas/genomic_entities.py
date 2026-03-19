"""Genomic Data Schemas

Standardized data models for biological entities and research tasks,
ensuring interoperability across the agent swarm.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class GenomicMarker(BaseModel):
    """Schema for genomic markers/variants."""

    gene: str
    variant: str
    significance: Optional[str] = None
    rsid: Optional[str] = None


class PatientData(BaseModel):
    """Schema for patient clinical and genomic profiles."""

    patient_id: str
    age: int
    sex: str
    genomic_variants: List[GenomicMarker]
    comorbidities: List[str]
    biomarkers: Dict[str, float]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ResearchDiscovery(BaseModel):
    """Schema for a research discovery report."""

    indication: str
    targets: List[str]
    lead_compounds: List[str]
    confidence_score: float
    agent_id: str
    reasoning: str
    metadata: Dict[str, Any] = {}


class SwarmTaskSchema(BaseModel):
    """Schema for tasks delegated within the swarm."""

    task_id: str
    description: str
    priority: int
    assigned_agent: Optional[str] = None
    status: str = "pending"


class EntityExtraction(BaseModel):
    """Schema for biological entity extraction."""

    class Entity(BaseModel):
        id: str
        type: str = Field(..., description="Type of entity: gene, protein, compound, disease")
        description: str

    entities: List[Entity]


class InteroperableTask(BaseModel):
    """Schema for standardized task communication between frameworks."""

    task_id: str
    source_framework: str = Field(..., description="e.g., Mistral, NANDA")
    target_framework: str
    task_type: str
    payload: Dict[str, Any]
    priority: int = 1
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentArtifact(BaseModel):
    """Schema for biological artifacts produced by agents."""

    artifact_id: str
    agent_id: str
    type: str = Field(
        ..., description="e.g., pdb_structure, genomic_profile, lead_compound"
    )
    data: Any
    metadata: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
