# Core Shared State and Configuration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the core shared state (ReviewState TypedDict in agents/base.py) and Pydantic Settings configuration (core/config.py) as defined in AGENTS.md, with TDD ensuring correctness.

**Architecture:** 
- `agents/base.py` defines the single ReviewState TypedDict used across all LangGraph agents, plus a ToolRegistry pattern for pure functions with Pydantic I/O
- `core/config.py` provides environment-driven Pydantic Settings for LLM, LangGraph, Jenkins, SonarQube, and ECS configuration
- Both modules follow the conventions from AGENTS.md and are designed for testability

**Spec:** AGENTS.md lines 53-112, 171-193

**Review Focus:**
1. ReviewState must contain all required fields: pr_number, repo_url, diff, files, findings, current_agent, metadata
2. ToolRegistry pure functions must have Pydantic-validated I/O
3. Settings must load from .env file with correct defaults and env var overrides
4. All settings fields must match AGENTS.md specification exactly

## Task 1: Write failing test for agents/base.py ReviewState

**Files:**
- Create: `tests/unit/test_base.py`
- Create: `agents/base.py`

**Status:** ✅ Completed — both tests pass (`test_review_state_has_required_fields`, `test_review_state_typedict`)

## Task 2: Write failing test for core/config.py Settings validation

**Files:**
- Create: `tests/unit/test_config.py`
- Create: `core/config.py`

**Status:** ✅ Completed — both tests pass (`test_settings_loads_from_env`, `test_settings_env_override`)

## Committed Changes

- `agents/base.py` — ReviewState TypedDict with all 7 fields (pr_number, repo_url, diff, files, findings, current_agent, metadata), Finding class, ToolRegistry pattern
- `core/config.py` — Pydantic BaseModel Settings with all fields from AGENTS.md (LLM, LangGraph, Jenkins, SonarQube, ECS), env var support via `default_factory=lambda: _env(...)` 
- `tests/unit/test_base.py` — Two tests verifying ReviewState structure and fields
- `tests/unit/test_config.py` — Two tests verifying Settings loads from env vars and respects overrides
- `pyproject.toml` — Project dependencies (FastAPI, LangGraph, LangChain, Pydantic, pytest, ruff, mypy)
- `.gitignore` — Standard Python, IDE, Docker, SonarQube, ECS, and worktree exclusions