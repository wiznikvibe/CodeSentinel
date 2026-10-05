"""Jenkins webhook receiver for CodeSentinel.

Accepts Jenkins webhook payloads, validates request structure,
and verifies the Jenkins signature using the X-Jenkins-Signature
header and the JENKINS_TOKEN from configuration.
"""

import hashlib
import hmac
import logging
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, status

from core.config import Settings

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


@router.post("/jenkins")
async def receive_jenkins_webhook(
    request: Request,
    x_jenkins_signature: str = Header(
        ..., description="Jenkins webhook signature header"
    ),
    settings: Settings = ...  # Will be injected via dependency
) -> dict[str, Any]:
    """Receive and process a Jenkins webhook payload.

    Validates the request structure, verifies the Jenkins signature,
    and returns a 202 Accepted response to acknowledge receipt.

    Args:
        request: The incoming FastAPI request object.
        x_jenkins_signature: The signature from the X-Jenkins-Signature header.
        settings: Application settings injected via dependency injection.

    Returns:
        A dictionary indicating successful receipt.

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
        import json

        data = json.loads(payload)
    except (json.JSONDecodeError, ValueError):
        logger.warning("Jenkins webhook received with malformed JSON payload")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed JSON payload in webhook",
        )

    # Log the webhook receipt (avoid logging sensitive data)
    logger.info(
        "Jenkins webhook successfully received and verified",
        extra={
            "build_url": data.get("build_url", "unknown"),
            "commit_sha": data.get("commit_sha", "unknown")[:16] if data.get("commit_sha") else "unknown",
            "pr_number": data.get("pr_number", "unknown"),
        },
    )

    # TODO: Process the webhook asynchronously (trigger code review, etc.)
    # For now, just acknowledge receipt

    return {
        "status": "accepted",
        "build_url": data.get("build_url", "") if data else "",
        "commit_sha": data.get("commit_sha", "") if data else "",
        "pr_number": data.get("pr_number", 0) if data else 0,
    }