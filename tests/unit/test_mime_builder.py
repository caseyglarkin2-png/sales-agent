"""Tests for MIME message builder."""
import pytest
from email import message_from_string

from src.email_utils.mime_builder import build_mime_message, validate_mime_message


def test_build_simple_text_message():
    """Test building simple plain text email."""
    msg_str = build_mime_message(
        from_email="alex@pesti.io",
        to_email="prospect@company.com",
        subject="Test Email",
        body_text="This is a test message.",
    )
    
    # Parse and validate
    msg = message_from_string(msg_str)
    assert msg["From"] == "alex@pesti.io"
    assert msg["To"] == "prospect@company.com"
    assert msg["Subject"] == "Test Email"
    assert msg["Date"] is not None
    assert msg["Message-ID"] is not None
    assert msg["Message-ID"].endswith("@pesti.io>")
    
    # Check body
    payload = msg.get_payload(decode=True).decode('utf-8') if msg.get_payload() else ""
    assert "This is a test message." in payload


def test_build_multipart_message():
    """Test building multipart message with HTML."""
    msg_str = build_mime_message(
        from_email="alex@pesti.io",
        to_email="prospect@company.com",
        subject="HTML Email",
        body_text="Plain text version",
        body_html="<html><body><p>HTML version</p></body></html>",
    )
    
    msg = message_from_string(msg_str)
    assert msg.is_multipart()
    
    # Check both parts exist
    parts = list(msg.walk())
    assert len(parts) >= 3  # Container + text + html
    
    # Check content types
    content_types = [part.get_content_type() for part in parts]
    assert "text/plain" in content_types
    assert "text/html" in content_types


def test_build_message_with_threading():
    """Test building message with threading headers."""
    original_msg_id = "<original-123@company.com>"
    msg_str = build_mime_message(
        from_email="alex@pesti.io",
        to_email="prospect@company.com",
        subject="Re: Previous conversation",
        body_text="This is a reply",
        in_reply_to=original_msg_id,
        references=original_msg_id,
    )
    
    msg = message_from_string(msg_str)
    assert msg["In-Reply-To"] == original_msg_id
    assert msg["References"] == original_msg_id


def test_validate_mime_message_valid():
    """Test validation of valid MIME message."""
    msg_str = build_mime_message(
        from_email="test@example.com",
        to_email="user@test.com",
        subject="Valid Message",
        body_text="Content here",
    )
    
    result = validate_mime_message(msg_str)
    assert result["valid"] is True
    assert len(result["errors"]) == 0
    assert result["size_bytes"] > 0
    assert result["size_bytes"] < 1000  # Should be small


def test_validate_mime_message_missing_headers():
    """Test validation catches missing headers."""
    invalid_msg = "From: test@example.com\n\nBody content"
    
    result = validate_mime_message(invalid_msg)
    assert result["valid"] is False
    assert any("To" in err for err in result["errors"])
    assert any("Subject" in err for err in result["errors"])


def test_validate_mime_message_size_warning():
    """Test validation warns on large messages."""
    # Create a large message (> 1MB)
    large_body = "X" * 1_500_000
    msg_str = build_mime_message(
        from_email="test@example.com",
        to_email="user@test.com",
        subject="Large Message",
        body_text=large_body,
    )
    
    result = validate_mime_message(msg_str)
    assert len(result["warnings"]) > 0
    assert any("1MB" in warn for warn in result["warnings"])
    assert result["size_bytes"] > 1_000_000


def test_message_id_uses_domain():
    """Test Message-ID uses sender's domain."""
    msg_str = build_mime_message(
        from_email="alex@pesti.io",
        to_email="prospect@company.com",
        subject="Domain Test",
        body_text="Testing domain extraction",
    )
    
    msg = message_from_string(msg_str)
    message_id = msg["Message-ID"]
    assert "@pesti.io>" in message_id
