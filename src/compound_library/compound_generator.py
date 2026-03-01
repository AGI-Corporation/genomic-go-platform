"""Mistral-Powered Compound Generator

Uses Mistral Large's reasoning capabilities to propose novel lead compounds
and optimized chemical scaffolds based on genomic targets.
"""

from typing import List, Dict, Any, Optional
from src.integrations.mistral_adapter import MistralGenomicAdapter


class CompoundGenerator:
    """Generates novel chemical entities using agentic reasoning."""

    def __init__(self, api_key: Optional[str] = None):
        self.mistral = MistralGenomicAdapter(api_key)

    async def generate_novel_leads(
        self, target_description: str, indication: str
    ) -> List[str]:
        """Proposes novel lead compounds for a given biological target."""
        prompt = f"""
        Given the biological target: {target_description}
        For the indication: {indication}
        Propose 3-5 novel chemical scaffolds or lead compound classes that could potentially inhibit or modulate this target.
        Focus on drug-likeness, synthetic accessibility, and novel mechanism of action.
        """

        response = await self.mistral.analyze_genomic_data("", prompt)
        return [line.strip() for line in response.split("\n") if line.strip()]


class CompoundGenerationAgent:
    """Agentic wrapper for the compound generator to work within the research swarm."""

    def __init__(self, api_key: Optional[str] = None):
        self.generator = CompoundGenerator(api_key)
        self.role = "Lead Optimization Specialist"

    async def process_task(
        self, task: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handles compound generation tasks from the orchestrator."""
        target = task.get("target_id", "Unknown Protein")
        indication = task.get("indication", "General Research")

        print(f"[{self.role}] Generating leads for {target} in {indication}...")
        leads = await self.generator.generate_novel_leads(target, indication)

        return {"role": self.role, "proposed_leads": leads, "status": "leads_generated"}
