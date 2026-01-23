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


# Tests will be added in Sprint 3
# Placeholder structure for now
