"""Unit tests for code_reviewer node - LangGraph code review agent."""

import pytest
from unittest.mock import MagicMock, patch


def test_code_reviewer_appends_findings():
    """Code reviewer must read ReviewState, format prompt, call LLM, and append findings.

    The code_reviewer node should:
    1. Read diff and files from ReviewState
    2. Format the prompt using core/prompts/code_reviewer.md
    3. Call the LLM with the formatted prompt
    4. Append resulting findings to state['findings']
    """
    # Import will fail until code_reviewer.py is created
    from agents.code_reviewer import review_diff

    # Set up mock state
    state: dict = {
        "pr_number": 123,
        "repo_url": "https://github.com/example/repo",
        "diff": "@@ -1,3 +1,4 @@\ndef add(a, b):\n    return a + b\n-    pass\n+    pass\n",
        "files": ["src/math.py"],
        "findings": [],
        "current_agent": "code_reviewer",
        "metadata": {},
    }

    # Mock the LLM call - the reviewer should return structured findings
    with patch("agents.code_reviewer.get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = "Mocked LLM response"
        mock_get_llm.return_value = mock_llm

        # Call the reviewer node
        result = review_diff(state)

        # Should return state with findings appended
        assert "findings" in result
        assert len(result["findings"]) > 0
        # The findings should be Finding objects
        from agents.base import Finding
        assert isinstance(result["findings"][0], Finding)