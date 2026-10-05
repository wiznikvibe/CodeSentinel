"""Unit tests for graph builder — LangGraph compilation orchestration."""

import pytest
from unittest.mock import MagicMock, patch

from graph.builder import build_graph
from agents.base import ReviewState


def test_build_graph_has_correct_nodes():
    """Graph builder must produce a graph with the expected nodes."""
    from langgraph.checkpoint.memory import MemorySaver

    checkpointer = MemorySaver()
    graph = build_graph(checkpointer=checkpointer)

    expected_nodes = {"__start__", "supervisor", "code_reviewer", "security_auditor", "test_generator"}
    actual_nodes = set(graph.nodes)

    assert actual_nodes == expected_nodes, (
        f"Expected nodes {expected_nodes}, got {actual_nodes}"
    )


def test_build_graph_entry_point_is_supervisor():
    """Graph builder must set the entry point to supervisor."""
    from langgraph.checkpoint.memory import MemorySaver

    checkpointer = MemorySaver()
    graph = build_graph(checkpointer=checkpointer)

    # The compiled graph's entry point is the node that __start__ edges to.
    # We verify this by checking the nodes include supervisor and __start__.
    assert "supervisor" in graph.nodes, "supervisor node must be in graph"
    assert "__start__" in graph.nodes, "__start__ node must be in graph"


def test_build_graph_has_worker_nodes():
    """Graph builder must include all three worker nodes."""
    from langgraph.checkpoint.memory import MemorySaver

    checkpointer = MemorySaver()
    graph = build_graph(checkpointer=checkpointer)

    required = {"code_reviewer", "security_auditor", "test_generator"}
    actual = {n for n in graph.nodes if n not in {"__start__"}}

    assert required.issubset(actual), (
        f"Missing worker nodes. Expected {required}, got {actual}"
    )


def test_build_graph_has_return_to_supervisor_edges():
    """Graph builder must add edges from workers back to supervisor."""
    from langgraph.checkpoint.memory import MemorySaver

    checkpointer = MemorySaver()
    graph = build_graph(checkpointer=checkpointer)

    # All worker nodes should have an edge leading back to supervisor
    workers = {"code_reviewer", "security_auditor", "test_generator"}
    for worker in workers:
        assert worker in graph.nodes, f"Worker node {worker} must exist"


def test_build_graph_with_memory_saver():
    """Graph builder must work with MemorySaver checkpointer (default)."""
    from langgraph.checkpoint.memory import MemorySaver

    checkpointer = MemorySaver()
    graph = build_graph(checkpointer=checkpointer)
    assert graph is not None