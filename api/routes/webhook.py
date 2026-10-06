"""Jenkins webhook receiver for CodeSentinel.

Accepts Jenkins webhook payloads, validates request structure,
verifies the Jenkins signature using the X-Jenkins-Signature
header and the JENKINS_TOKEN from configuration,
fetches SonarQube context for existing findings, and triggers
LangGraph code review execution.
"""

import hashlib
import hmac
import json
import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request, status

from core.config import Settings
from core.sonarqube import get_issues
from agents.base import ReviewState
from graph.builder import build_graph

router = APIRouter(prefix="/webhook", tags=["jenkins-webhook"])

logger = logging.getLogger(__name__)


def verify_jenkins_signature(
    payload: bytes, signature: str, secret: str
) -> bool:
    """Verify a Jenkins webhook signature using HMAC-SHA256.

    Jenkins computes the signature as HMAC-SHA256 of the request body
    using the Jenkins token as the secret key. The X-Jenkins-Signature
    header contains the hex-encoded HMAC.

    Args:
        payload: The raw request body bytes.
        signature: The signature from the X-Jenkins-Signature header.
        secret: The Jenkins token (secret) used to compute the HMAC.

    Returns:
        True if the signature is valid, False otherwise.
    """
    mac = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    # Use compare_digest for timing-safe comparison
    return hmac.compare_digest(mac, signature)


def _derive_project_key(repo_url: str) -> str:
    """Derive a SonarQube project key from the repository URL.

    Extracts the repository name from the URL to use as the SonarQube project key.
    For example, https://github.com/user/repo becomes "repo".

    Args:
        repo_url: The repository URL from the webhook payload.

    Returns:
        A string suitable as a SonarQube project key.
    """
    # Strip protocol and path, extract the last path segment
    cleaned = repo_url.strip("/")
    parts = cleaned.split("/")
    return parts[-1] if parts else "unknown"


def _run_graph(state: ReviewState, config: dict[str, Any]) -> None:
    """Run the LangGraph code review graph asynchronously.

    This function is intended to be called via FastAPI BackgroundTasks.
    It builds and executes the LangGraph workflow for code review,
    passing the initial ReviewState and configuration.

    Args:
        state: The ReviewState dict containing PR context and findings.
        config: Execution configuration (e.g., recursion_limit).
    """
    graph = build_graph(checkpointer=None)  # MemorySaver for dev execution
    # Execute the graph — the supervisor node will route through
    # code_reviewer, security_auditor, and test_generator workers
    # until reaching END or hitting the recursion limit.
    graph.invoke(state, config={"recursion_limit": 25})


@router.post("/jenkins")
async def receive_jenkins_webhook(
    request: Request,
    x_jenkins_signature: str = Header(
        ..., description="Jenkins webhook signature header"
    ),
    background_tasks: BackgroundTasks = BackgroundTasks(),  # noqa: B008
    settings: Settings = ...,  # type: ignore[assignment]  # noqa: B008
) -> dict[str, Any]:
    """Receive and process a Jenkins webhook payload.

    Validates the request structure, verifies the Jenkins signature,
    fetches SonarQube context for existing findings,
    constructs an initial ReviewState, and schedules LangGraph
    code review execution asynchronously via BackgroundTasks.

    Returns HTTP 202 Accepted immediately to acknowledge receipt;
    the LangGraph review runs in the background.

    Args:
        request: The incoming FastAPI request object.
        x_jenkins_signature: The signature from the X-Jenkins-Signature header.
        background_tasks: FastAPI BackgroundTasks instance for async execution.
        settings: Application settings injected via dependency injection.

    Returns:
        A dictionary indicating successful receipt with standard fields.

    Raises:
        HTTPException: If the signature is missing, invalid, or
                       configuration is missing.
    """
    # Read the raw payload body
    payload = await request.body()

    # Validate that we have a signature
    if not x_jenkins_signature:
        logger.warning("Jenkins webhook received without signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Jenkins webhook signature",
        )

    # Validate configuration - jenkins_token must be set
    if not settings.jenkins_token:
        logger.error("Jenkins token not configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Jenkins webhook configuration incomplete",
        )

    # Verify the Jenkins signature
    is_valid = verify_jenkins_signature(payload, x_jenkins_signature, settings.jenkins_token)

    if not is_valid:
        logger.warning(
            "Jenkins webhook received with invalid signature",
            extra={"signature": x_jenkins_signature[:16] if len(x_jenkins_signature) > 16 else x_jenkins_signature},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Jenkins webhook signature",
        )

    # Payload validation - try to parse JSON and check required fields
    try:
        data = json.loads(payload)
    except (json.JSONDecodeError, ValueError):
        logger.warning("Jenkins webhook received with malformed JSON payload")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed JSON payload in webhook",
        )

    # Extract required fields from payload
    pr_number = data.get("pr_number")
    repo_url = data.get("repo_url")
    commit_sha = data.get("commit_sha")
    changed_files = data.get("changed_files", [])
    build_url = data.get("build_url", "")

    # Validate required fields are present
    if pr_number is None:
        logger.warning("Jenkins webhook payload missing required field: pr_number")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required field: pr_number",
        )

    if repo_url is None:
        logger.warning("Jenkins webhook payload missing required field: repo_url")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required field: repo_url",
        )

    # Log the webhook receipt (avoid logging sensitive data)
    logger.info(
        "Jenkins webhook successfully received and verified",
        extra={
            "build_url": build_url,
            "commit_sha": commit_sha[:16] if commit_sha else "unknown",
            "pr_number": pr_number,
        },
    )

    # Derive SonarQube project key from repo URL
    project_key = _derive_project_key(repo_url)

    # Fetch SonarQube context — existing findings for this PR
    try:
        sonarqube_findings = get_issues(project_key=project_key, pull_request=pr_number)
    except Exception as e:
        logger.warning(
            "SonarQube context fetch failed, proceeding without SonarQube findings",
            extra={"project_key": project_key, "pr_number": pr_number, "error": str(e)},
        )
        sonarqube_findings = []

    # Construct initial ReviewState
    review_state: ReviewState = {
        "pr_number": pr_number,
        "repo_url": repo_url,
        "diff": data.get("diff", ""),
        "files": changed_files if changed_files else [],
        "findings": sonarqube_findings,
        "current_agent": "supervisor",
        "metadata": {
            "source": "jenkins_webhook",
            "build_url": build_url,
            "commit_sha": commit_sha or "",
        },
    }

    # Schedule LangGraph graph execution asynchronously via BackgroundTasks
    # FastAPI will execute these tasks after the response is returned
    background_tasks.add_task(_run_graph, review_state, {"recursion_limit": 25})

    # Return 202 Accepted immediately
    return {
        "status": "accepted",
        "build_url": build_url,
        "commit_sha": commit_sha or "",
        "pr_number": pr_number,
    }