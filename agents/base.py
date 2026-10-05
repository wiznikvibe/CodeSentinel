"""BaseAgent — shared state, tool registry, and patterns for all LangGraph agents.

This module defines the single source of truth for agent state via ReviewState
TypedDict and the ToolRegistry pattern for pure functions with Pydantic I/O.
"""

from typing import TypedDict, Annotated


class Finding:
    """A finding/issue identified during code review or security audit."""

    def __init__(
        self,
        severity: str,
        title: str,
        description: str,
        file_path: str | None = None,
        line_number: int | None = None,
    ):
        self.severity = severity
        self.title = title
        self.description = description
        self.file_path = file_path
        self.line_number = line_number

    def __repr__(self):
        return f"Finding(severity={self.severity!r}, title={self.title!r})"


class ReviewState(TypedDict):
    """Single source of truth for all agent state.

    All LangGraph agents (code_reviewer, security_auditor, supervisor)
    read and write this state. The `findings` field accumulates across
    agents using `add_messages`-style annotation.
    """

    pr_number: int
    """Pull request number being reviewed."""

    repo_url: str
    """Repository URL where the PR originates."""

    diff: str
    """The full diff/patch content to analyze."""

    files: list[str]
    """List of changed file paths."""

    findings: Annotated[list[Finding], ...]
    """Accumulated findings from all agents, annotated with add_messages."""

    current_agent: str
    """Name of the agent currently processing the state."""

    metadata: dict
    """Free-form metadata dict for tracking additional context."""


# ToolRegistry — placeholder for pure functions with Pydantic I/O
# Each tool should be a pure async function with Pydantic validated inputs/outputs
# Registered here and invoked via the graph.

analyze_complexity = None  # type: ignore[assignment]
"""Placeholder: async function analyzing code complexity from a diff."""


def register_tool(name: str, func):
    """Register a pure function as a tool in the ToolRegistry.

    Args:
        name: The tool name identifier.
        func: An async function with Pydantic-validated I/O.

    Returns:
        The registered function.
    """
    globals()[name] = func
    return func