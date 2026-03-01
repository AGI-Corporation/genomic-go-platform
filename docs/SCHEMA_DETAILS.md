# 📊 Genomic.go Schema Specifications

This document provides detailed information about the standardized data schemas used in the Genomic.go platform to ensure interoperability between AI agents and biological datasets.

## 1. Core Biological Entities

### GenomicMarker
Used for representing specific genetic variations.
- **gene** (str): The gene symbol (e.g., "APOE").
- **variant** (str): The specific variant (e.g., "e4").
- **significance** (str): Clinical significance (e.g., "Pathogenic").
- **rsid** (str): The Reference SNP cluster ID.

### PatientData
The primary model for clinical trial matching and genomic analysis.
- **patient_id** (str): Unique identifier.
- **age** (int): Chronological age.
- **sex** (str): Biological sex.
- **genomic_variants** (List[GenomicMarker]): List of relevant variants.
- **comorbidities** (List[str]): List of existing conditions.
- **biomarkers** (Dict[str, float]): Quantified biological markers.

## 2. Research & Swarm Logic

### ResearchDiscovery
The structured output of a discovery pipeline session.
- **indication** (str): Target disease.
- **targets** (List[str]): Identified biological targets.
- **lead_compounds** (List[str]): Candidate compounds.
- **confidence_score** (float): AI's confidence in the findings (0.0 - 1.0).
- **agent_id** (str): The ID of the agent that finalized the report.
- **reasoning** (str): Natural language explanation of the discovery.

## 3. Mistral Integration Config

### MistralModelConfig
Ensures consistent model selection across the framework.
- **chat_model**: Default is `mistral-large-latest`.
- **embedding_model**: Default is `mistral-embed`.
- **multimodal_model**: Default is `pixtral-12b-2409`.

---

*These schemas are implemented using Pydantic for runtime validation and automatic documentation generation.*
