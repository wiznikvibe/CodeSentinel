# AGENTS.md — Multi-Agent Code Review / QA Automation

**Stack**: FastAPI · LangChain · LangGraph · Jenkins · SonarQube · AWS ECS
**Agent Framework**: OpenCode + Superpowers (obra)

---

## Superpowers Workflow Directives (CRITICAL)

This repository strictly follows the **Superpowers** development methodology. The OpenCode agent must utilize its installed Superpowers skills for all tasks:

1. **Brainstorming & Design First**: Never write code immediately. Use the `brainstorming` skill to ask clarifying questions, explore architecture alternatives, and save a design document before proceeding.
2. **Git Worktrees**: Use the `using-git-worktrees` skill. All new features or bug fixes must be implemented in a clean, isolated git worktree branch. 
3. **Write Plans**: Use the `writing-plans` skill to break approved designs into bite-sized tasks (2-5 minutes each) with exact file paths and verification steps.
4. **Test-Driven Development (TDD)**: The `test-driven-development` skill is mandatory here. Enforce **RED-GREEN-REFACTOR**:
   - Write a failing `pytest` test first.
   - Watch it fail.
   - Write the minimal code in `api/` or `agents/` to pass it.
   - Refactor.
5. **Subagent Execution**: For executing plans, rely on the `subagent-driven-development` skill. Dispatch subagents for specific tasks and enforce the two-stage review (spec compliance, then code quality).
6. **Systematic Debugging**: If LangGraph state loops, Jenkins webhooks fail, or SonarQube gates fail, you must invoke the `systematic-debugging` skill (4-phase root-cause tracing) instead of guessing.
7. **Verification**: Always use `verification-before-completion` and `requesting-code-review` before finishing a branch.

---

## Project Structure (enforced)

```text
.
├── agents/                 # LangGraph agent definitions
│   ├── base.py            # BaseAgent, shared state, tool registry
│   ├── code_reviewer.py   # Reviews diffs, suggests fixes
│   ├── security_auditor.py# OWASP, secrets, injection checks
│   └── supervisor.py      # Routes tasks, aggregates results
├── api/                    # FastAPI service layer
│   ├── main.py            # App factory, lifespan, middleware
│   └── deps.py            # DI: LLM client, vector store, settings
├── core/                   # Shared business logic
│   ├── config.py          # Pydantic Settings (env-driven)
│   └── prompts/           # Versioned prompt templates (.md)
├── jenkins/                # Jenkins integration (client.py, webhook.py)
├── graph/                  # LangGraph compilation & checkpointers
├── tests/                  # Pytest (Crucial for Superpowers TDD)
│   ├── unit/              # Pure logic, mocked externals
│   ├── integration/       # Real API calls
│   └── fixtures/          # Sample diffs, payloads, expected outputs
└── infra/                  # IaC & deployment (ECS, Jenkins, SonarQube)

---

## Key Conventions

### 1. LangGraph Agent Pattern
- **State**: Single `ReviewState` TypedDict in `agents/base.py` — all agents read/write this
- **Tools**: Registered in `base.ToolRegistry` — each tool is a pure function with Pydantic I/O
- **Supervisor**: Uses `Command` for dynamic routing; never hardcodes agent sequence
- **Checkpointing**: PostgresSaver (prod) / MemorySaver (dev) — see `graph/checkpointer.py`

```python
# agents/base.py — canonical pattern
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, add_messages

class ReviewState(TypedDict):
    pr_number: int
    repo_url: str
    diff: str
    files: list[str]
    findings: Annotated[list[Finding], add_messages]  # accumulated
    current_agent: str
    metadata: dict

# Tool signature — always pure, validated
async def analyze_complexity(file: str, diff: str) -> ComplexityReport: ...
```

### 2. FastAPI Service Rules
- **App factory** in `api/main.py:create_app()` — enables test overrides
- **Dependencies** in `api/deps.py` — single source for `get_llm()`, `get_settings()`, `get_db()`
- **Routes** thin — delegate to `core/` services or graph invocation
- **Webhooks** verify signatures (Jenkins: `X-Jenkins-Signature`; GitHub: `X-Hub-Signature-256`)

### 3. Configuration (Pydantic Settings)
```python
# core/config.py
class Settings(BaseSettings):
    # LLM
    llm_provider: Literal["openai", "anthropic", "local"] = "openai"
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.1
    
    # LangGraph
    checkpoint_db_url: str  # postgresql://...
    redis_url: str | None = None
    
    # Jenkins
    jenkins_url: str
    jenkins_user: str
    jenkins_token: SecretStr
    
    # SonarQube
    sonarqube_url: str
    sonarqube_token: SecretStr
    
    # ECS
    ecs_cluster: str
    ecs_task_family: str
    
    class Config:
        env_file = ".env"
        extra = "ignore"
