# Security Auditor Prompt Template

## Purpose
Prompt for the LangGraph security auditor agent that checks for OWASP Top 10 vulnerabilities, secrets injection, and other security issues.

## Core Directives
1. **Scan the diff** for potential security vulnerabilities
2. **Check for hardcoded secrets**, API keys, tokens in the diff
3. **Identify** injection vulnerabilities (SQLi, XSS, command injection)
4. **Verify** proper authentication and authorization checks
5. **Flag** insecure dependencies and outdated library versions

## Input Variables (from ReviewState)
- `diff`: str — The diff to security-scan
- `files`: list[str] — Changed files
- `repo_url`: str — Repository URL for context
- `pr_number`: int — Pull request number

## Output Expectations
- Security findings annotated into `findings` list
- Special focus on: secret detection, injection flaws, authz issues
- Return structured findings with severity levels
- Consistent with `Finding` type in `agents/base.py`

## Integration Notes
- Consumes ReviewState fields (diff, files, repo_url, pr_number)
- Works alongside `code_reviewer` findings
- Output format consistent with `Finding` type in `agents/base.py`

## Versioning
Version this prompt template when updating security scan logic or criteria.
Store version in prompt metadata or as a comment at the top of the file.