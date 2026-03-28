"""Tests for NANDA agent integration module."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from integrations.nanda_agent_integration import (
    NANDAAgentConfig,
    NANDAAgentIntegration,
)


@pytest.fixture
def config():
    return NANDAAgentConfig(
        anthropic_key="test-key-123",
        domain="genomic.test.network",
        agent_id="agent-001",
        num_agents=2,
    )


@pytest.fixture
def integration(config):
    return NANDAAgentIntegration(config=config)


@pytest.fixture
def integration_with_agent(integration):
    """Integration pre-loaded with one deployed agent."""
    integration.deployed_agents["agent-001"] = {
        "agent_id": "agent-001",
        "type": "research",
        "specialization": "genomics",
        "endpoint": "https://genomic.test.network",
        "status": "active",
        "deployed_at": datetime.utcnow().isoformat(),
    }
    integration.agent_states["agent-001"] = "running"
    return integration


class TestNANDAAgentIntegrationInit:
    """Tests for NANDAAgentIntegration initialization."""

    def test_stores_config(self, integration, config):
        assert integration.config is config

    def test_deployed_agents_starts_empty(self, integration):
        assert integration.deployed_agents == {}

    def test_agent_states_starts_empty(self, integration):
        assert integration.agent_states == {}


class TestGetAgentStatus:
    """Tests for get_agent_status."""

    def test_returns_not_found_for_unknown_agent(self, integration):
        result = integration.get_agent_status("nonexistent-id")
        assert result == {"status": "not_found"}

    def test_returns_agent_info_for_known_agent(self, integration_with_agent):
        with patch.object(
            integration_with_agent, "_check_agent_health", return_value="healthy"
        ):
            result = integration_with_agent.get_agent_status("agent-001")

        assert result["agent_id"] == "agent-001"
        assert result["current_state"] == "running"
        assert result["health"] == "healthy"

    def test_includes_all_agent_fields(self, integration_with_agent):
        with patch.object(
            integration_with_agent, "_check_agent_health", return_value="healthy"
        ):
            result = integration_with_agent.get_agent_status("agent-001")

        assert "type" in result
        assert "specialization" in result
        assert "endpoint" in result
        assert "status" in result


class TestCheckAgentHealth:
    """Tests for _check_agent_health."""

    def test_returns_healthy_on_200(self, integration):
        mock_response = Mock()
        mock_response.status_code = 200
        with patch("integrations.nanda_agent_integration.requests.get", return_value=mock_response):
            health = integration._check_agent_health(
                {"endpoint": "https://genomic.test.network"}
            )
        assert health == "healthy"

    def test_returns_unhealthy_on_non_200(self, integration):
        mock_response = Mock()
        mock_response.status_code = 503
        with patch("integrations.nanda_agent_integration.requests.get", return_value=mock_response):
            health = integration._check_agent_health(
                {"endpoint": "https://genomic.test.network"}
            )
        assert health == "unhealthy"

    def test_returns_unreachable_on_exception(self, integration):
        with patch(
            "integrations.nanda_agent_integration.requests.get",
            side_effect=ConnectionError("timeout"),
        ):
            health = integration._check_agent_health(
                {"endpoint": "https://unreachable.network"}
            )
        assert health == "unreachable"


class TestGenerateAgentId:
    """Tests for _generate_agent_id."""

    def test_returns_string(self, integration):
        agent_id = integration._generate_agent_id()
        assert isinstance(agent_id, str)

    def test_returns_six_digit_number(self, integration):
        agent_id = integration._generate_agent_id()
        assert len(agent_id) == 6
        assert agent_id.isdigit()

    def test_returns_unique_ids(self, integration):
        ids = {integration._generate_agent_id() for _ in range(20)}
        # With 900,000 possible IDs, 20 draws should almost always yield many unique values
        assert len(ids) > 15


class TestSendTaskToAgent:
    """Tests for send_task_to_agent."""

    def test_raises_value_error_for_unknown_agent(self, integration):
        with pytest.raises(ValueError, match="Agent unknown-id not found"):
            asyncio.get_event_loop().run_until_complete(
                integration.send_task_to_agent("unknown-id", {"type": "genomics"})
            )

    @pytest.mark.asyncio
    async def test_returns_result_on_success(self, integration_with_agent):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "ok"}
        with patch(
            "integrations.nanda_agent_integration.requests.post",
            return_value=mock_response,
        ):
            result = await integration_with_agent.send_task_to_agent(
                "agent-001", {"type": "analysis"}
            )
        assert result == {"result": "ok"}

    @pytest.mark.asyncio
    async def test_raises_on_non_200_response(self, integration_with_agent):
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        with patch(
            "integrations.nanda_agent_integration.requests.post",
            return_value=mock_response,
        ):
            with pytest.raises(Exception, match="Task execution failed"):
                await integration_with_agent.send_task_to_agent(
                    "agent-001", {"type": "analysis"}
                )

    @pytest.mark.asyncio
    async def test_raises_on_network_error(self, integration_with_agent):
        with patch(
            "integrations.nanda_agent_integration.requests.post",
            side_effect=ConnectionError("network error"),
        ):
            with pytest.raises(ConnectionError):
                await integration_with_agent.send_task_to_agent(
                    "agent-001", {"type": "analysis"}
                )


class TestShutdownAgent:
    """Tests for shutdown_agent."""

    @pytest.mark.asyncio
    async def test_returns_false_for_unknown_agent(self, integration):
        result = await integration.shutdown_agent("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_true_on_success(self, integration_with_agent):
        mock_response = Mock()
        mock_response.status_code = 200
        with patch(
            "integrations.nanda_agent_integration.requests.post",
            return_value=mock_response,
        ):
            result = await integration_with_agent.shutdown_agent("agent-001")
        assert result is True

    @pytest.mark.asyncio
    async def test_removes_agent_from_deployed_on_success(self, integration_with_agent):
        mock_response = Mock()
        mock_response.status_code = 200
        with patch(
            "integrations.nanda_agent_integration.requests.post",
            return_value=mock_response,
        ):
            await integration_with_agent.shutdown_agent("agent-001")
        assert "agent-001" not in integration_with_agent.deployed_agents

    @pytest.mark.asyncio
    async def test_updates_state_to_stopped_on_success(self, integration_with_agent):
        mock_response = Mock()
        mock_response.status_code = 200
        with patch(
            "integrations.nanda_agent_integration.requests.post",
            return_value=mock_response,
        ):
            await integration_with_agent.shutdown_agent("agent-001")
        assert integration_with_agent.agent_states["agent-001"] == "stopped"

    @pytest.mark.asyncio
    async def test_returns_false_on_non_200_response(self, integration_with_agent):
        mock_response = Mock()
        mock_response.status_code = 503
        with patch(
            "integrations.nanda_agent_integration.requests.post",
            return_value=mock_response,
        ):
            result = await integration_with_agent.shutdown_agent("agent-001")
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_network_error(self, integration_with_agent):
        with patch(
            "integrations.nanda_agent_integration.requests.post",
            side_effect=ConnectionError("timeout"),
        ):
            result = await integration_with_agent.shutdown_agent("agent-001")
        assert result is False


class TestDistributeWorkflow:
    """Tests for distribute_workflow."""

    @pytest.fixture
    def integration_two_agents(self, integration):
        for agent_id in ["agent-001", "agent-002"]:
            integration.deployed_agents[agent_id] = {
                "agent_id": agent_id,
                "endpoint": f"https://genomic.test.network/{agent_id}",
                "status": "active",
            }
            integration.agent_states[agent_id] = "running"
        return integration

    @pytest.mark.asyncio
    async def test_distribute_workflow_collects_successful_results(
        self, integration_two_agents
    ):
        workflow = {
            "id": "wf-001",
            "steps": [{"type": "step_a"}, {"type": "step_b"}],
            "dependencies": {},
        }

        async def mock_send_task(agent_id, task):
            return {"agent": agent_id, "status": "done"}

        with patch.object(
            integration_two_agents, "send_task_to_agent", side_effect=mock_send_task
        ):
            results = await integration_two_agents.distribute_workflow(
                workflow, ["agent-001", "agent-002"]
            )

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_distribute_workflow_tolerates_agent_failure(
        self, integration_two_agents
    ):
        workflow = {
            "id": "wf-002",
            "steps": [{"type": "step_a"}, {"type": "step_b"}],
            "dependencies": {},
        }

        async def mock_send_task(agent_id, task):
            if agent_id == "agent-001":
                raise Exception("agent-001 failed")
            return {"agent": agent_id, "status": "done"}

        with patch.object(
            integration_two_agents, "send_task_to_agent", side_effect=mock_send_task
        ):
            results = await integration_two_agents.distribute_workflow(
                workflow, ["agent-001", "agent-002"]
            )

        # Only the successful result should be returned
        assert len(results) == 1
        assert results[0]["agent"] == "agent-002"

    @pytest.mark.asyncio
    async def test_distribute_workflow_partitions_steps(self, integration_two_agents):
        """Test that workflow steps are partitioned across agents."""
        captured_tasks = []

        async def capture_task(agent_id, task):
            captured_tasks.append((agent_id, task))
            return {"agent": agent_id}

        workflow = {
            "id": "wf-003",
            "steps": [
                {"type": "step_1"},
                {"type": "step_2"},
                {"type": "step_3"},
                {"type": "step_4"},
            ],
        }

        with patch.object(
            integration_two_agents, "send_task_to_agent", side_effect=capture_task
        ):
            await integration_two_agents.distribute_workflow(
                workflow, ["agent-001", "agent-002"]
            )

        # Each agent should receive some steps
        all_steps = [step for _, task in captured_tasks for step in task["steps"]]
        assert len(all_steps) == 4
