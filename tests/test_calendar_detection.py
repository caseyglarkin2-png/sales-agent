"""Tests for calendar link detection in email drafts."""

import pytest


@pytest.fixture
def sample_emails():
    """Sample emails with and without calendar links."""
    return {
        "with_hubspot": "Book time: https://meetings.hubspot.com/casey-larkin",
        "with_calendly": "Schedule here: https://calendly.com/casey/30min",
        "with_cal": "Use this link: https://cal.com/casey",
        "without_link": "Let's schedule a call next week.",
        "with_multiple": "Book via https://meetings.hubspot.com/casey or https://calendly.com/casey"
    }


# Smoke test to validate fixture
def test_sample_emails_fixture_structure(sample_emails):
    """Validate sample_emails fixture has all required email types."""
    assert "with_hubspot" in sample_emails
    assert "with_calendly" in sample_emails
    assert "with_cal" in sample_emails
    assert "without_link" in sample_emails
    assert "with_multiple" in sample_emails
    
    # Verify links are present
    assert "meetings.hubspot.com" in sample_emails["with_hubspot"]
    assert "calendly.com" in sample_emails["with_calendly"]
    assert "cal.com" in sample_emails["with_cal"]
    assert "http" not in sample_emails["without_link"]


# Additional tests will be added in Sprint 3

