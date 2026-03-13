import pytest
from src.research_framework.discovery_tool import GenomicDiscoveryTool
from src.research_framework.evaluation import ResearchEvaluation, EvaluationCriterion, Score
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_end_to_end_discovery_with_refinement(mocker):
    # Setup mocks
    mocker.patch("src.integrations.mistral_adapter.MistralGenomicAdapter.run_agent_task")
    mocker.patch("src.integrations.mistral_adapter.MistralGenomicAdapter.analyze_genomic_data", return_value="Research Findings")
    mocker.patch("src.integrations.mistral_adapter.MistralGenomicAdapter.get_text_embedding", return_value=[0.1]*768)

    # Mock evaluation to trigger refinement (low score)
    low_eval = ResearchEvaluation(
        scientific_accuracy=EvaluationCriterion(explanation="Accurate", score=Score.low_relevance),
        clinical_relevance=EvaluationCriterion(explanation="Relevant", score=Score.high_relevance),
        groundedness=EvaluationCriterion(explanation="Grounded", score=Score.high_relevance)
    )
    mocker.patch("src.research_framework.evaluation.ResearchJudge.evaluate_discovery", return_value=low_eval)

    # Mock swarm orchestrator
    mock_orchestrator = MagicMock()
    mock_orchestrator.delegate_task_with_context = AsyncMock(return_value={"status": "refined"})

    tool = GenomicDiscoveryTool()
    tool.swarm.orchestrator = mock_orchestrator

    report = await tool.accelerate_research("Cystic Fibrosis")

    assert report["indication"] == "Cystic Fibrosis"
    assert "refinement" in report
    assert report["refinement"]["status"] == "refined"

@pytest.mark.asyncio
async def test_link_prediction(mocker):
    from src.research_framework.knowledge_graph import BiologicalKnowledgeGraph

    mocker.patch("src.integrations.mistral_adapter.MistralGenomicAdapter.get_text_embedding", side_effect=[[1,0], [0.9, 0.1], [0.1, 0.9]])

    kg = BiologicalKnowledgeGraph()
    await kg.add_entity("A", "Type", {"description": "A"})
    await kg.add_entity("B", "Type", {"description": "B"})
    await kg.add_entity("C", "Type", {"description": "C"})

    predictions = kg.predict_links(threshold=0.8)

    assert len(predictions) >= 1
    assert predictions[0][0] == "A"
    assert predictions[0][1] == "B"
    assert predictions[0][2] > 0.8
