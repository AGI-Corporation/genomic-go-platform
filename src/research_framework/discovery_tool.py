"""Integrated Research & Development Discovery Tool

A consolidated interface that brings together Mistral-powered swarms,
multimodal biological analysis, and knowledge graph reasoning.
"""

import asyncio
import json
import os
from typing import List, Dict, Any, Optional
from src.research_framework.swarm import GenomicSwarmFramework
from src.research_framework.agents import (
    LiteratureAgent,
    TargetDiscoveryAgent,
    LeadOptimizationAgent,
)
from src.compound_library.compound_generator import CompoundGenerationAgent
from src.research_framework.knowledge_graph import BiologicalKnowledgeGraph
from src.research_framework.evaluation import ResearchJudge
from src.integrations.mistral_adapter import MistralGenomicAdapter


class GenomicDiscoveryTool:
    """The central R&D tool for Genomic.go."""

    def __init__(self, api_key: Optional[str] = None):
        self.swarm = GenomicSwarmFramework()
        self.kg = BiologicalKnowledgeGraph(api_key)
        self.mistral = MistralGenomicAdapter(api_key)
        self.judge = ResearchJudge(api_key)

        # Register specialized agents
        self.swarm.orchestrator.register_agent("lit_agent", LiteratureAgent(api_key))
        self.swarm.orchestrator.register_agent(
            "target_agent", TargetDiscoveryAgent(api_key)
        )
        self.swarm.orchestrator.register_agent(
            "lead_agent", LeadOptimizationAgent(api_key)
        )
        self.swarm.orchestrator.register_agent(
            "gen_agent", CompoundGenerationAgent(api_key)
        )

    async def accelerate_research(self, indication: str):
        """Runs the complete R&D acceleration pipeline with experiment tracking."""
        print(f"Accelerating R&D for: {indication}")

        # 1. Swarm Intelligence Literature & Target Mining
        print("Deploying Swarm Intelligence for target identification...")
        swarm_results = await self.swarm.run_discovery_pipeline(indication)

        # 2. Knowledge Graph Enrichment
        print("Populating Biological Knowledge Graph...")
        await self.kg.add_entity(
            indication, "disease", {"description": f"Target disease: {indication}"}
        )

        # 3. Automated Evaluation (LLM-as-a-Judge)
        print("Evaluating research quality using Mistral Judge...")
        evaluation = await self.judge.evaluate_discovery(
            query=f"Discover therapeutic insights for {indication}",
            context=f"Genomic and literature data processed for {indication}",
            findings=str(swarm_results),
        )

        # 4. Compile Final Report
        report = {
            "indication": indication,
            "swarm_intelligence_summary": swarm_results,
            "evaluation": evaluation.model_dump(),
            "kg_nodes": len(self.kg.graph.nodes),
            "status": "research_accelerated",
        }

        # 5. Lab Notebook: Persistence
        self._save_to_notebook(report)

        return report

    def _save_to_notebook(self, report: Dict[str, Any]):
        """Persists the research findings to the local lab notebook."""
        os.makedirs("lab_notebook", exist_ok=True)
        safe_name = report["indication"].lower().replace(" ", "_")
        filename = f"lab_notebook/discovery_{safe_name}.json"

        with open(filename, "w") as f:
            json.dump(report, f, indent=2)
        print(f"Research findings persisted to: {filename}")


async def main():
    tool = GenomicDiscoveryTool()
    report = await tool.accelerate_research("Alzheimer's Disease")
    print("\n--- Research Report ---")
    print(report)


if __name__ == "__main__":
    asyncio.run(main())
