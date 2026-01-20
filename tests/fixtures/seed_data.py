"""Seed data and test fixtures for local development and testing."""
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Sample prospect data for testing
SAMPLE_PROSPECTS = [
    {
        "id": "prospect-001",
        "email": "sarah.johnson@techcorp.com",
        "first_name": "Sarah",
        "last_name": "Johnson",
        "company": "TechCorp Inc",
        "title": "VP of Engineering",
        "phone": "+1-555-0101",
        "linkedin": "https://linkedin.com/in/sarahjohnson",
        "source": "form_submission",
        "created_at": datetime.utcnow().isoformat(),
    },
    {
        "id": "prospect-002",
        "email": "michael.chen@innovate.io",
        "first_name": "Michael",
        "last_name": "Chen",
        "company": "Innovate Solutions",
        "title": "CTO",
        "phone": "+1-555-0102",
        "linkedin": "https://linkedin.com/in/mchen",
        "source": "campaign",
        "created_at": (datetime.utcnow() - timedelta(days=5)).isoformat(),
    },
    {
        "id": "prospect-003",
        "email": "emma.rodriguez@startupco.com",
        "first_name": "Emma",
        "last_name": "Rodriguez",
        "company": "StartUp Co",
        "title": "CEO",
        "phone": "+1-555-0103",
        "linkedin": "https://linkedin.com/in/emarodriguez",
        "source": "referral",
        "created_at": (datetime.utcnow() - timedelta(days=2)).isoformat(),
    },
]

# Sample HubSpot form submissions
SAMPLE_FORM_SUBMISSIONS = [
    {
        "portalId": "12345",
        "formId": "form1",
        "email": "sarah.johnson@techcorp.com",
        "company": "TechCorp Inc",
        "firstName": "Sarah",
        "lastName": "Johnson",
        "formSubmissionId": "sub-001",
        "pageTitle": "Book a Demo",
        "pageUri": "https://example.com/demo",
        "timestamp": int(datetime.utcnow().timestamp() * 1000),
        "submitText": "Schedule Call",
        "userMessage": "Very interested in learning more",
        "fieldValues": [
            {"name": "firstname", "value": "Sarah"},
            {"name": "lastname", "value": "Johnson"},
            {"name": "email", "value": "sarah.johnson@techcorp.com"},
            {"name": "company", "value": "TechCorp Inc"},
            {"name": "phone", "value": "555-0101"},
            {"name": "message", "value": "Very interested"},
        ],
    },
    {
        "portalId": "12345",
        "formId": "form2",
        "email": "michael.chen@innovate.io",
        "company": "Innovate Solutions",
        "firstName": "Michael",
        "lastName": "Chen",
        "formSubmissionId": "sub-002",
        "pageTitle": "Request Information",
        "pageUri": "https://example.com/info",
        "timestamp": int(datetime.utcnow().timestamp() * 1000),
        "submitText": "Request Info",
        "userMessage": "Send me more details",
        "fieldValues": [
            {"name": "firstname", "value": "Michael"},
            {"name": "lastname", "value": "Chen"},
            {"name": "email", "value": "michael.chen@innovate.io"},
            {"name": "company", "value": "Innovate Solutions"},
            {"name": "message", "value": "Interested in pricing"},
        ],
    },
]

