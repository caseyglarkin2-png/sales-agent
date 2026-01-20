"""Tests for webhook validation."""
import pytest

from src.webhook import WebhookValidator


def test_webhook_signature_validation():
    """Test webhook signature validation."""
    secret = "my-secret-key"
    validator = WebhookValidator(secret)
    
    payload = '{"event": "test"}'
    signature = validator.get_signature_header(payload)
    
    assert validator.verify_signature(payload, signature) is True


def test_webhook_signature_validation_fails_on_mismatch():
    """Test webhook signature validation fails on mismatch."""
    validator = WebhookValidator("secret")
    
    payload = '{"event": "test"}'
    wrong_signature = "wrong-signature"
    
    assert validator.verify_signature(payload, wrong_signature) is False


def test_webhook_signature_validation_fails_on_modified_payload():
    """Test webhook signature validation fails when payload is modified."""
    secret = "secret"
    validator = WebhookValidator(secret)
    
    payload = '{"event": "test"}'
    signature = validator.get_signature_header(payload)
    
    modified_payload = '{"event": "modified"}'
    assert validator.verify_signature(modified_payload, signature) is False
