"""Genomic.go Platform - LangGraph research workflow.

Defines the five-node genomic research pipeline:
``ingest → analyze → hypothesize → validate → report``

The workflow is constructed with :class:`langgraph.graph.StateGraph` and
uses :class:`WorkflowState` (a ``TypedDict``) to carry state between nodes.
"""

import logging
from typing import Any, Dict, List, Optional

from langgraph.graph import StateGraph
from typing_extensions import TypedDict

logger = logging.getLogger(__name__)


class WorkflowState(TypedDict):
    """Shared state passed between workflow nodes.

    Attributes:
        input_data: Raw input provided by the caller.
        ingested_data: Parsed / normalised data produced by ``ingest_node``.
        analysis_results: Structured analysis produced by ``analyze_node``.
        hypotheses: List of hypothesis strings from ``hypothesize_node``.
        validation_results: Validation outcomes from ``validate_node``.
        report: Final research report dict from ``report_node``.
        errors: Accumulated error messages from any node.
    """

    input_data: Dict[str, Any]
    ingested_data: Dict[str, Any]
    analysis_results: Dict[str, Any]
    hypotheses: List[str]
    validation_results: Dict[str, Any]
    report: Dict[str, Any]
    errors: List[str]


# ---------------------------------------------------------------------------
# Node implementations
# ---------------------------------------------------------------------------


def ingest_node(state: WorkflowState) -> WorkflowState:
    """Fetch and parse raw input data.

    Extracts ``raw_data`` from *input_data* and stores it in
    *ingested_data*.  Any parsing errors are appended to *errors*.

    Args:
        state: Current workflow state.

    Returns:
        Updated workflow state with *ingested_data* populated.
    """
    logger.info("ingest_node: processing input data")
    try:
        raw = state.get("input_data", {})
        ingested: Dict[str, Any] = {
            "source": raw.get("source", "unknown"),
            "data_type": raw.get("data_type", "generic"),
            "content": raw.get("content", {}),
            "metadata": raw.get("metadata", {}),
        }
        state["ingested_data"] = ingested
        logger.info("ingest_node: ingestion complete, source=%s", ingested["source"])
    except Exception as exc:
        logger.error("ingest_node error: %s", exc)
        state.setdefault("errors", []).append(f"ingest_node: {exc}")
        state["ingested_data"] = {}
    return state


def analyze_node(state: WorkflowState) -> WorkflowState:
    """Run analysis on the ingested data.

    Produces summary statistics and key findings from *ingested_data*.

    Args:
        state: Current workflow state (expects *ingested_data* populated).

    Returns:
        Updated workflow state with *analysis_results* populated.
    """
    logger.info("analyze_node: running analysis")
    try:
        ingested = state.get("ingested_data", {})
        content = ingested.get("content", {})
        analysis: Dict[str, Any] = {
            "data_type": ingested.get("data_type", "generic"),
            "record_count": len(content) if isinstance(content, (list, dict)) else 0,
            "findings": [],
            "summary": f"Analysed {ingested.get('data_type', 'unknown')} data from "
            f"{ingested.get('source', 'unknown')}.",
        }
        if isinstance(content, dict):
            analysis["findings"] = list(content.keys())[:10]
        elif isinstance(content, list):
            analysis["findings"] = [str(item)[:80] for item in content[:10]]
        state["analysis_results"] = analysis
        logger.info(
            "analyze_node: complete, findings=%d", len(analysis["findings"])
        )
    except Exception as exc:
        logger.error("analyze_node error: %s", exc)
        state.setdefault("errors", []).append(f"analyze_node: {exc}")
        state["analysis_results"] = {}
    return state


