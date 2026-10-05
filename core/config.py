"""Pydantic Settings — environment-driven configuration for the CodeSentinel agent.

All configuration is driven by environment variables via a .env file.
This matches the specification in AGENTS.md (core/config.py section).

The Settings class uses Pydantic BaseModel with env var support.
Environment variables are automatically read via Field(default_factory=...) 
when the .env file is present or vars are set in the environment.

.env format (example - never commit this file):
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
    ECS_CLUSTER=code-review-agent
    AWS_REGION=us-east-1
"""

from __future__ import annotations

import os
from typing import Literal, Optional

from pydantic import BaseModel, Field, SecretStr


def _env(key: str, default: str | None = None) -> str:
    """Read environment variable with fallback to default."""
    return os.environ.get(key, default)


class Settings(BaseModel):
    """Pydantic Settings matching AGENTS.md specification.

    Environment variables are automatically read from os.environ.
    Set required vars in .env or the runtime environment before instantiating.

    Key fields per AGENTS.md:
    - LLM: llm_provider (default: openai), llm_model (default: gpt-4o-mini),
      llm_temperature (default: 0.1)
    - LangGraph: checkpoint_db_url (required, no default), redis_url (default: None)
    - Jenkins: jenkins_url (required), jenkins_user (default: "agent-bot"),
      jenkins_token (required)
    - SonarQube: sonarqube_url (required), sonarqube_token (required)
    - ECS: ecs_cluster (required), ecs_task_family (default: "code-review-agent")
    """

    # LLM configuration — read from env if set, otherwise use defaults
    llm_provider: Literal["openai", "anthropic", "local"] = Field(
        default_factory=lambda: _env("LLM_PROVIDER", "openai"),
        description="LLM provider (openai, anthropic, local)",
    )
    llm_model: str = Field(
        default_factory=lambda: _env("LLM_MODEL", "gpt-4o-mini"),
        description="LLM model name (e.g. gpt-4o-mini, gpt-4o)",
    )
    llm_temperature: float = Field(
        default_factory=lambda: float(_env("LLM_TEMPERATURE", "0.1")),
        ge=0.0,
        le=2.0,
        description="Sampling temperature for LLM calls (0.0-2.0)",
    )

    # LangGraph checkpointing
    # checkpoint_db_url is required — no default, must be set via env
    checkpoint_db_url: str = Field(
        default_factory=lambda: _env("CHECKPOINT_DB_URL"),
        description="PostgreSQL connection string for LangGraph checkpointer",
    )
    redis_url: Optional[str] = Field(
        default_factory=lambda: _env("REDIS_URL", None),
        description="Redis URL for caching/queues (optional)",
    )

    # Jenkins integration
    jenkins_url: str = Field(
        default_factory=lambda: _env("JENKINS_URL"),
        description="Jenkins server URL",
    )
    jenkins_user: str = Field(
        default_factory=lambda: _env("JENKINS_USER", "agent-bot"),
        description="Jenkins username",
    )
    jenkins_token: SecretStr = Field(
        default_factory=lambda: _env("JENKINS_TOKEN"),
        description="Jenkins authentication token",
    )

    # SonarQube integration
    sonarqube_url: str = Field(
        default_factory=lambda: _env("SONARQUBE_URL"),
        description="SonarQube server URL",
    )
    sonarqube_token: SecretStr = Field(
        default_factory=lambda: _env("SONARQUBE_TOKEN"),
        description="SonarQube authentication token",
    )

    # ECS deployment
    ecs_cluster: str = Field(
        default_factory=lambda: _env("ECS_CLUSTER"),
        description="ECS cluster name",
    )
    ecs_task_family: str = Field(
        default_factory=lambda: _env("ECS_TASK_FAMILY", "code-review-agent"),
        description="ECS task family name",
    )