# Master Plan: SonarQube Integration & Webhook Graph Flow

## Overview
Wire external SonarQube integration into the existing LangGraph code review workflow, starting from Jenkins webhook payloads.

## Phase 1: SonarQube Client (`core/sonarqube.py`)
**Goal**: Create a SonarQube client that fetches issues for a given project/PR and returns normalized `Finding` objects.

**Responsibilities**:
- Use the installed `sonarqube` package (requests-based API wrapper) to call SonarQube REST API
- Implement `get_issues(project_key, pull_request)` that queries `api/issues/search`
- Authenticate using `sonarqube_token` from `Settings`
- Return a list of `Finding` objects compatible with `ReviewState.findings`
- Normalize SonarQube issue fields: severity, title, description, file path, line number

**API Endpoints** (via `sonarqube` package or direct `requests`):
- `GET {sonarqube_url}/api/issues/search?component={project_key}&qualifiers=+SONAR%3Aissue` etc.

**Normalized Finding fields** (matching `agents/base.py.Finding`):
- `severity`: string (blocker, critical, major, minor, info)
- `title`: string
- `description`: string
- `file_path`: string | null
- `line_number`: int | null

---

## Phase 2: Webhook → Graph Flow (`api/routes/webhook.py`)
**Goal**: After Jenkins webhook signature validation, parse the payload, fetch SonarQube context, construct ReviewState, and schedule LangGraph graph execution asynchronously.

**Responsibilities**:
1. **Parse Jenkins Payload**: Extract `pr_number`, `repo_url`, `commit_sha`, `changed_files`, `build_url` from the JSON payload
2. **Fetch SonarQube Context**: Call `core/sonarqube.get_issues(project_key, pull_request)` to get existing findings
3. **Construct Initial ReviewState**: Populate with:
   - `pr_number`, `repo_url`, `diff` (from webhook payload or empty), `files` (changed files from payload)
   - `findings` (from SonarQube integration, pre-populated)
   - `current_agent`: "supervisor"
   - `metadata`: { "source": "jenkins_webhook", "build_url": ..., "commit_sha": ... }
4. **Schedule Graph Execution**: Use FastAPI `BackgroundTasks` to invoke the LangGraph graph asynchronously
5. **Return HTTP 202**: Immediately acknowledge receipt, process in background

**Complete Flow**:
```
Jenkins Webhook
      │
      ▼
Signature Validation (already implemented)
      │
      ▼
Parse Jenkins Payload → {pr_number, repo_url, commit_sha, changed_files, build_url}
      │
      ▼
Fetch SonarQube Context → core/sonarqube.get_issues(project_key, pull_request)
      │
      ▼
Construct Initial ReviewState (with SonarQube findings pre-loaded)
      │
      ▼
Schedule Graph Execution via BackgroundTasks (invoke LangGraph supervisor)
      │
      ▼
Return HTTP 202 Accepted
      │
      └──────────────► Background: LangGraph graph executes through supervisor → workers
```

## Dependencies
- `core/config.py` already has `sonarqube_url` and `sonarqube_token` fields
- `sonarqube` package 0.0.5 installed (requests-based SonarQube API wrapper)
- `ReviewState` in `agents/base.py` already has appropriate schema
- LangGraph graph in `graph/builder.py` already compiled with supervisor + 3 workers

## Verification
- Unit tests in `tests/unit/test_webhook.py` should pass
- Integration tests should verify webhook → SonarQube → graph flow
- SonarQube findings should be visible in the accumulated `ReviewState.findings`