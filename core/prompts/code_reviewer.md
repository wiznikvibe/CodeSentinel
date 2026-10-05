# Code Reviewer Prompt Template

## Purpose
Prompt for the LangGraph code reviewer agent that analyzes PR diffs and identifies issues, bugs, and improvements.

## Format
Follow the structured format in `agents/base.py` using `ReviewState`.

## Core Directives
1. **Analyze the diff** provided in the state
2. **Identify** new bugs, vulnerabilities, code smells (SonarQube integration)
3. **Check** for OWASP Top 10 issues (security_auditor integration)
4. **Flag** style inconsistencies and best practice violations
5. **Prioritize** findings by severity and impact

## Input Variables
- `pr_number`: int — Pull request number
- `repo_url`: str — Repository URL
- `diff`: str — The full diff to review
- `files`: list[str] — List of changed files

## Output Expectations
- `findings`: List[Finding] — Accumulated findings annotated with add_messages
- Current agent tracking: `current_agent: str`
- Metadata: `metadata: dict`

## Versioning
Version this prompt template when updating review logic or criteria.
Store version in prompt metadata or as a comment at the top of the file.