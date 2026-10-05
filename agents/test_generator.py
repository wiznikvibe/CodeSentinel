"""Test Generator LangGraph node.

Generates suggested tests based on the review information already available
in ReviewState. Follows the superpowers pattern: reads ReviewState, formats
prompt, calls LLM, appends test suggestions to state.
"""

from typing import Any

from agents.base import Finding  # type: ignore[attr-defined]


#: LLM client factory — overridden by tests/injection via agents.test_generator.get_llm
get_llm: Any = None  # noqa: F811  – assigned at runtime / by tests


def generate_tests(state: dict) -> dict:
    """LangGraph test generator node.

    Generates suggested test cases based on the PR diff and existing
    findings from ReviewState. The goal is to identify gaps in test coverage
    and suggest tests that would catch previously identified issues.

    Args:
        state: ReviewDict with pr_number, repo_url, diff, files,
               findings, current_agent, metadata.

    Returns:
        Updated state with generated test suggestions appended to
        state["test_suggestions"].
    """
    pr_number: int = state["pr_number"]
    repo_url: str = state["repo_url"]
    diff: str = state["diff"]
    files: list[str] = state["files"]
    existing_findings: list = state.get("findings", [])

    # Format the prompt using the test_generator.md template
    # Build a summary of existing findings to help the LLM generate relevant tests
    findings_summary = ""
    if existing_findings:
        findings_summary = "\nExisting findings that tests should cover:\n"
        for finding in existing_findings:
            findings_summary += f"- {finding.title} in {finding.file_path or 'unknown'} (line {finding.line_number or 'unknown'}): {finding.description}\n"
    else:
        findings_summary = "\nNo existing findings available."

    prompt = f"""Test Suggestion PR #{pr_number}

Repository: {repo_url}

Diff:
{diff}

Changed files: {", ".join(files)}{findings_summary}

Please analyze the above diff and existing findings, then suggest test cases that would:
1. Cover new logic or functions introduced in the diff
2. Test edge cases and error conditions for the changed code
3. Address any security vulnerabilities identified in existing findings
4. Follow best practices for test coverage and readability

Return your suggestions as a JSON list of objects with: title (string),
description (string), file (string | null), line (int | null), test_type (string)
where test_type describes the kind of test (e.g., "unit", "integration", "security",
"edge_case", "regression").

Each suggestion should be a focused, actionable test case that, if implemented,
would improve test coverage for the changed code.
"""

    # Call the LLM with the formatted prompt
    # Rely on injected get_llm (injected by tests or graph setup)
    llm = get_llm()  # type: ignore[union-attr]
    raw_response = llm.invoke(prompt)

    # Parse the LLM response into test suggestion structures
    new_suggestions = []

    if isinstance(raw_response, str) and raw_response.strip():
        import json

        try:
            parsed = json.loads(raw_response)
            if isinstance(parsed, list):
                for item in parsed:
                    suggestion = {
                        "title": item.get("title", "Unnamed test"),
                        "description": item.get("description", ""),
                        "file": item.get("file"),
                        "line": item.get("line"),
                        "test_type": item.get("test_type", "unit"),
                    }
                    new_suggestions.append(suggestion)
        except (json.JSONDecodeError, TypeError):
            # Fallback: create a single suggestion from the raw response
            suggestion = {
                "title": "Test suggestion",
                "description": raw_response,
                "file": None,
                "line": None,
                "test_type": "unit",
            }
            new_suggestions.append(suggestion)

    # Append new suggestions to existing state test suggestions
    updated_suggestions = list(state.get("test_suggestions", [])) + new_suggestions

    return {
        "pr_number": state["pr_number"],
        "repo_url": state["repo_url"],
        "diff": state["diff"],
        "files": state["files"],
        "findings": state.get("findings", []),
        "test_suggestions": updated_suggestions,
        "current_agent": "test_generator",
        "metadata": state.get("metadata", {}),
    }


# Register the tool in the ToolRegistry
def register_tool(name: str, func):  # type: ignore[override]
    """Register a pure function as a tool in the ToolRegistry."""
    globals()[name] = func
    return func


register_tool("generate_tests", generate_tests)