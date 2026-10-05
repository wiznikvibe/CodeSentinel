"""Unit tests for Jenkins webhook receiver."""

import hmac
import hashlib
import pytest

from api.routes.webhook import verify_jenkins_signature


def test_verify_jenkins_signature_valid():
    """Valid HMAC-SHA256 signature should be verified correctly."""
    secret = "test-token-123"
    # Compute the expected signature
    payload = b'{"build_url": "http://example.com"}'
    mac = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    signature = mac

    assert verify_jenkins_signature(payload, signature, secret) is True


def test_verify_jenkins_signature_invalid():
    """Invalid signature should be rejected."""
    secret = "test-token-123"
    payload = b'{"build_url": "http://example.com"}'
    signature = "invalid-signature"

    assert verify_jenkins_signature(payload, signature, secret) is False


def test_verify_jenkins_signature_wrong_secret():
    """Signature computed with wrong secret should be rejected."""
    secret = "correct-token"
    wrong_secret = "wrong-token"
    payload = b'{"build_url": "http://example.com"}'
    mac = hmac.new(wrong_secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    signature = mac

    assert verify_jenkins_signature(payload, signature, secret) is False