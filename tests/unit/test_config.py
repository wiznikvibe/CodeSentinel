"""Unit tests for core/config.py - Pydantic Settings configuration."""

import os
import pytest


def test_settings_loads_from_env():
    """Settings must load with correct defaults and env var overrides.

    Required fields (checkpoint_db_url, jenkins_url, jenkins_token,
    sonarqube_url, sonarqube_token, ecs_cluster) must be provided
    via environment variables per AGENTS.md specification.
    """
    from core.config import Settings

    # Set required environment variables
    os.environ["CHECKPOINT_DB_URL"] = "postgresql://user:pass@localhost:5432/agent_checkpoints"
    os.environ["JENKINS_URL"] = "https://jenkins.example.com"
    os.environ["JENKINS_TOKEN"] = "***"
    os.environ["SONARQUBE_URL"] = "https://sonar.example.com"
    os.environ["SONARQUBE_TOKEN"] = "***"
    os.environ["ECS_CLUSTER"] = "code-review-cluster"

    try:
        settings = Settings()
        # LLM defaults
        assert settings.llm_provider == "openai"
        assert settings.llm_model == "gpt-4o-mini"
        assert settings.llm_temperature == 0.1
        # LangGraph defaults
        assert settings.checkpoint_db_url is not None  # required field from env
        assert settings.redis_url is None  # optional field, defaults to None
        # Jenkins defaults
        assert settings.jenkins_url is not None  # required field from env
        assert settings.jenkins_user == "agent-bot"
        # SonarQube defaults
        assert settings.sonarqube_url is not None  # required field from env
        # ECS defaults
        assert settings.ecs_cluster is not None  # required field from env
        assert settings.ecs_task_family == "code-review-agent"
    finally:
        # Clean up env vars
        del os.environ["CHECKPOINT_DB_URL"]
        del os.environ["JENKINS_URL"]
        del os.environ["JENKINS_TOKEN"]
        del os.environ["SONARQUBE_URL"]
        del os.environ["SONARQUBE_TOKEN"]
        del os.environ["ECS_CLUSTER"]


def test_settings_env_override():
    """Settings must respect env var overrides."""
    from core.config import Settings

    os.environ["LLM_MODEL"] = "gpt-4o"
    try:
        settings = Settings()
        assert settings.llm_model == "gpt-4o"
    finally:
        # Clean up env vars
        del os.environ["LLM_MODEL"]