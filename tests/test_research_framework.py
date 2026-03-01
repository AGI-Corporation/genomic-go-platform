import pytest
from src.research_framework.knowledge_graph import BiologicalKnowledgeGraph
from src.research_framework.swarm import GenomicSwarmFramework

@pytest.mark.asyncio
async def test_knowledge_graph_basic(mocker):
    # Mocking Mistral to avoid API calls
    mocker.patch("src.integrations.mistral_adapter.MistralGenomicAdapter.get_text_embedding", return_value=[0.1, 0.2, 0.3])

    kg = BiologicalKnowledgeGraph()
    await kg.add_entity("BRCA1", "Gene", {"description": "Breast cancer type 1 susceptibility protein"})
    await kg.add_entity("Breast Cancer", "Disease", {})
    kg.add_interaction("BRCA1", "Breast Cancer", "ASSOCIATED_WITH")

    assert "BRCA1" in kg.graph.nodes
    assert kg.graph.has_edge("BRCA1", "Breast Cancer")

def test_swarm_initialization():
    swarm = GenomicSwarmFramework()
    # Let's check the orchestrator
    assert swarm.orchestrator is not None
