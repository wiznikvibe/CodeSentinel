"""Dependency injection for the FastAPI service.

Single source for LLM client, settings, and database dependency.
"""

from typing import Generator

from fastapi import Depends, Request
from pydantic import BaseModel

from core.config import Settings


def get_settings() -> Settings:
    """Get application settings.

    Returns:
        Settings instance loaded from environment variables.
    """
    return Settings()


def get_llm() -> Any:
    """Get LLM client instance.

    Note: In production, this would return a real LLM client (OpenAI, Anthropic, etc.).
    For testing, this is overridden via injection.

    Returns:
        LLM client instance.
    """
    import os

    provider = os.environ.get("LLM_PROVIDER", "openai")
    model = os.environ.get("LLM_MODEL", "gpt-4o-mini")

    if provider == "openai":
        from openai import OpenAI

        return OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    elif provider == "anthropic":
        from anthropic import Anthropic

        return Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    else:
        return None


def get_db() -> Generator[Any, None, None]:
    """Get database session dependency.

    Note: In production, this would yield a real database session.
    For testing, this is mocked or overridden.

    Yields:
        Database session object.
    """
    # Placeholder - in production would yield a real DB session
    yield None  # type: ignore[return-value]