# Sample Gmail threads (mock)
SAMPLE_GMAIL_THREADS = [
    {
        "id": "thread-001",
        "snippet": "Hi Sarah, thanks for attending the webinar! I wanted to...",
        "historyId": "123456",
        "messages": [
            {
                "id": "msg-001",
                "threadId": "thread-001",
                "labelIds": ["IMPORTANT", "INBOX"],
                "snippet": "Hi Sarah, thanks for attending the webinar!",
                "internalDate": str(int((datetime.utcnow() - timedelta(days=3)).timestamp() * 1000)),
                "payload": {
                    "headers": [
                        {"name": "From", "value": "contact@example.com"},
                        {"name": "Subject", "value": "Follow-up from webinar"},
                        {"name": "To", "value": "sarah.johnson@techcorp.com"},
                    ]
                },
            },
            {
                "id": "msg-002",
                "threadId": "thread-001",
                "labelIds": ["SENT"],
                "snippet": "Thanks for reaching out! Yes, I'd love to chat...",
                "internalDate": str(int((datetime.utcnow() - timedelta(days=2)).timestamp() * 1000)),
                "payload": {
                    "headers": [
                        {"name": "From", "value": "sarah.johnson@techcorp.com"},
                        {"name": "Subject", "value": "RE: Follow-up from webinar"},
                        {"name": "To", "value": "contact@example.com"},
                    ]
                },
            },
        ],
    },
]

# Sample calendar availability slots
SAMPLE_CALENDAR_SLOTS = [
    {
        "start": (datetime.utcnow() + timedelta(days=1, hours=10)).isoformat() + "Z",
        "end": (datetime.utcnow() + timedelta(days=1, hours=10, minutes=30)).isoformat() + "Z",
        "duration_minutes": 30,
    },
    {
        "start": (datetime.utcnow() + timedelta(days=1, hours=14)).isoformat() + "Z",
        "end": (datetime.utcnow() + timedelta(days=1, hours=14, minutes=30)).isoformat() + "Z",
        "duration_minutes": 30,
    },
    {
        "start": (datetime.utcnow() + timedelta(days=2, hours=11)).isoformat() + "Z",
        "end": (datetime.utcnow() + timedelta(days=2, hours=11, minutes=30)).isoformat() + "Z",
        "duration_minutes": 30,
    },
]

# Sample draft emails
SAMPLE_DRAFTS = [
    {
        "id": "draft-001",
        "to": "sarah.johnson@techcorp.com",
        "subject": "Quick thought on TechCorp's engineering challenges",
        "body": """Hi Sarah,

I noticed you're leading engineering at TechCorp Inc. We've been working with similar companies to help streamline their deployment pipelines.

Given TechCorp's focus on innovation, I thought you might be interested in a quick 30-minute conversation about how we've helped teams like yours reduce deployment time by 40%.

Would any of these times work?
- Tomorrow, 10:30 AM
- Tomorrow, 2:30 PM
- Thursday, 11:30 AM

No pressure either way - happy to chat if it makes sense!

Best regards,
[Your Name]""",
        "mode": "DRAFT_ONLY",
        "status": "draft",
        "created_at": datetime.utcnow().isoformat(),
    },
]

# Sample HubSpot tasks
SAMPLE_HUBSPOT_TASKS = [
    {
        "id": "task-001",
        "contact_id": "contact-12345",
        "subject": "Follow up with Sarah Johnson (TechCorp Inc)",
        "body": "Review draft email and approve before sending. Draft ID: draft-001",
        "hs_task_status": "NOT_STARTED",
        "hs_task_priority": "HIGH",
        "hs_task_due_date": int((datetime.utcnow() + timedelta(days=1)).timestamp() * 1000),
        "created_at": datetime.utcnow().isoformat(),
    },
]

# Sample prospecting messages (AI-generated)
SAMPLE_PROSPECTING_MESSAGES = [
    """Hi {first_name},

I noticed you're at {company} and impressed by what you're building. We recently helped a similar company in your space improve their sales process.

Would be great to grab 30 minutes to chat about how we're helping teams like yours.

Available:
- Tomorrow, 10:30 AM
- Tomorrow, 2:30 PM
- Thursday, 11:30 AM

Let me know!
{signature}""",

    """Hi {first_name},

Came across your LinkedIn and {company}'s recent news on {news_topic}. Exciting stuff!

We specialize in helping companies like yours with {solution_area}. Our clients typically see {metric} improvement in {outcome}.

Think it'd be worth a quick conversation?

{signature}""",

    """Hi {first_name},

{company} is doing some really interesting work in {industry}. I've been following your progress.

We've built solutions specifically for {use_case} that might be relevant. Happy to show you how we helped {similar_company} achieve {result}.

Coffee chat this week?

{signature}""",
]

