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

## Output Expectations
- Security findings annotated into `findings` list
- Special focus on: secret detection, injection flaws, authz issues
- Return structured findings with severity levels

## Integration Notes
- Consumes SonarQube issues from `core/sonarqube.py`
- Works alongside `code_reviewer` findings
- Output format consistent with `Finding` type in `agents/base.py`