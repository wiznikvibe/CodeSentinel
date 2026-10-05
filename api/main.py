"""FastAPI application factory for CodeSentinel.

Enables test overrides and proper dependency injection setup.
"""

from fastapi import FastAPI

from api.routes import webhook
from api.deps import get_settings, get_llm, get_db


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance.
    """
    app = FastAPI(
        title="CodeSentinel - Multi-Agent Code Review",
        description="Automated code review and security auditing for PRs",
        version="0.1.0",
    )

    # Include routes
    app.include_router(webhook.router)

    # Add middleware and other configuration here
    # (CORS, logging, etc.)

    @app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/ready")
async def ready_check() -> dict[str, str]:
    """Readiness check endpoint."""
    return {"status": "ready"}


# Dependency overrides for testing
# These allow tests to inject mock dependencies
def get_settings_override() -> Settings:
    """Override for get_settings dependency."""
    from core.config import Settings

    return Settings()


def get_llm_override() -> Any:
    """Override for get_llm dependency."""
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


def get_db_override() -> Any:
    """Override for get_db dependency."""
    return None