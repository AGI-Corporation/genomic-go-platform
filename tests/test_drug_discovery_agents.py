"""Tests for CrewAI Drug Discovery multi-agent pipeline."""

import sys
import os
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from agents.drug_discovery import (
    ADMETPredictionAgent,
    DrugDiscoveryConfig,
    DrugDiscoveryPipeline,
    DrugDiscoveryResult,
    LiteratureMiningAgent,
    MoleculeGenerationAgent,
    ResearchReportAgent,
    TargetDiscoveryAgent,
    _build_tasks,
    _require_crewai,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_llm():
    return MagicMock(name="MockLLM")


# ---------------------------------------------------------------------------
# Unit tests (no crewai dependency)
# ---------------------------------------------------------------------------


class TestDrugDiscoveryConfig:
    def test_defaults(self):
        config = DrugDiscoveryConfig(disease="Cancer")
        assert config.max_targets == 3
        assert config.max_candidates == 5
        assert config.verbose is False
        assert config.additional_context == ""

    def test_custom_values(self):
        config = DrugDiscoveryConfig(
            disease="Parkinson's disease",
            max_targets=5,
            max_candidates=10,
            verbose=True,
        )
        assert config.max_targets == 5
        assert config.max_candidates == 10


class TestDrugDiscoveryResult:
    def test_defaults(self):
        result = DrugDiscoveryResult(disease="Alzheimer's")
        assert result.targets == []
        assert result.literature_summary == ""
        assert result.candidate_molecules == []
        assert result.admet_summary == ""
        assert result.final_report == ""
        assert result.raw_crew_output is None

    def test_with_values(self):
        result = DrugDiscoveryResult(
            disease="Cancer",
            targets=["EGFR", "KRAS"],
            final_report="Report text",
        )
        assert len(result.targets) == 2
        assert result.final_report == "Report text"


class TestRequireCrewai:
    def test_raises_when_unavailable(self):
        """_require_crewai should raise ImportError when crewai is not installed."""
        with patch("agents.drug_discovery._CREWAI_AVAILABLE", False):
            with pytest.raises(ImportError, match="crewai"):
                _require_crewai()

    def test_no_error_when_available(self):
        """_require_crewai should not raise when crewai is available."""
        with patch("agents.drug_discovery._CREWAI_AVAILABLE", True):
            _require_crewai()  # should not raise


# ---------------------------------------------------------------------------
# Tests with crewai mocked out
# ---------------------------------------------------------------------------

MOCK_AGENT = MagicMock()
MOCK_TASK = MagicMock()
MOCK_CREW = MagicMock()


def _patch_crewai():
    """Return a context manager that patches crewai imports."""
    return patch.multiple(
        "agents.drug_discovery",
        _CREWAI_AVAILABLE=True,
        Agent=MagicMock(return_value=MOCK_AGENT),
        Task=MagicMock(return_value=MOCK_TASK),
        Crew=MagicMock(return_value=MOCK_CREW),
    )


class TestAgentFactories:
    """Each agent factory should instantiate an Agent with the right role."""

    def test_target_discovery_agent(self):
        mock_agent_cls = MagicMock()
        with patch("agents.drug_discovery._CREWAI_AVAILABLE", True), patch(
            "agents.drug_discovery.Agent", mock_agent_cls
        ):
            TargetDiscoveryAgent.build(llm=_mock_llm())
        mock_agent_cls.assert_called_once()
        call_kwargs = mock_agent_cls.call_args.kwargs
        assert "Target Discovery" in call_kwargs["role"]

    def test_literature_mining_agent(self):
        mock_agent_cls = MagicMock()
        with patch("agents.drug_discovery._CREWAI_AVAILABLE", True), patch(
            "agents.drug_discovery.Agent", mock_agent_cls
        ):
            LiteratureMiningAgent.build(llm=_mock_llm())
        call_kwargs = mock_agent_cls.call_args.kwargs
        assert "Literature" in call_kwargs["role"]

    def test_molecule_generation_agent(self):
        mock_agent_cls = MagicMock()
        with patch("agents.drug_discovery._CREWAI_AVAILABLE", True), patch(
            "agents.drug_discovery.Agent", mock_agent_cls
        ):
            MoleculeGenerationAgent.build(llm=_mock_llm())
        call_kwargs = mock_agent_cls.call_args.kwargs
        assert "Medicinal Chemist" in call_kwargs["role"]

    def test_admet_prediction_agent(self):
        mock_agent_cls = MagicMock()
        with patch("agents.drug_discovery._CREWAI_AVAILABLE", True), patch(
            "agents.drug_discovery.Agent", mock_agent_cls
        ):
            ADMETPredictionAgent.build(llm=_mock_llm())
        call_kwargs = mock_agent_cls.call_args.kwargs
        assert "ADMET" in call_kwargs["role"]

    def test_report_agent(self):
        mock_agent_cls = MagicMock()
        with patch("agents.drug_discovery._CREWAI_AVAILABLE", True), patch(
            "agents.drug_discovery.Agent", mock_agent_cls
        ):
            ResearchReportAgent.build(llm=_mock_llm())
        call_kwargs = mock_agent_cls.call_args.kwargs
        assert "Director" in call_kwargs["role"]


class TestBuildTasks:
    def test_returns_five_tasks(self):
        mock_task_cls = MagicMock(side_effect=lambda **kw: MagicMock())
        config = DrugDiscoveryConfig(
            disease="Alzheimer's", max_targets=3, max_candidates=5
        )
        agents = [MagicMock() for _ in range(5)]
        with patch("agents.drug_discovery._CREWAI_AVAILABLE", True), patch(
            "agents.drug_discovery.Task", mock_task_cls
        ):
            tasks = _build_tasks(config, *agents)
        assert len(tasks) == 5

    def test_disease_in_task_description(self):
        task_instances = []

        def capture_task(**kwargs):
            m = MagicMock()
            m.description = kwargs.get("description", "")
            task_instances.append(m)
            return m

        config = DrugDiscoveryConfig(disease="Parkinson's disease")
        agents = [MagicMock() for _ in range(5)]
        with patch("agents.drug_discovery._CREWAI_AVAILABLE", True), patch(
            "agents.drug_discovery.Task", side_effect=capture_task
        ):
            _build_tasks(config, *agents)

        # At least one task should mention the disease
        assert any("Parkinson" in t.description for t in task_instances)


class TestDrugDiscoveryPipeline:
    def test_raises_without_crewai(self):
        with patch("agents.drug_discovery._CREWAI_AVAILABLE", False):
            with pytest.raises(ImportError):
                DrugDiscoveryPipeline(llm=_mock_llm())

    def test_get_agent_descriptions(self):
        with patch("agents.drug_discovery._CREWAI_AVAILABLE", True):
            pipeline = DrugDiscoveryPipeline.__new__(DrugDiscoveryPipeline)
            pipeline.llm = _mock_llm()
            pipeline.verbose = False
            descriptions = pipeline.get_agent_descriptions()

        assert len(descriptions) == 5
        roles = [d["role"] for d in descriptions]
        assert any("Target" in r for r in roles)
        assert any("Literature" in r for r in roles)
        assert any("Medicinal" in r for r in roles)
        assert any("ADMET" in r for r in roles)
        assert any("Director" in r for r in roles)

    def test_run_invokes_crew_kickoff(self):
        mock_crew_instance = MagicMock()
        mock_crew_instance.kickoff.return_value = "Final report text"
        mock_crew_cls = MagicMock(return_value=mock_crew_instance)
        mock_agent_cls = MagicMock(return_value=MagicMock())
        mock_task_cls = MagicMock(return_value=MagicMock())

        from crewai.process import (
            Process as RealProcess,
        )  # noqa: F401 (only for mock ref)

        with patch("agents.drug_discovery._CREWAI_AVAILABLE", True), patch(
            "agents.drug_discovery.Agent", mock_agent_cls
        ), patch("agents.drug_discovery.Task", mock_task_cls), patch(
            "agents.drug_discovery.Crew", mock_crew_cls
        ), patch(
            "agents.drug_discovery.Process", MagicMock(sequential=MagicMock())
        ):
            pipeline = DrugDiscoveryPipeline(llm=_mock_llm())
            result = pipeline.run("Alzheimer's disease")

        mock_crew_instance.kickoff.assert_called_once()
        assert isinstance(result, DrugDiscoveryResult)
        assert result.disease == "Alzheimer's disease"
        assert "Final report text" in result.final_report

    def test_run_result_contains_disease(self):
        mock_crew = MagicMock()
        mock_crew.kickoff.return_value = "Some output"

        with patch("agents.drug_discovery._CREWAI_AVAILABLE", True), patch(
            "agents.drug_discovery.Agent", MagicMock(return_value=MagicMock())
        ), patch(
            "agents.drug_discovery.Task", MagicMock(return_value=MagicMock())
        ), patch(
            "agents.drug_discovery.Crew", MagicMock(return_value=mock_crew)
        ), patch(
            "agents.drug_discovery.Process", MagicMock(sequential=MagicMock())
        ):
            pipeline = DrugDiscoveryPipeline(llm=_mock_llm())
            result = pipeline.run(
                "Parkinson's disease", max_targets=2, max_candidates=3
            )

        assert result.disease == "Parkinson's disease"
