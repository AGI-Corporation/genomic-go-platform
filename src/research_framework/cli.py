"""Command-Line Interface for Genomic Discovery Tool

A terminal-based interface for researchers to interact with the
Mistral-powered genomic swarm intelligence framework.
"""

import asyncio
import argparse
import sys
import json
from src.research_framework.discovery_tool import GenomicDiscoveryTool


async def run_discovery(indication: str):
    """Main entry point for the discovery CLI."""
    print("=" * 60)
    print(f"🧬 Genomic.go Discovery Pipeline: {indication}")
    print("=" * 60)

    tool = GenomicDiscoveryTool()
    try:
        report = await tool.accelerate_research(indication)

        print("\n" + "*" * 20 + " Research Report " + "*" * 20)
        print(f"Indication: {report['indication']}")
        print(f"Knowledge Graph Nodes: {report['kg_nodes']}")
        print(f"Status: {report['status']}")

        print("\nSwarm Decisions:")
        for res in report["swarm_intelligence_summary"]:
            print(f"- {res['task_id']}: {res['orchestrator_decision']}")

        print("\nPipeline execution complete.")

    except Exception as e:
        print(f"\n❌ Error during research acceleration: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Genomic.go R&D Acceleration Tool")
    parser.add_argument(
        "indication", type=str, help="The target indication/disease (e.g., 'Alzheimer')"
    )

    args = parser.parse_args()

    asyncio.run(run_discovery(args.indication))


if __name__ == "__main__":
    main()
