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
28 passed in 0.37s
  tests/unit/test_base.py::test_review_state_has_required_fields PASSED
  tests/unit/test_base.py::test_review_state_typedict PASSED
  tests/unit/test_code_reviewer.py::test_code_reviewer_appends_findings PASSED
  tests/unit/test_config.py::test_settings_loads_from_env PASSED
  tests/unit/test_config.py::test_settings_env_override PASSED
  tests/unit/test_security_auditor.py::test_security_auditor_appends_findings PASSED
  tests/unit/test_supervisor.py::test_supervisor_routes_to_code_reviewer_first PASSED
  tests/unit/test_supervisor.py::test_supervisor_routes_to_security_auditor_after_code_reviewer PASSED
  tests/unit/test_supervisor.py::test_supervisor_terminates_after_all_workers PASSED
  tests/unit/test_supervisor.py::test_supervisor_routes_to_test_generator PASSED
  tests/unit/test_supervisor.py::test_supervisor_avoids_repeated_dispatch PASSED
  tests/unit/test_supervisor.py::test_supervisor_handles_invalid_llm_output PASSED
  tests/unit/test_builder.py::test_build_graph_has_correct_nodes PASSED
  tests/unit/test_builder.py::test_build_graph_entry_point_is_supervisor PASSED
  tests/unit/test_builder.py::test_build_graph_has_worker_nodes PASSED
  tests/unit/test_builder.py::test_build_graph_has_return_to_supervisor_edges PASSED
  tests/unit/test_builder.py::test_build_graph_with_memory_saver PASSED
  tests/unit/test_builder.py::test_graph_supervisor_routes_to_security_auditor PASSED
  tests/unit/test_builder.py::test_graph_dynamic_routing PASSED
  tests/unit/test_builder.py::test_graph_loop_protection PASSED
  tests/unit/test_builder.py::test_checkpointer_memory_saver_instantiation PASSED
  tests/unit/test_builder.py::test_checkpointer_graph_compiles_with_checkpointer PASSED
  tests/unit/test_builder.py::test_checkpointer_state_persistence_same_thread PASSED
  tests/unit/test_builder.py::test_checkpointer_different_threads_isolate_state PASSED
  tests/unit/test_test_generator.py::test_test_generator_appends_suggestions PASSED
  tests/unit/test_webhook.py::test_verify_jenkins_signature_valid PASSED
  tests/unit/test_webhook.py::test_verify_jenkins_signature_invalid PASSED
  tests/unit/test_webhook.py::test_verify_jenkins_signature_wrong_secret PASSED
```

### Next Development Phases (planned)

| Phase | planned deliverables |
|-------|---------------------|
| **Security Auditor node** | `agents/security_auditor.py` — LangGraph node mirroring code_reviewer pattern, integrating SonarQube/OSSWAP checks |
| **Supervisor node** | `agents/supervisor.py` — LangGraph router that aggregates findings from code_reviewer + security_auditor + test_generator |
| **Jenkins integration** | `jenkins/client.py`, `jenkins/webhook.py` — Shared library steps: `checkout`, `sonarqube_scan`, `trigger_review_agent` |
| **API layer** | `api/main.py` — App factory, `/webhook/jenkins` endpoint, `/health` & `/ready` endpoints |
| **Graph compilation** | `graph/builder.py` — LangGraph compilation with MemorySaver/PostgresSaver checkpointers |
| **Integration tests** | `tests/integration/` — Real API calls requiring SONARQUBE_URL, JENKINS_URL env vars |
| **Orchestration layer** | `orchestration-layer` branch merged — supervisor routing, graph builder, checkpointing, 28 unit tests |

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