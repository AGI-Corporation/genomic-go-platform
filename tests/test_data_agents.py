import pytest
from src.research_framework.agents import BioinformaticsAgent, TargetDiscoveryAgent, VisionResearchAgent
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_bioinformatics_agent_vcf(mocker):
    mocker.patch("src.integrations.mistral_adapter.MistralGenomicAdapter.analyze_genomic_data", return_value="Interpretation: High risk variant.")
    agent = BioinformaticsAgent()
    task = {"description": "Check BRCA1 mutations"}
    context = {"vcf_data": "rs123	C	T"}

    result = await agent.process_task(task, context)
    assert result["role"] == "Bioinformatics Scientist"
    assert "Interpretation" in result["variant_analysis"]

@pytest.mark.asyncio
async def test_target_discovery_agent_fasta(mocker):
    mocker.patch("src.integrations.mistral_adapter.MistralGenomicAdapter.analyze_genomic_data", return_value="Target: BACE1 identified.")
    agent = TargetDiscoveryAgent()
    task = {"description": "Find targets in BACE1"}
    context = {"fasta_data": ">BACE1\nMAQALPW"}

    result = await agent.process_task(task, context)
    assert result["role"] == "Target Identification Specialist"
    assert "Target" in result["targets"]

@pytest.mark.asyncio
async def test_vision_research_agent(mocker):
    mocker.patch("src.integrations.mistral_adapter.MistralGenomicAdapter.analyze_biological_image", return_value="Image analysis: Clear protein structure.")
    agent = VisionResearchAgent()
    task = {"description": "Analyze protein structure"}
    context = {"image_path": "data/sample/protein_structure.png"}

    result = await agent.process_task(task, context)
    assert result["role"] == "Multimodal Vision Researcher"
    assert "Image analysis" in result["vision_analysis"]
