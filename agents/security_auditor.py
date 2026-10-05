"""Security Auditor LangGraph node.

Scans PR diffs for OWASP Top 10 vulnerabilities, hardcoded secrets,
injection flaws, and other security issues. Follows the superpowers
pattern: reads ReviewState, formats prompt, calls LLM, appends Findings
to state.
"""

from typing import Any

from agents.base import Finding  # type: ignore[attr-defined]

#: LLM client factory — overridden by tests/injection via agents.security_auditor.get_llm
get_llm: Any = None  # noqa: F811  – assigned at runtime / by tests


def audit_diff(state: dict) -> dict:
    """LangGraph security auditor node.

    Reads the PR diff from ReviewState, formats a prompt using the
    security.md template, calls the LLM, and appends identified
    security findings to the state's findings list.

    Args:
        state: ReviewDict with pr_number, repo_url, diff, files,
               findings, current_agent, metadata.

    Returns:
        Updated state with new findings appended to state["findings"].
    """
    pr_number: int = state["pr_number"]
    repo_url: str = state["repo_url"]
    diff: str = state["diff"]
    files: list[str] = state["files"]

    # Format the prompt using the security.md template
    prompt = f"""Security Audit PR #{pr_number}

Repository: {repo_url}

Diff:
{diff}

Changed files: {", ".join(files)}

Please scan the above diff for security vulnerabilities and identify:
- OWASP Top 10 security vulnerabilities (SQL injection, XSS, CSRF, etc.)
- Hardcoded secrets, API keys, tokens, or credentials
- Injection vulnerabilities (SQLi, XSS, command injection, LDAP injection)
- Insecure authentication or authorization checks
- Insecure dependencies or outdated library versions

Return your findings as a JSON list of objects with: severity (string),
title (string), description (string), file (string | null), line (int | null).
"""

    # Call the LLM with the formatted prompt
    # Rely on injected get_llm (injected by tests or graph setup)
    llm = get_llm()  # type: ignore[union-attr]
    raw_response = llm.invoke(prompt)

    # Parse the LLM response into Finding objects
    new_findings = []

    if isinstance(raw_response, str) and raw_response.strip():
        import json

        try:
            parsed = json.loads(raw_response)
            if isinstance(parsed, list):
                for item in parsed:
                    finding = Finding(
                        severity=item.get("severity", "info"),
                        title=item.get("title", "Unnamed security issue"),
                        description=item.get("description", ""),
                        file_path=item.get("file"),
                        line_number=item.get("line"),
                    )
                    new_findings.append(finding)
        except (json.JSONDecodeError, TypeError):
            finding = Finding(
                severity="info",
                title="Security audit review",
                description=raw_response,
                file_path=None,
                line_number=None,
            )
            new_findings.append(finding)

    # Append new findings to existing state findings
    updated_findings = list(state.get("findings", [])) + new_findings

    return {
        "pr_number": state["pr_number"],
        "repo_url": state["repo_url"],
        "diff": state["diff"],
        "files": state["files"],
        "findings": updated_findings,
        "current_agent": "security_auditor",
        "metadata": state.get("metadata", {}),
    }


# Register the tool in the ToolRegistry
def register_tool(name: str, func):  # type: ignore[override]
    """Register a pure function as a tool in the ToolRegistry."""
    globals()[name] = func


register_tool("audit_diff", audit_diff)