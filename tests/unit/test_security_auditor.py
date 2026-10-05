"""Unit tests for security_auditor node - LangGraph security audit agent."""

import pytest
from unittest.mock import MagicMock, patch


def test_security_auditor_appends_findings():
    """Security auditor must read ReviewState, format prompt, call LLM, and append findings.

    The security_auditor node should:
    1. Read diff and files from ReviewState
    2. Format the prompt using core/prompts/security.md
    3. Call the LLM with the formatted prompt
    4. Append resulting findings to state['findings']
    """
    # Import will fail until security_auditor.py is created
    from agents.security_auditor import audit_diff

    # Set up mock state
    state: dict = {
        "pr_number": 123,
        "repo_url": "https://github.com/example/repo",
        "diff": "@@ -1,3 +1,4 @@\ndef add(a, b):\n    return a + b\n-    pass\n+    pass\n",
        "files": ["src/math.py"],
        "findings": [],
        "current_agent": "security_auditor",
        "metadata": {},
    }

    # Mock the LLM call - the auditor should return structured findings
    with patch("agents.security_auditor.get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = "[{\"severity\": \"high\", \"title\": \"Hardcoded API Key\", \"description\": \"Found hardcoded API key in code\", \"file\": \"src/math.py\", \"line\": 4}]"
        mock_get_llm.return_value = mock_llm

        # Call the auditor node
        result = audit_diff(state)

        # Should return state with findings appended
        assert "findings" in result
        assert len(result["findings"]) > 0
        # The findings should be Finding objects
        from agents.base import Finding
        assert isinstance(result["findings"][0], Finding)
        assert result["findings"][0].title == "Hardcoded API Key"
        assert result["findings"][0].severity == "high"