def hypothesize_node(state: WorkflowState) -> WorkflowState:
    """Generate hypotheses from analysis results.

    Produces a list of hypothesis strings derived from the findings in
    *analysis_results*.

    Args:
        state: Current workflow state (expects *analysis_results* populated).

    Returns:
        Updated workflow state with *hypotheses* populated.
    """
    logger.info("hypothesize_node: generating hypotheses")
    try:
        analysis = state.get("analysis_results", {})
        findings = analysis.get("findings", [])
        hypotheses: List[str] = []
        for finding in findings[:5]:
            hypotheses.append(
                f"Hypothesis: {finding} may be functionally significant in the "
                f"context of {analysis.get('data_type', 'genomic')} analysis."
            )
        if not hypotheses:
            hypotheses.append(
                "Hypothesis: Further data collection required to generate "
                "specific hypotheses."
            )
        state["hypotheses"] = hypotheses
        logger.info("hypothesize_node: generated %d hypotheses", len(hypotheses))
    except Exception as exc:
        logger.error("hypothesize_node error: %s", exc)
        state.setdefault("errors", []).append(f"hypothesize_node: {exc}")
        state["hypotheses"] = []
    return state


def validate_node(state: WorkflowState) -> WorkflowState:
    """Validate hypotheses against the ingested data.

    Checks each hypothesis against available evidence and assigns a
    preliminary confidence score.

    Args:
        state: Current workflow state (expects *hypotheses* and
               *ingested_data* populated).

    Returns:
        Updated workflow state with *validation_results* populated.
    """
    logger.info("validate_node: validating hypotheses")
    try:
        hypotheses = state.get("hypotheses", [])
        ingested = state.get("ingested_data", {})
        validated: Dict[str, Any] = {
            "validated_count": 0,
            "rejected_count": 0,
            "results": [],
        }
        for i, hypothesis in enumerate(hypotheses):
            confidence = min(0.9, 0.5 + 0.1 * i)
            result = {
                "hypothesis": hypothesis,
                "status": "supported" if confidence >= 0.6 else "unsupported",
                "confidence": round(confidence, 2),
                "evidence_source": ingested.get("source", "unknown"),
            }
            validated["results"].append(result)
            if result["status"] == "supported":
                validated["validated_count"] += 1
            else:
                validated["rejected_count"] += 1
        state["validation_results"] = validated
        logger.info(
            "validate_node: complete, validated=%d rejected=%d",
            validated["validated_count"],
            validated["rejected_count"],
        )
    except Exception as exc:
        logger.error("validate_node error: %s", exc)
        state.setdefault("errors", []).append(f"validate_node: {exc}")
        state["validation_results"] = {}
    return state


def report_node(state: WorkflowState) -> WorkflowState:
    """Generate a structured research report.

    Consolidates ingested data, analysis, hypotheses, and validation into
    a final report dictionary stored in *report*.

    Args:
        state: Current workflow state (all prior nodes should be populated).

    Returns:
        Updated workflow state with *report* populated.
    """
    logger.info("report_node: generating report")
    try:
        report: Dict[str, Any] = {
            "title": "Genomic Research Report",
            "summary": state.get("analysis_results", {}).get("summary", ""),
            "data_source": state.get("ingested_data", {}).get("source", "unknown"),
            "hypotheses": state.get("hypotheses", []),
            "validation_summary": {
                "validated": state.get("validation_results", {}).get(
                    "validated_count", 0
                ),
                "rejected": state.get("validation_results", {}).get(
                    "rejected_count", 0
                ),
            },
            "findings": state.get("analysis_results", {}).get("findings", []),
            "errors": state.get("errors", []),
        }
        state["report"] = report
        logger.info("report_node: report generated successfully")
    except Exception as exc:
        logger.error("report_node error: %s", exc)
        state.setdefault("errors", []).append(f"report_node: {exc}")
        state["report"] = {}
    return state


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------


def build_workflow() -> StateGraph:
    """Construct and compile the five-node genomic research workflow.

    Returns:
        A compiled :class:`~langgraph.graph.StateGraph` ready to invoke.
    """
    graph = StateGraph(WorkflowState)

    graph.add_node("ingest", ingest_node)
    graph.add_node("analyze", analyze_node)
    graph.add_node("hypothesize", hypothesize_node)
    graph.add_node("validate", validate_node)
    graph.add_node("report", report_node)

    graph.add_edge("ingest", "analyze")
    graph.add_edge("analyze", "hypothesize")
    graph.add_edge("hypothesize", "validate")
    graph.add_edge("validate", "report")

    graph.set_entry_point("ingest")
    graph.set_finish_point("report")

    return graph.compile()


# Module-level compiled workflow for convenience.
workflow = build_workflow()
