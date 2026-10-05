"""Unit tests for agents/base.py - ReviewState and ToolRegistry."""

import pytest
from typing import TypedDict, Annotated


def test_review_state_has_required_fields():
    """ReviewState must contain all required fields per AGENTS.md."""
    # Import will fail until agents/base.py is created
    from agents.base import ReviewState

    state: ReviewState = {
        "pr_number": 1,
        "repo_url": "https://github.com/example/repo",
        "diff": "",
        "files": [],
        "findings": [],
        "current_agent": "",
        "metadata": {},
    }
    assert state["pr_number"] == 1
    assert state["repo_url"] == "https://github.com/example/repo"
    assert state["diff"] == ""
    assert state["files"] == []
    assert state["findings"] == []
    assert state["current_agent"] == ""
    assert state["metadata"] == {}


def test_review_state_typedict():
    """ReviewState must be a TypedDict with correct structure."""
    from agents.base import ReviewState

    # Verify it's a TypedDict
    assert hasattr(ReviewState, '__annotations__')

    # Verify all expected fields exist in annotations
    expected_fields = {"pr_number", "repo_url", "diff", "files", "findings", "current_agent", "metadata"}
    actual_fields = set(ReviewState.__annotations__.keys())
    assert actual_fields == expected_fields, f"Expected {expected_fields}, got {actual_fields}"