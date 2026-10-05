"""Unit tests for supervisor node - LangGraph routing agent."""

import pytest
from unittest.mock import MagicMock, patch

from agents.base import ReviewState, Finding


def test_supervisor_routes_to_code_reviewer_first():
    """Supervisor must determine first step routes to code_reviewer."""
    from agents.supervisor import supervisor_node

    # Set up mock state - no workers have run yet
    state: ReviewState = {
        "pr_number": 123,
        "repo_url": "https://github.com/example/repo",
        "diff": "@@ -1,3 +1,4 @@\ndef add(a, b):\n    return a + b\n",
        "files": ["src/math.py"],
        "findings": [],
        "current_agent": "",
        "metadata": {},
    }

    # Mock the LLM - supervisor should return code_reviewer
    with patch("agents.supervisor.get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        # Supervisor prompts LLM to choose next worker
        mock_llm.invoke.return_value = "code_reviewer"
        mock_get_llm.return_value = mock_llm

        # Call the supervisor node
        result = supervisor_node(state)

        # Should return a Command routing to code_reviewer
        from langgraph.types import Command
        assert isinstance(result, Command)
        assert result.goto == "code_reviewer"


def test_supervisor_routes_to_security_auditor_after_code_reviewer():
    """Supervisor must route to security_auditor after code_reviewer has run."""
    from agents.supervisor import supervisor_node

    # Set up mock state - code_reviewer has run, security_auditor has not
    state: ReviewState = {
        "pr_number": 123,
        "repo_url": "https://github.com/example/repo",
        "diff": "@@ -1,3 +1,4 @@\ndef add(a, b):\n    return a + b\n",
        "files": ["src/math.py"],
        "findings": [],
        "current_agent": "code_reviewer",
        "metadata": {"completed": ["code_reviewer"]},
    }

    with patch("agents.supervisor.get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = "security_auditor"
        mock_get_llm.return_value = mock_llm

        result = supervisor_node(state)
        from langgraph.types import Command
        assert isinstance(result, Command)
        assert result.goto == "security_auditor"


def test_supervisor_terminates_after_all_workers():
    """Supervisor must terminate (END) when all workers have completed."""
    from agents.supervisor import supervisor_node

    # Set up mock state - all workers have run
    state: ReviewState = {
        "pr_number": 123,
        "repo_url": "https://github.com/example/repo",
        "diff": "@@ -1,3 +1,4 @@\ndef add(a, b):\n    return a + b\n",
        "files": ["src/math.py"],
        "findings": [],
        "current_agent": "test_generator",
        "metadata": {"completed": ["code_reviewer", "security_auditor", "test_generator"]},
    }

    with patch("agents.supervisor.get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = "END"
        mock_get_llm.return_value = mock_llm

        result = supervisor_node(state)
        from langgraph.types import Command
        assert isinstance(result, Command)
        assert result.goto == "END"  # supervisor terminates the graph


def test_supervisor_handles_invalid_llm_output():
    """Supervisor must default to END when LLM returns invalid destination."""
    from agents.supervisor import supervisor_node

    state: ReviewState = {
        "pr_number": 123,
        "repo_url": "https://github.com/example/repo",
        "diff": "@@ -1,3 +1,4 @@\ndef add(a, b):\n    return a + b\n",
        "files": ["src/math.py"],
        "findings": [],
        "current_agent": "",
        "metadata": {},
    }

    with patch("agents.supervisor.get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = "arbitrary_node_not_allowed"
        mock_get_llm.return_value = mock_llm

        result = supervisor_node(state)
        from langgraph.types import Command
        # Should default to END for invalid output
        assert isinstance(result, Command)
        assert result.goto == "END"