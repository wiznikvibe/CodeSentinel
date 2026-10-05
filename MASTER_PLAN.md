# Master Implementation Plan

## Overview
Implement three features in parallel using subagent-driven development with isolated worktrees:
1. Security Auditor Node
2. Test Generator Node
3. Jenkins Webhook Receiver

---

## Architecture

### Existing ReviewState (agents/base.py)
```python
class ReviewState(TypedDict):
    pr_number: int
    repo_url: str
    diff: str
    files: list[str]
    findings: Annotated[list[Finding], add_messages]  # accumulated
    current_agent: str
    metadata: dict
```

All agents read/write this state. New findings are appended via `list(state.get("findings", [])) + new_findings`.

### Existing Agent Pattern (agents/code_reviewer.py)
- Node function: `review_diff(state: dict) -> dict`
- Reads state fields, formats prompt, calls LLM via injected `get_llm()`, parses JSON response into `Finding` objects
- Appends new findings: `list(state.get("findings", [])) + new_findings`
- Returns partial state dict

### Existing Configuration (core/config.py)
- `Settings` BaseModel with env var support
- LLM: `llm_provider`, `llm_model`, `llm_temperature`
- LangGraph: `checkpoint_db_url`, `redis_url`
- Jenkins: `jenkins_url`, `jenkins_user`, `jenkins_token` (SecretStr)
- SonarQube: `sonarqube_url`, `sonarqube_token` (SecretStr)
- ECS: `ecs_cluster`, `ecs_task_family`

### Prompt Template Convention
- Lives in `core/prompts/*.md`
- Referenced by agent nodes for formatting LLM prompts

### Jenkins Webhook
- Existing convention: `X-Jenkins-Signature` header for signature verification
- Endpoint: `/webhook/jenkins`
- Payload includes: `build_url`, `commit_sha`, `pr_number`, `changed_files`

---

## Feature 1 — Security Auditor Node

### Files to Create
- `agents/security_auditor.py` — LangGraph node for security analysis
- `core/prompts/security.md` — Prompt template for security scanning
- `tests/unit/test_security_auditor.py` — Unit tests

### Behavior
- Consumes `ReviewState` (diff, files, repo_url, pr_number)
- Analyzes diff for OWASP Top 10 vulnerabilities
- Checks for hardcoded secrets, API keys, tokens
- Identifies injection vulnerabilities (SQLi, XSS, command injection)
- Verifies authentication and authorization checks
- Appends structured `Finding` objects to `state["findings"]`
- Does not overwrite existing findings
- Handles empty/malformed state gracefully

### Prompt Template (core/prompts/security.md)
- Follows conventions of `code_reviewer.md` and `security_auditor.md`
- Input variables: `diff`, `files`, `repo_url`, `pr_number`
- Output: structured findings JSON list

---

## Feature 2 — Test Generator Node

### Files to Create
- `agents/test_generator.py` — LangGraph node for test generation
- `core/prompts/test_generator.md` — Prompt template for test suggestions
- `tests/unit/test_test_generator.py` — Unit tests

### Behavior
- Consumes `ReviewState` (diff, files, findings, pr_number)
- Generates suggested tests based on existing review information
- Focuses on tests that would catch previously identified issues
- Also suggests new test cases for uncovered logic
- Appends test suggestions to appropriate state field
- Preserves existing state information
- Handles empty/incomplete state safely

### Prompt Template (core/prompts/test_generator.md)
- Input variables from ReviewState
- Output: suggested test cases

---

## Feature 3 — Jenkins Webhook Receiver

### Files to Create
- `api/routes/webhook.py` — FastAPI route for Jenkins webhook
- Tests for the webhook handler

### Behavior
- Accepts POST requests at `/webhook/jenkins`
- Validates request structure (expected payload fields)
- Verifies Jenkins signature using `X-Jenkins-Signature` header and `JENKINS_TOKEN` from config
- Rejects missing/invalid signatures with appropriate HTTP errors
- Prevents unauthenticated webhook processing
- Processes webhook asynchronously
- Follows existing HTTP framework conventions

### Configuration
- Uses existing `Settings` from `core/config.py`
- `JENKINS_TOKEN` for signature verification
- No new configuration mechanisms needed

---

## Worktree Strategy

Three isolated worktrees/branches:
1. `feature/security-auditor` — Security Auditor implementation
2. `feature/test-generator` — Test Generator implementation
3. `feature/jenkins-webhook` — Jenkins Webhook implementation

Each subagent works only in its assigned worktree.

---

## TDD Workflow (per feature)
1. **RED**: Write test first, verify it fails
2. **GREEN**: Implement minimal code to pass test
3. **REFACTOR**: Clean up, align with conventions
4. **VALIDATION**: Run test suite, check integration