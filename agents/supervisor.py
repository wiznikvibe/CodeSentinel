"""Supervisor LangGraph node.

Responsible for deciding which worker should execute next based on ReviewState.
Follows the superpowers pattern: reads ReviewState, formats prompt, calls LLM,
returns Command for dynamic routing.

Do not hardcode agent sequence — use the LLM to determine the next step from
an explicit constrained set of allowed destinations.
"""

from typing import Any

from langgraph.types import Command

#: LLM client factory — overridden by tests/injection via agents.supervisor.get_llm
get_llm: Any = None  # noqa: F811  – assigned at runtime / by tests


#: Allowed routing destinations for the supervisor.
#: The LLM must output one of these strings; any other value defaults to END.
ALLOWED_DESTINATIONS = {"code_reviewer", "security_auditor", "test_generator", "END"}


def supervisor_node(state: dict) -> Command:
    """LangGraph supervisor node.

    Evaluates the current ReviewState and decides which worker should execute
    next. Uses the LLM to determine the routing decision from an explicit set
    of allowed destinations.

    Args:
        state: ReviewDict with pr_number, repo_url, diff, files,
               findings, current_agent, metadata.

    Returns:
        Command compatible with langgraph.types.Command. The `goto` field
        will be one of: "code_reviewer", "security_auditor", "test_generator",
        or "END" (termination).
    """
    pr_number: int = state["pr_number"]
    repo_url: str = state["repo_url"]
    diff: str = state["diff"]
    files: list[str] = state["files"]
    findings: list = state.get("findings", [])
    current_agent: str = state.get("current_agent", "")
    metadata: dict = state.get("metadata", {})

    # Determine which workers have already completed
    completed: list[str] = metadata.get("completed", [])
    # Ensure completed is a list
    if not isinstance(completed, list):
        completed = []

    # Build a summary of completed work to help the LLM decide
    completed_summary = ""
    if completed:
        completed_summary = f"\nCompleted agents: {', '.join(completed)}"

    # Format the prompt using the supervisor prompt template
    prompt = f"""Supervisor PR #{pr_number}

Repository: {repo_url}

Diff:
{diff}

Changed files: {", ".join(files)}{completed_summary}

Please determine the next step for the code review workflow. Based on the
current state, decide which agent should run next, or if the workflow is
complete.

Available agents:
- code_reviewer: Reviews the PR diff for bugs, code smells, and style issues
- security_auditor: Scans the diff for OWASP Top 10 vulnerabilities and secrets
- test_generator: Suggests test cases based on the diff and existing findings
- END: Terminate the workflow — all required reviews are complete

Return ONLY the name of the next agent (code_reviewer, security_auditor, or test_generator)
or "END" to terminate. Do not return any reasoning, explanation, or extra text.
"""

    # Call the LLM with the formatted prompt
    # Rely on injected get_llm (injected by tests or graph setup)
    llm = get_llm()  # type: ignore[union-attr]
    raw_response = llm.invoke(prompt)

    # Parse the LLM response - must be one of the allowed destinations
    next_agent = raw_response.strip() if isinstance(raw_response, str) else ""

    # Validate the LLM output against the allowed set
    if next_agent not in ALLOWED_DESTINATIONS:
        # Invalid or unexpected output — default to END (terminate)
        next_agent = "END"

    # Prevent repeated dispatch of the same worker consecutively.
    # If the last agent to run was the same as the proposed next agent,
    # skip it and terminate to avoid infinite loops.
    if next_agent != "END" and next_agent == current_agent:
        next_agent = "END"

    # Return a Command routing to the determined next agent
    return Command(goto=next_agent)