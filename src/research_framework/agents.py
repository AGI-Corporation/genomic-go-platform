"""Specialized Research Agents for Genomic Swarm

This module defines concrete implementations of research agents
that handle specific steps in the genomic discovery pipeline.
"""

import os
from typing import Dict, Any, Optional
from src.integrations.mistral_adapter import MistralGenomicAdapter
from src.compound_library.compound_searcher import CompoundSearcher


class BaseGenomicAgent:
    """Base class for all genomic research agents."""

    def __init__(self, role: str, api_key: str = None):
        self.role = role
        self.mistral = MistralGenomicAdapter(api_key)
        self.tools: Dict[str, Any] = {}

    def register_tool(self, name: str, tool_func: Any):
        """Registers a new tool for the agent to use."""
        self.tools[name] = tool_func


class LiteratureAgent(BaseGenomicAgent):
    """Agent specialized in mining and summarizing scientific literature."""

    def __init__(self, api_key: str = None):
        super().__init__("Literature Reviewer", api_key)

    async def process_task(
        self, task: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        prompt = f"Review the latest literature for: {task.get('description')}. focus on clinical relevance."
        result = await self.mistral.analyze_genomic_data("", prompt)
        return {"role": self.role, "summary": result}


class TargetDiscoveryAgent(BaseGenomicAgent):
    """Agent specialized in identifying therapeutic targets from multi-omic data."""

    def __init__(self, api_key: str = None):
        super().__init__("Target Identification Specialist", api_key)
        from src.utils.bio_parsers import parse_fasta

        self.register_tool("fasta_parser", parse_fasta)

    async def process_task(
        self, task: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        fasta_data = context.get("fasta_data", "")
        prompt = f"Identify high-confidence drug targets for: {task.get('description')}. Use genetic evidence."
        if fasta_data:
            prompt += f"\n\nAnalyzed sequence data: {fasta_data[:1000]}"

        result = await self.mistral.analyze_genomic_data("", prompt)
        return {"role": self.role, "targets": result}


class LeadOptimizationAgent(BaseGenomicAgent):
    """Agent specialized in compound screening and lead optimization."""

    def __init__(self, api_key: str = None, qdrant_url: Optional[str] = None):
        super().__init__("Lead Chemist", api_key)
        self.qdrant_url = qdrant_url or os.getenv("QDRANT_URL")
        self.searcher = None
        if self.qdrant_url:
            try:
                self.searcher = CompoundSearcher(
                    collection_name="compound_library", qdrant_url=self.qdrant_url
                )
            except Exception:
                self.searcher = None

    async def process_task(
        self, task: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        description = task.get("description", "")
        prompt = f"Propose lead compounds or chemical scaffolds for: {description}."
        llm_result = await self.mistral.analyze_genomic_data("", prompt)

        semantic_results = []
        if self.searcher:
            try:
                semantic_results = self.searcher.search(description, limit=3)
            except Exception:
                semantic_results = []

        return {
            "role": self.role,
            "proposed_leads": llm_result,
            "library_matches": semantic_results,
        }


class BioinformaticsAgent(BaseGenomicAgent):
    """Agent specialized in variant interpretation and sequence analysis."""

    def __init__(self, api_key: str = None):
        super().__init__("Bioinformatics Scientist", api_key)
        from src.utils.bio_parsers import parse_vcf

        self.register_tool("vcf_parser", parse_vcf)

    async def process_task(
        self, task: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        vcf_data = context.get("vcf_data", "")
        prompt = f"Analyze genomic variants for clinical significance: {task.get('description')}."
        if vcf_data:
            prompt += f"\n\nInput VCF variants: {vcf_data}"

        result = await self.mistral.analyze_genomic_data("", prompt)
        return {"role": self.role, "variant_analysis": result}


class SafetyAgent(BaseGenomicAgent):
    """Agent specialized in toxicity and ADME prediction."""

    def __init__(self, api_key: str = None):
        super().__init__("Safety & Toxicity Specialist", api_key)

    async def process_task(
        self, task: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        prompt = f"Evaluate the safety and potential toxicity profile for: {task.get('description')}."
        result = await self.mistral.analyze_genomic_data("", prompt)
        return {"role": self.role, "safety_assessment": result}


class RegulatoryAgent(BaseGenomicAgent):
    """Agent specialized in clinical trial submission and regulatory compliance."""

    def __init__(self, api_key: str = None):
        super().__init__("Regulatory Affairs Officer", api_key)

    async def process_task(
        self, task: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        prompt = f"Prepare regulatory summary and trial design considerations for: {task.get('description')}."
        result = await self.mistral.analyze_genomic_data("", prompt)
        return {"role": self.role, "regulatory_summary": result}


class VisionResearchAgent(BaseGenomicAgent):
    """Agent specialized in biological image analysis using Pixtral."""

    def __init__(self, api_key: str = None):
        super().__init__("Multimodal Vision Researcher", api_key)

    async def process_task(
        self, task: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        image_path = context.get("image_path")
        if not image_path:
            return {"role": self.role, "error": "No image provided for vision analysis."}

        prompt = f"Analyze this biological image for research insights related to {task.get('description')}."
        result = await self.mistral.analyze_biological_image(image_path, prompt)
        return {"role": self.role, "vision_analysis": result}
