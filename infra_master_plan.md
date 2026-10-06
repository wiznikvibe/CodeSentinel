# Infrastructure Master Plan: Docker, Local Dev, ECS Deployment

## PHASE 1 Discovery Summary

**Application Requirements:**
- Python >=3.10
- FastAPI application with create_app factory pattern
- LangGraph with PostgresSaver (prod) / MemorySaver (dev)
- Worker nodes: code_reviewer, security_auditor, test_generator
- Supervisor orchestration
- Jenkins webhook endpoint with background task execution
- SonarQube client integration
- Environment-driven configuration via core/config.py Settings
- Health endpoints: /health, /ready
- Secrets via AWS Secrets Manager (production) / env vars (local)

**Infrastructure Requirements from AGENTS.md:**
- Docker build: `docker build -t code-review-agent .`
- Local stack: `./scripts/dev.sh up` (API + Postgres + Redis + LocalStack)
- ECS deployment: `./scripts/deploy.sh <env>` (uses `infra/ecs/`)
- ECS Task Definition: 2 containers — api (1 vCPU/2GB) + worker (2 vCPU/4GB) (Fargate recommended)
- Service: ALB target group → /health & /ready; autoscaling on CPU > 70% / SQS queue depth
- Secrets: AWS Secrets Manager → injected as env vars (no .env in containers)
- Observability: CloudWatch Logs + X-Ray tracing

**Environment Variables Required:**
- LLM_PROVIDER, LLM_MODEL, LLM_TEMPERATURE
- OPENAI_API_KEY / ANTHROPIC_API_KEY
- CHECKPOINT_DB_URL (PostgreSQL)
- REDIS_URL (optional)
- JENKINS_URL, JENKINS_USER, JENKINS_TOKEN
- SONARQUBE_URL, SONARQUBE_TOKEN
- ECS_CLUSTER, ECS_TASK_FAMILY, AWS_REGION

---

## PHASE 2 Infrastructure Master Plan

### A. Container Architecture

**Base Image:**
- `python:3.13-slim` (Python 3.13 matches venv, slim reduces size vs Alpine issues)
- Why: Matches pyproject.toml requires-python >=3.10, provides system dependencies, avoids Alpine/Musl libc complications with native packages

**Multi-stage build:**
1. **Builder stage**: `python:3.13-slim` with uv for dependency installation
   - Copy pyproject.toml and uv.lock
   - Install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`
   - `uv sync --frozen` to install dependencies
   - Copy application source

2. **Runtime stage**: `python:3.13-slim`
   - Copy installed dependencies from builder
   - Copy application source
   - Create non-root user `appuser`
   - Set working directory `/app`

**Dependency caching:**
- Use `uv sync --frozen` with uv.lock
- Cache pip/uv cache layers via multi-stage build
- Copy pyproject.toml/uv.lock first for layer caching

**Application layout:**
```
/app
├── api/
├── agents/
├── core/
├── graph/
├── infra/
├── tests/
└── pyproject.toml
```

**Runtime user:**
- `appuser` (UID 1000) — non-root as per security best practices

**Entrypoint:**
- `entrypoint.sh` handles startup, database migrations/checks, then executes command

**Commands:**
- **API**: `uv run uvicorn api.main:app --host 0.0.0.0 --port 8000`
- **Worker** (if separate): `uv run python -m worker.main` (or uses same image with different command)

**Health-check strategy:**
- Docker HEALTHCHECK: `curl -f http://localhost:8000/health || exit 1`
- Interval: 30s, timeout: 10s, retries: 3, start-period: 40s

**Port configuration:**
- API: 8000 (container port), mapped to host port via compose/ECS
- No worker port (background processing)

**Environment variable injection:**
- Docker Compose: environment files or .env
- ECS: AWS Secrets Manager via task definition environment variables
- Never commit .env files

### B. Local Development Architecture

**Service topology:**
```
api (FastAPI) → port 8000
worker (same image, different command) → background tasks
postgres (PostgreSQL 15) → port 5432
redis (Redis 7) → port 6379
localstack (AWS services mock) → port 4566
```

**Docker Compose services:**
- `api`: Depends on postgres, redis
- `worker`: Depends on postgres, redis (shares code with api)
- `postgres`: PostgreSQL with health check
- `redis`: Redis with health check
- `localstack`: AWS LocalStack for Secrets Manager mock

**Volume configuration:**
- Postgres data volume for persistence
- Redis data volume optional
- LocalStack data volume

**Network configuration:**
- Single Docker network for service communication
- Services reachable via service names

### C. ECS/Fargate Deployment Architecture

**Infrastructure as Code:**
- `infra/ecs/`: ECS task definition, service, ALB, VPC, security groups
- `infra/iam/`: Task role, execution role, secrets permissions
- `infra/secrets/`: Secrets Manager definitions

**ECS Configuration:**
- **Task Family**: code-review-agent
- **Task Role**: Permissions for Secrets Manager, CloudWatch Logs, X-Ray
- **Execution Role**: Permissions for pulling images, writing logs, reading secrets
- **Task Definition**:
  - Container 1: api — 1 vCPU, 2GB memory, port 8000
  - Container 2: worker — 2 vCPU, 4GB memory (optional, can be same container)
- **Service**:
  - ALB target group health checks: /health and /ready
  - Autoscaling: CPU > 70% or SQS queue depth
  - Desired count: 2+ for HA
  - Rolling updates with health checks

**Networking:**
- ECS service in private subnets
- ALB in public subnets
- Security groups restrict inbound/outbound traffic
- VPC endpoints for Secrets Manager, ECR, CloudWatch

**Secrets management:**
- AWS Secrets Manager stores all sensitive values
- Task definition references secrets via environment variable mapping
- Never store secrets in task definition as plain text

**Observability:**
- CloudWatch Logs: stdout/stderr from containers
- X-Ray tracing: Enable via `api/main.py` configuration
- Container Insights enabled for resource monitoring

### D. Deployment Helpers

**Scripts:**
- `scripts/dev.sh`: Start local stack via docker-compose
- `scripts/deploy.sh <env>`: Deploy to ECS (dev/staging/prod)
- `scripts/health-check.sh`: Verify deployment health
- `scripts/rollback.sh`: Rollback to previous task definition

**CI/CD integration:**
- GitHub Actions for building/pushing images to ECR
- ECS rolling updates via AWS CLI or Terraform
- Automated tests before deployment
- Manual approval for production deployments

---

## Implementation Strategy

Using subagent-driven-development with isolated git worktrees:

**Workstream 1: Docker containers**
- Create Dockerfile with multi-stage build
- Create docker-compose.yml for local development
- Test builds and local stack startup
- Document Docker setup

**Workstream 2: ECS infrastructure**
- Create infra/ecs/ task definition JSON
- Create IAM roles and policies
- Define CloudFormation/Terraform for ECS service
- Document deployment process

**Workstream 3: Deployment scripts**
- Create scripts/dev.sh for local development
- Create scripts/deploy.sh for ECS deployment
- Create health check and rollback scripts
- Document usage

**Integration validation:**
- Tech Lead reviews all outputs for architectural consistency
- Validate against AGENTS.md specifications
- Run local development stack
- Validate Docker image builds
- Verify security best practices (non-root user, secrets handling)
