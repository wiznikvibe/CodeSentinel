"""LangGraph builder — compiles the review orchestration graph.

Provides `build_graph(checkpointer)` which returns a compiled LangGraph
with the supervisor node and worker nodes (code_reviewer, security_auditor,
test_generator) wired together.

Entry point: START -> supervisor
Routing: supervisor returns Command(goto=X) → graph routes to node X
         worker → supervisor (fixed edge) → supervisor decides next → ... → END
"""

from typing import Any, Optional

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph
from langgraph.types import Command

from agents.base import ReviewState
from agents.code_reviewer import review_diff
from agents.security_auditor import audit_diff
from agents.test_generator import generate_tests
from agents.supervisor import supervisor_node


def build_graph(checkpointer: Optional[Any] = None) -> Any:
    """Build and return a compiled LangGraph for the code review workflow.

    Args:
        checkpointer: Optional checkpoint saver. Defaults to MemorySaver()
            for dev/local execution. Pass a PostgresSaver instance for
            production checkpointing.

    Returns:
        A compiled LangGraph graph ready for execution.

    The graph workflow:
        START -> supervisor -> (LLM routing) -> worker -> supervisor -> ...
        The supervisor returns Command(goto=...) to determine the next node.
        Valid goto values: "code_reviewer", "security_auditor", "test_generator", "END"

    Recursion limit: Set to 25 per-invocation via config dict (e.g.,
    `config={"recursion_limit": 25}`). The builder does not set a default
    since invocation context varies (dev testing vs production).
    """
    # === Graph construction ===

    # Define the StateGraph with ReviewState as the schema
    graph = StateGraph(ReviewState)

    # === Add nodes ===

    # Supervisor node — decides which worker should execute next
    graph.add_node("supervisor", supervisor_node)

    # Worker nodes — each reads ReviewState, calls LLM, appends findings/suggestions
    graph.add_node("code_reviewer", review_diff)
    graph.add_node("security_auditor", audit_diff)
    graph.add_node("test_generator", generate_tests)

    # === Edges ===

    # Entry point: START -> supervisor
    graph.set_entry_point("supervisor")

    # After each worker completes, route back to supervisor
    # This creates the loop: supervisor → worker → supervisor → worker → ...
    graph.add_edge("code_reviewer", "supervisor")
    graph.add_edge("security_auditor", "supervisor")
    graph.add_edge("test_generator", "supervisor")

    # The supervisor returns Command(goto=X) which automatically routes
    # the graph to the named node (or END to terminate).
    # No explicit conditional edges from supervisor are needed — the
    # Command's `goto` field determines the routing at runtime.

    # === Compile ===

    if checkpointer is None:
        checkpointer = MemorySaver()

    compiled_graph = graph.compile(checkpointer=checkpointer)

    return compiled_graph