"""Genomic Data Schemas

Standardized data models for biological entities and research tasks,
ensuring interoperability across the agent swarm.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


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
    timestamp: datetime = Field(default_factory=datetime.utcnow)


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
