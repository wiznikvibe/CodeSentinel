# CodeSentinel — Multi-Agent Code Review / QA Automation

![Status](https://img.shields.io/badge/status-active-brightgreen.svg)

## Overview

**CodeSentinel** is a multi-agent code review and QA automation platform built on the **Superpowers** development methodology with **OpenCode** + **Superpowers** (obra). It implements a LangGraph-based workflow for automated PR code reviews, security audits, and quality gate enforcement.

The stack includes: **FastAPI** · **LangChain** · **LangGraph** · **Jenkins** · **SonarQube** · **AWS ECS**.

## Development Progression

This project follows the **Superpowers** workflow with mandatory TDD, brainstorming-first design, and git worktree isolation.

### Current State — `main` branch

| Feature | Status | Commit |
|---------|--------|--------|
| **Project scaffolding** | ✅ Complete | `188bedf` |
| **Core shared state** | ✅ Complete | `a652a44` |
| **Pydantic Settings (core/config.py)** | ✅ Complete | `a652a44` |
| **Agents/base.py** — ReviewState + Finding + ToolRegistry | ✅ Complete | `a652a44` |
| **pyproject.toml** — Dependencies (FastAPI, LangGraph, LangChain, Pydantic, pytest, ruff, mypy) | ✅ Complete | `bc5e507` |
| ** .gitignore** — Python, IDE, Docker, SonarQube, ECS, worktrees | ✅ Complete | `aa601e6` |
| **Code reviewer LangGraph node** | ✅ Complete | `9b7845d` |
| **tests/unit/test_code_reviewer.py** — Mocked LLM test | ✅ Complete | `9b7845d` |
| **tests/unit/test_base.py** — ReviewState field validation | ✅ Complete | `a652a44` |
| **tests/unit/test_config.py** — Settings env var loading + overrides | ✅ Complete | `a652a44` |

### Test Results (fresh verification)

```
5 passed in 0.02s
  tests/unit/test_base.py::test_review_state_has_required_fields PASSED
  tests/unit/test_base.py::test_review_state_typedict PASSED
  tests/unit/test_code_reviewer.py::test_code_reviewer_appends_findings PASSED
  tests/unit/test_config.py::test_settings_loads_from_env PASSED
  tests/unit/test_config.py::test_settings_env_override PASSED
```

### Next Development Phases (planned)

| Phase | planned deliverables |
|-------|---------------------|
| **Security Auditor node** | `agents/security_auditor.py` — LangGraph node mirroring code_reviewer pattern, integrating SonarQube/OSSWAP checks |
| **Supervisor node** | `agents/supervisor.py` — LangGraph router that aggregates findings from code_reviewer + security_auditor |
| **Jenkins integration** | `jenkins/client.py`, `jenkins/webhook.py` — Shared library steps: `checkout`, `sonarqube_scan`, `trigger_review_agent` |
| **API layer** | `api/main.py` — App factory, `/webhook/jenkins` endpoint, `/health` & `/ready` endpoints |
| **Graph compilation** | `graph/builder.py` — LangGraph compilation with MemorySaver/PostgresSaver checkpointers |
| **Integration tests** | `tests/integration/` — Real API calls requiring SONARQUBE_URL, JENKINS_URL env vars |

## Project Structure (enforced)

```
.
├── agents/                 # LangGraph agent definitions
│   ├── base.py            # BaseAgent, shared state, tool registry
│   ├── code_reviewer.py   # Reviews diffs, identifies bugs/vulnerabilities
│   ├── security_auditor.py  # OWASP Top 10, secret detection
│   └── supervisor.py      # Routes tasks, aggregates results
├── api/                    # FastAPI service layer
│   ├── main.py            # App factory, lifespan, middleware
│   └── deps.py            # DI: LLM client, vector store, settings
├── core/                   # Shared business logic
│   ├── config.py          # Pydantic Settings (env-driven)
│   └── prompts/           # Versioned prompt templates (.md)
├── jenkins/                # Jenkins integration (client.py, webhook.py)
├── graph/                  # LangGraph compilation & checkpointers
├── tests/                  # Pytest