import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

# Set mock key in environment
os.environ["MISTRAL_API_KEY"] = "mock_key"

from src.research_framework.discovery_tool import GenomicDiscoveryTool

async def test_mock_discovery():
    with patch('src.integrations.mistral_adapter.Mistral') as mock_mistral:
        instance = mock_mistral.return_value
        # Mock embeddings
        instance.embeddings.create_async = AsyncMock(return_value=MagicMock(
            data=[MagicMock(embedding=[0.1]*768)]
        ))
        # Mock chat completion
        instance.chat.complete_async = AsyncMock(return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(content="lit_agent"))]
        ))

        tool = GenomicDiscoveryTool()
        report = await tool.accelerate_research("Cystic Fibrosis")

        print(f"Report Indication: {report['indication']}")
        print(f"Status: {report['status']}")
        assert report['status'] == "research_accelerated"
        assert report['indication'] == "Cystic Fibrosis"
        # Check if agent execution was triggered
        for task in report['swarm_intelligence_summary']:
            assert 'agent_execution' in task

        print("Integration test PASSED")

if __name__ == "__main__":
    asyncio.run(test_mock_discovery())
