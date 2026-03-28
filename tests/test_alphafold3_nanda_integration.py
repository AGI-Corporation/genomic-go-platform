"""Tests for AlphaFold3 NANDA integration module."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from integrations.alphafold3_nanda_integration import (
    AgentTaskStatus,
    AlphaFoldTask,
    NANDAProtocolCoordinator,
    AlphaFold3NANDAIntegration,
)


class TestAlphaFoldTask:
    """Tests for the AlphaFoldTask dataclass."""

    def test_default_status_is_pending(self):
        task = AlphaFoldTask(
            task_id="t1",
            sequence="MKTFF",
            model_seeds=[1, 2],
            created_at=datetime.utcnow().isoformat(),
        )
        assert task.status == AgentTaskStatus.PENDING

    def test_default_retry_count_is_zero(self):
        task = AlphaFoldTask(
            task_id="t1",
            sequence="MKTFF",
            model_seeds=[1],
            created_at=datetime.utcnow().isoformat(),
        )
        assert task.retry_count == 0

    def test_default_assigned_node_is_none(self):
        task = AlphaFoldTask(
            task_id="t1",
            sequence="MKTFF",
            model_seeds=[1],
            created_at=datetime.utcnow().isoformat(),
        )
        assert task.assigned_node is None


class TestNANDAProtocolCoordinator:
    """Tests for NANDAProtocolCoordinator."""

    @pytest.fixture
    def coordinator(self):
        return NANDAProtocolCoordinator(redundancy_factor=2)

    def test_initialization(self, coordinator):
        assert coordinator.redundancy_factor == 2
        assert coordinator.nodes == {}
        assert coordinator.active_tasks == {}
        assert coordinator.heartbeat_timeout == 30

    def test_register_node_stores_node(self, coordinator):
        coordinator.register_node("node-01", ["alphafold3"], "http://node1.example.com")
        assert "node-01" in coordinator.nodes
        node = coordinator.nodes["node-01"]
        assert node["capabilities"] == ["alphafold3"]
        assert node["endpoint"] == "http://node1.example.com"
        assert node["status"] == "online"
        assert node["load"] == 0

    def test_register_multiple_nodes(self, coordinator):
        coordinator.register_node("node-01", ["alphafold3"], "http://node1")
        coordinator.register_node("node-02", ["alphafold3", "genomics"], "http://node2")
        assert len(coordinator.nodes) == 2

    def test_select_nodes_by_capability(self, coordinator):
        coordinator.register_node("node-01", ["alphafold3"], "http://node1")
        coordinator.register_node("node-02", ["genomics"], "http://node2")

        selected = coordinator._select_nodes("alphafold3", 5)
        assert "node-01" in selected
        assert "node-02" not in selected

    def test_select_nodes_online_only(self, coordinator):
        coordinator.register_node("node-01", ["alphafold3"], "http://node1")
        coordinator.register_node("node-02", ["alphafold3"], "http://node2")
        coordinator.nodes["node-02"]["status"] = "offline"

        selected = coordinator._select_nodes("alphafold3", 5)
        assert "node-01" in selected
        assert "node-02" not in selected

    def test_select_nodes_sorted_by_load(self, coordinator):
        coordinator.register_node("node-01", ["alphafold3"], "http://node1")
        coordinator.register_node("node-02", ["alphafold3"], "http://node2")
        coordinator.nodes["node-01"]["load"] = 5
        coordinator.nodes["node-02"]["load"] = 1

        selected = coordinator._select_nodes("alphafold3", 1)
        assert selected == ["node-02"]

    def test_select_nodes_respects_count(self, coordinator):
        for i in range(5):
            coordinator.register_node(f"node-0{i}", ["alphafold3"], f"http://node{i}")

        selected = coordinator._select_nodes("alphafold3", 2)
        assert len(selected) == 2

    def test_select_nodes_no_match_returns_empty(self, coordinator):
        coordinator.register_node("node-01", ["genomics"], "http://node1")

        selected = coordinator._select_nodes("alphafold3", 2)
        assert selected == []

    @pytest.mark.asyncio
    async def test_submit_task_no_nodes_sets_failed_status(self, coordinator):
        task_id = await coordinator.submit_task("MKTFF", [1, 2, 3])
        assert task_id in coordinator.active_tasks
        assert coordinator.active_tasks[task_id].status == AgentTaskStatus.FAILED

    @pytest.mark.asyncio
    async def test_submit_task_with_nodes_adds_to_active_tasks(self, coordinator):
        coordinator.register_node("node-01", ["alphafold3"], "http://node1")
        coordinator.register_node("node-02", ["alphafold3"], "http://node2")

        task_id = await coordinator.submit_task("MKTFF", [1, 2, 3])
        assert task_id in coordinator.active_tasks

    @pytest.mark.asyncio
    async def test_submit_task_returns_unique_ids(self, coordinator):
        coordinator.register_node("node-01", ["alphafold3"], "http://node1")

        id1 = await coordinator.submit_task("SEQ1", [1])
        id2 = await coordinator.submit_task("SEQ2", [2])
        assert id1 != id2

    @pytest.mark.asyncio
    async def test_dispatch_to_nodes_increments_load(self, coordinator):
        coordinator.register_node("node-01", ["alphafold3"], "http://node1")
        task = AlphaFoldTask(
            task_id="t1",
            sequence="MKTFF",
            model_seeds=[1],
            created_at=datetime.utcnow().isoformat(),
        )
        await coordinator._dispatch_to_nodes(task, ["node-01"])
        assert coordinator.nodes["node-01"]["load"] == 1

    @pytest.mark.asyncio
    async def test_dispatch_to_multiple_nodes(self, coordinator):
        coordinator.register_node("node-01", ["alphafold3"], "http://node1")
        coordinator.register_node("node-02", ["alphafold3"], "http://node2")
        task = AlphaFoldTask(
            task_id="t2",
            sequence="MKTFF",
            model_seeds=[1],
            created_at=datetime.utcnow().isoformat(),
        )
        await coordinator._dispatch_to_nodes(task, ["node-01", "node-02"])
        assert coordinator.nodes["node-01"]["load"] == 1
        assert coordinator.nodes["node-02"]["load"] == 1

    @pytest.mark.asyncio
    async def test_handle_node_failure_reassigns_incomplete_tasks(self, coordinator):
        """Test that tasks assigned to a failed node are reassigned."""
        coordinator.register_node("node-01", ["alphafold3"], "http://node1")
        coordinator.register_node("node-02", ["alphafold3"], "http://node2")

        # Manually create a task assigned to node-01
        task = AlphaFoldTask(
            task_id="task-001",
            sequence="MKTFF",
            model_seeds=[1],
            created_at=datetime.utcnow().isoformat(),
            assigned_node="node-01",
        )
        coordinator.active_tasks["task-001"] = task

        # Mark node-01 offline so the failover selects node-02
        coordinator.nodes["node-01"]["status"] = "offline"

        await coordinator._handle_node_failure("node-01")

        # node-02 should have received the reassigned task (load increased)
        assert coordinator.nodes["node-02"]["load"] == 1

    @pytest.mark.asyncio
    async def test_handle_node_failure_skips_completed_tasks(self, coordinator):
        """Test that completed tasks are not reassigned after node failure."""
        coordinator.register_node("node-01", ["alphafold3"], "http://node1")
        coordinator.register_node("node-02", ["alphafold3"], "http://node2")

        task = AlphaFoldTask(
            task_id="task-done",
            sequence="MKTFF",
            model_seeds=[1],
            created_at=datetime.utcnow().isoformat(),
            assigned_node="node-01",
            status=AgentTaskStatus.COMPLETED,
        )
        coordinator.active_tasks["task-done"] = task

        await coordinator._handle_node_failure("node-01")

        # node-02 should not receive the completed task
        assert coordinator.nodes["node-02"]["load"] == 0


class TestAlphaFold3NANDAIntegration:
    """Tests for the high-level AlphaFold3NANDAIntegration wrapper."""

    @pytest.fixture
    def coordinator(self):
        c = NANDAProtocolCoordinator(redundancy_factor=1)
        c.register_node("node-01", ["alphafold3"], "http://node1")
        return c

    @pytest.fixture
    def integration(self, coordinator):
        return AlphaFold3NANDAIntegration(coordinator=coordinator)

    @pytest.mark.asyncio
    async def test_predict_structure_returns_task_id_and_status(self, integration):
        result = await integration.predict_structure("MKTFFIVLLSCVPVFA")
        assert "task_id" in result
        assert result["status"] == "submitted"

    @pytest.mark.asyncio
    async def test_predict_structure_task_id_is_string(self, integration):
        result = await integration.predict_structure("MKTFF")
        assert isinstance(result["task_id"], str)
        assert len(result["task_id"]) > 0

    @pytest.mark.asyncio
    async def test_predict_structure_registers_task(self, integration, coordinator):
        result = await integration.predict_structure("MKTFF")
        assert result["task_id"] in coordinator.active_tasks
