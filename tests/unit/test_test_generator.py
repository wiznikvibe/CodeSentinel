"""Unit tests for test_generator node - LangGraph test suggestion agent."""

import pytest
from unittest.mock import MagicMock, patch


def test_test_generator_appends_suggestions():
    """Test generator must read ReviewState, format prompt, call LLM, and append suggestions.

    The test_generator node should:
    1. Read diff and files from ReviewState
    2. Format the prompt using core/prompts/test_generator.md
    3. Call the LLM with the formatted prompt
    4. Append resulting test suggestions to state['test_suggestions']
    """
    # Import will fail until test_generator.py is created
    from agents.test_generator import generate_tests

    # Set up mock state with existing findings
    state: dict = {
        "pr_number": 123,
        "repo_url": "https://github.com/example/repo",
        "diff": "@@ -1,3 +1,4 @@\ndef add(a, b):\n    return a + b\n-    pass\n+    pass\n",
        "files": ["src/math.py"],
        "findings": [],
        "current_agent": "test_generator",
        "metadata": {},
    }

    # Mock the LLM call - the generator should return structured suggestions
    with patch("agents.test_generator.get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = '[{"title": "Test add function", "description": "Test the add function with various inputs", "file": "src/math.py", "line": 1, "test_type": "unit"}, {"title": "Test add edge cases", "description": "Test add with negative numbers and zero", "file": "src/math.py", "line": 5, "test_type": "unit"}]'
        mock_get_llm.return_value = mock_llm

        # Call the generator node
        result = generate_tests(state)

        # Should return state with test suggestions appended
        assert "test_suggestions" in result
        assert len(result["test_suggestions"]) > 0
        # Each suggestion should be a dict
        assert isinstance(result["test_suggestions"][0], dict)
        assert result["test_suggestions"][0]["title"] == "Test add function"
        assert result["test_suggestions"][0]["test_type"] == "unit"