```

### 4. Jenkins Integration
- **Jenkinsfile** in `infra/jenkins/` — declarative pipeline calling `/webhook/jenkins` on completion
- **Shared library** for reusable steps: `checkout`, `sonarqube_scan`, `trigger_review_agent`
- **Webhook payload** includes: `build_url`, `commit_sha`, `pr_number`, `changed_files`

### 5. SonarQube Integration
- **Quality Gate** in `infra/sonarqube/quality-gate.json` — fail on: new bugs, vulnerabilities, code smells, coverage < 80%
- **Client** in `core/sonarqube.py` — `get_issues(project_key, pull_request)` returns normalized findings
- **Agent consumes** SonarQube issues as context for `code_reviewer` and `security_auditor`

### 6. ECS Deployment (Fargate recommended)
- **Task Definition**: 2 containers — `api` (FastAPI, 1 vCPU/2GB) + `worker` (LangGraph, 2 vCPU/4GB)
- **Service**: ALB target group → `/health` & `/ready`; autoscaling on CPU > 70% / SQS queue depth
- **Secrets**: AWS Secrets Manager → injected as env vars (no `.env` in containers)
- **Observability**: CloudWatch Logs + X-Ray tracing (enable in `api/main.py`)

---

## Developer Commands

| Action | Command |
|--------|---------|
| Install deps | `uv sync` (or `poetry install`) |
| Run API locally | `uv run uvicorn api.main:app --reload` |
| Run graph dev UI | `uv run langgraph dev --config graph/builder.py` |
| Run tests | `uv run pytest tests/unit -x` |
| Run integration tests | `uv run pytest tests/integration -x -m integration` |
| Lint + typecheck | `uv run ruff check . && uv run mypy .` |
| Format | `uv run ruff format .` |
| Build Docker | `docker build -t code-review-agent .` |
| Local stack | `./scripts/dev.sh up` (API + Postgres + Redis + LocalStack) |
| Deploy to ECS | `./scripts/deploy.sh <env>` (uses `infra/ecs/`) |

---

## Testing Strategy

- **Unit**: Mock `LLM`, `SonarQubeClient`, `JenkinsClient` — test agent logic, tool outputs, state transitions
- **Integration**: Real API calls — require `SONARQUBE_URL`, `JENKINS_URL` in env; marked `@pytest.mark.integration`
- **Graph tests**: Use `graph/builder.py:build_graph(checkpointer=MemorySaver())` — assert stream events, final state
- **Fixtures**: `tests/fixtures/` — sample PR diffs, Jenkins payloads, SonarQube responses

---

## Common Pitfalls

| Issue | Prevention |
|-------|------------|
| LLM output parsing fails | Use `PydanticOutputParser` + `RunnableWithFallbacks` in every tool |
| Graph infinite loops | Set `recursion_limit=25` in `graph/builder.py`; log `current_agent` each step |
| Jenkins webhook timeout | Respond `202 Accepted` immediately; process async via Redis queue |
| SonarQube rate limits | Cache project issues for 5 min; batch requests |
| ECS task OOM | Set `memory` + `memoryReservation` in task def; monitor `ContainerInsights` |
| Prompt drift | Version prompts in `core/prompts/`; test against golden fixtures |

---

## Environment Variables (required)

```bash
# .env (never commit)
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

CHECKPOINT_DB_URL=postgresql://user:pass@localhost:5432/agent_checkpoints
REDIS_URL=redis://localhost:6379/0

JENKINS_URL=https://jenkins.example.com
JENKINS_USER=agent-bot
JENKINS_TOKEN=***

SONARQUBE_URL=https://sonar.example.com
SONARQUBE_TOKEN=***

ECS_CLUSTER=code-review-cluster
ECS_TASK_FAMILY=code-review-agent
AWS_REGION=us-east-1
```

---

## References

- **LangGraph patterns**: `graph/builder.py`, `agents/supervisor.py`
- **Prompt templates**: `core/prompts/*.md` — edit these, not inline strings
- **Jenkins shared lib**: `infra/jenkins/vars/` — global pipeline functions
- **ECS task def**: `infra/ecs/task-def.json` — source of truth for container specs