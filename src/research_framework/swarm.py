"""Genomic Swarm Intelligence Framework

A decentralized, agentic research framework optimized for Mistral AI,
enabling collaborative genomic discovery through specialized swarms.
"""

import asyncio
from typing import List, Dict, Any, Optional, Protocol
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from src.integrations.mistral_adapter import MistralGenomicAdapter


class ResearchAgent(Protocol):
    """Protocol for specialized research agents."""

    role: str

    async def process_task(
        self, task: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]: ...


@dataclass
class SwarmTask:
    """A task to be executed by the research swarm."""

    id: str
    description: str
    priority: int = 1
    required_capabilities: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class SwarmOrchestrator:
    """Orchestrates specialized swarms using Mistral Large reasoning."""

    def __init__(self, api_key: Optional[str] = None):
        self.mistral = MistralGenomicAdapter(api_key)
        self.agents: Dict[str, ResearchAgent] = {}
        self.task_history: List[Dict[str, Any]] = []

    def register_agent(self, agent_id: str, agent: ResearchAgent):
        """Registers a new specialized agent to the swarm."""
        self.agents[agent_id] = agent

    async def delegate_task(self, task: SwarmTask) -> Dict[str, Any]:
        return await self.delegate_task_with_context(task, {})

    async def delegate_task_with_context(
        self, task: SwarmTask, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Uses Mistral tool-calling to decide and execute research tasks."""
        # Define tools for the orchestrator
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "assign_to_agent",
                    "description": "Assign a task to a specialized agent",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "agent_id": {
                                "type": "string",
                                "enum": list(self.agents.keys()),
                            },
                            "priority": {"type": "integer"},
                        },
                        "required": ["agent_id"],
                    },
                },
            }
        ]

        # Step 1: Use Mistral to decide agent assignment via tool calling
        prompt = f"Decide which agent is best for this genomic task: {task.description}"
        decision = await self.mistral.run_agent_task(prompt, tools)

        # Step 2: Execute task through recommended agents
        execution_result = {
            "task_id": task.id,
            "status": "completed",
            "orchestrator_decision": decision,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Mock agent execution
        for agent_id, agent in self.agents.items():
            # In hackathon mode, we often match based on ID substring if decision is empty
            if agent_id in decision or task.id.lower() in agent_id.lower():
                agent_result = await agent.process_task(asdict(task), context)
                execution_result["agent_execution"] = agent_result
                break

        self.task_history.append(execution_result)
        return execution_result


class GenomicSwarmFramework:
    """The entry point for the Genomic.go research and development tool."""

    def __init__(self):
        self.orchestrator = SwarmOrchestrator()

    async def run_discovery_pipeline(self, indication: str, context: Dict[str, Any] = None):
        """Executes an end-to-end genomic discovery pipeline."""
        print(f"Starting discovery pipeline for: {indication}")
        context = context or {}

        # Define swarm tasks
        tasks = [
            SwarmTask(
                "LIT_REVIEW", f"Summarize recent genomic literature for {indication}"
            ),
            SwarmTask(
                "TARGET_ID",
                f"Identify candidate drug targets for {indication} using GWAS data",
            ),
            SwarmTask(
                "COMPOUND_SCREEN",
                f"Search for lead compounds targeting identified proteins for {indication}",
            ),
            SwarmTask(
                "VARIANT_ANALYSIS",
                f"Analyze patient genomic variants relevant to {indication}",
            ),
            SwarmTask(
                "SAFETY_ADME",
                f"Predict safety and ADME profile for potential {indication} leads",
            ),
            SwarmTask(
                "REGULATORY_PREP",
                f"Prepare initial regulatory brief for {indication} clinical trial",
            ),
        ]

        # Add vision task if image present
        if context.get("image_path"):
            tasks.append(
                SwarmTask(
                    "IMAGE_ANALYSIS", f"Analyze biological imagery for {indication}"
                )
            )

        results = []
        for task in tasks:
            print(f"Executing task: {task.id}...")
            result = await self.orchestrator.delegate_task_with_context(task, context)
            results.append(result)

        return results


if __name__ == "__main__":
    print("Genomic Swarm Framework Initialized for Mistral Hackathon.")