# Sample audit trail events
SAMPLE_AUDIT_EVENTS = [
    {
        "event_id": "audit-001",
        "timestamp": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
        "event_type": "prospect_intake",
        "actor": "form_submission",
        "resource": "sarah.johnson@techcorp.com",
        "action": "intake",
        "status": "success",
        "details": {"source": "hubspot_form"},
    },
    {
        "event_id": "audit-002",
        "timestamp": (datetime.utcnow() - timedelta(hours=1, minutes=30)).isoformat(),
        "event_type": "draft_created",
        "actor": "system",
        "resource": "sarah.johnson@techcorp.com",
        "action": "create_draft",
        "status": "success",
        "details": {"draft_id": "draft-001", "mode": "DRAFT_ONLY"},
    },
    {
        "event_id": "audit-003",
        "timestamp": (datetime.utcnow() - timedelta(hours=1)).isoformat(),
        "event_type": "task_created",
        "actor": "system",
        "resource": "sarah.johnson@techcorp.com",
        "action": "create_task",
        "status": "success",
        "details": {"task_id": "task-001", "title": "Follow up with Sarah Johnson"},
    },
]


def get_sample_prospect(prospect_id: str = "prospect-001") -> Dict[str, Any]:
    """Get a sample prospect by ID."""
    for prospect in SAMPLE_PROSPECTS:
        if prospect["id"] == prospect_id:
            return prospect
    return SAMPLE_PROSPECTS[0]


def get_sample_form_submission(form_id: str = "form1") -> Dict[str, Any]:
    """Get a sample form submission by form ID."""
    import copy
    for submission in SAMPLE_FORM_SUBMISSIONS:
        if submission["formId"] == form_id:
            return copy.deepcopy(submission)
    return copy.deepcopy(SAMPLE_FORM_SUBMISSIONS[0])


def get_all_sample_prospects() -> List[Dict[str, Any]]:
    """Get all sample prospects."""
    return SAMPLE_PROSPECTS


def get_all_sample_submissions() -> List[Dict[str, Any]]:
    """Get all sample form submissions."""
    return SAMPLE_FORM_SUBMISSIONS


def export_seed_data(output_file: str = "seed_data.json") -> None:
    """Export all seed data to JSON file."""
    seed_data = {
        "prospects": SAMPLE_PROSPECTS,
        "form_submissions": SAMPLE_FORM_SUBMISSIONS,
        "gmail_threads": SAMPLE_GMAIL_THREADS,
        "calendar_slots": SAMPLE_CALENDAR_SLOTS,
        "drafts": SAMPLE_DRAFTS,
        "hubspot_tasks": SAMPLE_HUBSPOT_TASKS,
        "prospecting_messages": SAMPLE_PROSPECTING_MESSAGES,
        "audit_events": SAMPLE_AUDIT_EVENTS,
    }

    with open(output_file, "w") as f:
        json.dump(seed_data, f, indent=2)

    print(f"Seed data exported to {output_file}")


if __name__ == "__main__":
    # Export seed data when run directly
    export_seed_data()
    print("Sample data:")
    print(f"- {len(SAMPLE_PROSPECTS)} prospects")
    print(f"- {len(SAMPLE_FORM_SUBMISSIONS)} form submissions")
    print(f"- {len(SAMPLE_GMAIL_THREADS)} email threads")
    print(f"- {len(SAMPLE_CALENDAR_SLOTS)} calendar slots")
    print(f"- {len(SAMPLE_DRAFTS)} draft emails")
    print(f"- {len(SAMPLE_HUBSPOT_TASKS)} HubSpot tasks")
