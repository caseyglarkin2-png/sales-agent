"""HubSpot form webhook route for capturing new leads.

Receives form submissions from HubSpot and initiates the prospecting workflow.
"""
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from src.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/webhooks", tags=["Webhooks"])


class FormFieldValue(BaseModel):
    """A single form field value."""

    objectTypeId: str = Field(description="Object type (e.g., '0-1' for contact)")
    formSubmissionId: str = Field(description="Unique submission ID")
    pageTitle: str | None = Field(None, description="Page title")
    pageUri: str | None = Field(None, description="Page URL")
    timestamp: int = Field(description="Unix timestamp in milliseconds")
    submitText: str | None = Field(None, description="Submit button text")
    userMessage: str | None = Field(None, description="Message from user")


class FormFieldData(BaseModel):
    """Form field with name and value."""

    name: str = Field(description="Field name (e.g., 'firstname', 'email')")
    value: str = Field(description="Field value")


class FormSubmissionPayload(BaseModel):
    """HubSpot form submission webhook payload.

    This is the shape of data sent by HubSpot when a form is submitted.
    See: https://developers.hubspot.com/docs/api/webhooks/form-submissions
    """

    portalId: int = Field(description="HubSpot portal/account ID")
    formId: str = Field(description="HubSpot form ID")
    formSubmissionId: str = Field(description="Unique submission ID")
    pageTitle: str | None = Field(None, description="Page where form was submitted")
    pageUri: str | None = Field(None, description="URL of page")
    timestamp: int = Field(description="Unix timestamp in milliseconds")
    submitText: str | None = Field(None, description="Submit button text")
    userMessage: str | None = Field(None, description="User message (if text field)")
    fieldValues: list[FormFieldData] = Field(description="List of submitted field values")

    def get_field(self, name: str) -> str | None:
        """Get a field value by name (case-insensitive)."""
        for field in self.fieldValues:
            if field.name.lower() == name.lower():
                return field.value
        return None

    def get_email(self) -> str | None:
        """Extract email from form fields."""
        return self.get_field("email")

    def get_first_name(self) -> str | None:
        """Extract first name from form fields."""
        return self.get_field("firstname")

    def get_last_name(self) -> str | None:
        """Extract last name from form fields."""
        return self.get_field("lastname")

    def get_company(self) -> str | None:
        """Extract company from form fields."""
        return (
            self.get_field("company")
            or self.get_field("company_name")
            or self.get_field("company")
        )


# Define expected form IDs for validation
EXPECTED_FORM_IDS = [
    "lead-interest-form",  # Development/testing
    "contact-form",  # General contact
    "demo-request-form",  # Demo request
]


def validate_form_id(form_id: str) -> bool:
    """Check if form_id is one of our expected forms.

    In production, validate against HubSpot to ensure webhooks
    are only from forms you've configured.

    Args:
        form_id: The HubSpot form ID

    Returns:
        True if form is valid, False otherwise
    """
    # For now, accept any form with a valid format
    # In production, validate against EXPECTED_FORM_IDS or query HubSpot
    return bool(form_id and len(form_id) > 0)


@router.post("/hubspot/form-submission", status_code=status.HTTP_202_ACCEPTED)
async def hubspot_form_submission(payload: FormSubmissionPayload) -> dict[str, Any]:
    """Receive HubSpot form submission webhook.

    HubSpot sends a POST when a form is submitted. This endpoint:
    1. Validates the form ID
    2. Extracts contact information
    3. Queues the prospecting workflow

    Args:
        payload: HubSpot form submission payload

    Returns:
        Acknowledgment with submission ID

    Raises:
        HTTPException: If form ID is unexpected or data is invalid
    """
    logger.info(
        "Received HubSpot form submission",
        form_id=payload.formId,
        submission_id=payload.formSubmissionId,
        portal_id=payload.portalId,
    )

    # Validate form ID
    if not validate_form_id(payload.formId):
        logger.warning(f"Unexpected form ID: {payload.formId}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Form {payload.formId} not configured for webhooks. "
            f"Expected one of: {', '.join(EXPECTED_FORM_IDS)}",
        )

    # Extract contact info
    email = payload.get_email()
    first_name = payload.get_first_name()
    last_name = payload.get_last_name()
    company = payload.get_company()

    if not email:
        logger.warning("Form submission missing email", submission_id=payload.formSubmissionId)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Form submission must include email address",
        )

    logger.info(
        "Form submission valid",
        email=email,
        first_name=first_name,
        company=company,
    )

    # TODO: Queue the prospecting workflow
    # For now, just acknowledge receipt
    # In future: create_prospecting_task(email, first_name, last_name, company)

    return {
        "status": "accepted",
        "submission_id": payload.formSubmissionId,
        "email": email,
        "message": "Form submission queued for processing",
    }


@router.post("/hubspot/form-submission/test", status_code=status.HTTP_200_OK)
async def hubspot_form_submission_test(payload: FormSubmissionPayload) -> dict[str, Any]:
    """Test endpoint for validating HubSpot form webhook.

    Use this to test the webhook locally before configuring in HubSpot.

    Example payload:
    ```json
    {
      "portalId": 12345,
      "formId": "lead-interest-form",
      "formSubmissionId": "submission-12345",
      "pageTitle": "Sales Demo",
      "pageUri": "https://company.com/demo",
      "timestamp": 1674150000000,
      "submitText": "Request Demo",
      "userMessage": null,
      "fieldValues": [
        {"name": "firstname", "value": "John"},
        {"name": "lastname", "value": "Doe"},
        {"name": "email", "value": "john@company.com"},
        {"name": "company", "value": "Company Inc"}
      ]
    }
    ```
    """
    logger.info(
        "HubSpot form webhook test",
        form_id=payload.formId,
        email=payload.get_email(),
    )

    return {
        "status": "ok",
        "message": "Form validation successful",
        "email": payload.get_email(),
        "company": payload.get_company(),
        "first_name": payload.get_first_name(),
        "received_fields": len(payload.fieldValues),
    }


@router.get("/hubspot/form-submission/example-payload", status_code=status.HTTP_200_OK)
async def get_example_payload() -> dict[str, Any]:
    """Get example HubSpot form submission payload for testing.

    Use this to construct test payloads or understand the format.
    """
    return {
        "portalId": 12345,
        "formId": "lead-interest-form",
        "formSubmissionId": "submission-" + "x" * 24,
        "pageTitle": "Sales Demo Request",
        "pageUri": "https://company.com/demo",
        "timestamp": 1674150000000,  # Unix timestamp in milliseconds
        "submitText": "Request Demo",
        "userMessage": None,
        "fieldValues": [
            {"name": "firstname", "value": "John"},
            {"name": "lastname", "value": "Doe"},
            {"name": "email", "value": "john@company.com"},
            {"name": "company", "value": "Company Inc"},
            {
                "name": "company_size",
                "value": "50-200",
            },  # Custom field
        ],
    }
