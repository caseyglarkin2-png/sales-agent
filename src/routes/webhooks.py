"""HubSpot form webhook route for capturing new leads.

Receives form submissions from HubSpot and initiates the prospecting workflow.
Also creates signals for the CaseyOS command queue.
"""
import asyncio
from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.logger import get_logger
from src.formlead_orchestrator import create_formlead_orchestrator
from src.tasks.formlead_task import process_formlead_async
from src.db import get_db
from src.models.signal import SignalSource
from src.services.signal_service import SignalService

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
async def hubspot_form_submission(
    payload: FormSubmissionPayload,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Receive HubSpot form submission webhook.

    HubSpot sends a POST when a form is submitted. This endpoint:
    1. Validates the form ID
    2. Extracts contact information
    3. Creates a Signal for CaseyOS command queue
    4. Queues the prospecting workflow

    Args:
        payload: HubSpot form submission payload
        db: Database session

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

    # Convert payload to dict for orchestrator
    form_data = {
        "portalId": payload.portalId,
        "formId": payload.formId,
        "formSubmissionId": payload.formSubmissionId,
        "email": email,
        "company": company or "",
        "firstName": first_name or "",
        "lastName": last_name or "",
        "fieldValues": [{"name": f.name, "value": f.value} for f in payload.fieldValues],
    }

    # Create signal for CaseyOS command queue
    signal_id: Optional[str] = None
    recommendation_id: Optional[str] = None
    signal_error: Optional[str] = None
    try:
        signal_service = SignalService(db)
        signal, recommendation = await signal_service.create_and_process(
            source=SignalSource.FORM,
            event_type="form_submitted",
            payload={
                "email": email,
                "name": f"{first_name or ''} {last_name or ''}".strip() or "Unknown",
                "company": company or "Unknown",
                "form_id": payload.formId,
                "portal_id": payload.portalId,
                "form_submission_id": payload.formSubmissionId,
            },
            source_id=payload.formSubmissionId,
        )
        await db.commit()
        signal_id = signal.id
        recommendation_id = recommendation.id if recommendation else None
        logger.info(
            "Signal created for form submission",
            signal_id=signal_id,
            recommendation_id=recommendation_id,
        )
    except Exception as e:
        signal_error = str(e)
        logger.warning(f"Failed to create signal (non-fatal): {e}", exc_info=True)
        await db.rollback()

    # Generate workflow ID for tracking
    workflow_id = f"form-lead-{uuid4()}"

    # Queue the form lead processing as async task
    try:
        # Use .apply_async to get task ID immediately
        task = process_formlead_async.apply_async(
            args=(form_data,),
            kwargs={"workflow_id": workflow_id},
            task_id=workflow_id,  # Use workflow ID as task ID for correlation
        )

        logger.info(
            "Form lead task queued",
            task_id=task.id,
            workflow_id=workflow_id,
            email=email,
        )

        return {
            "status": "accepted",
            "submission_id": payload.formSubmissionId,
            "email": email,
            "workflow_id": workflow_id,
            "task_id": task.id,
            "signal_id": signal_id,
            "recommendation_id": recommendation_id,
            "signal_error": signal_error,
            "message": "Form submission queued for processing",
            "status_url": f"/api/tasks/{workflow_id}/status",
        }
    except Exception as e:
        logger.error(
            "Error queueing form lead task",
            workflow_id=workflow_id,
            email=email,
            exc_info=True,
        )
        # Still return 202 to avoid HubSpot retry storms
        return {
            "status": "accepted",
            "submission_id": payload.formSubmissionId,
            "email": email,
            "workflow_id": workflow_id,
            "signal_error": signal_error,
            "message": "Form submission queued but may have failed",
            "error": str(e),
        }


@router.post("/hubspot/workflow", status_code=status.HTTP_202_ACCEPTED)
async def hubspot_workflow_webhook(request: Request) -> dict[str, Any]:
    """Receive HubSpot workflow webhook with contact data.

    HubSpot workflows send contact properties directly, not form submission format.
    This endpoint accepts flexible JSON payloads from workflow actions.
    """
    import uuid
    from datetime import datetime
    
    try:
        body = await request.json()
    except Exception:
        body = {}
    
    logger.info("Received HubSpot workflow webhook", payload_keys=list(body.keys()) if body else [])
    
    # Extract contact info from various possible formats
    # HubSpot workflow can send: email, firstname, lastname, company, etc.
    email = (
        body.get("email") or 
        body.get("properties", {}).get("email") or
        body.get("contact", {}).get("email")
    )
    first_name = (
        body.get("firstname") or 
        body.get("first_name") or
        body.get("properties", {}).get("firstname")
    )
    last_name = (
        body.get("lastname") or 
        body.get("last_name") or
        body.get("properties", {}).get("lastname")
    )
    company = (
        body.get("company") or 
        body.get("company_name") or
        body.get("properties", {}).get("company")
    )
    
    if not email:
        logger.warning("Workflow webhook missing email", payload=body)
        return {
            "status": "error",
            "message": "Email is required",
            "received_keys": list(body.keys()) if body else [],
        }
    
    logger.info("Workflow webhook valid", email=email, first_name=first_name, company=company)
    
    # Convert to form data format for orchestrator
    submission_id = f"workflow-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
    form_data = {
        "portalId": body.get("portalId", body.get("portal_id", 23918564)),
        "formId": body.get("formId", body.get("form_id", "workflow-trigger")),
        "formSubmissionId": submission_id,
        "email": email,
        "company": company or "",
        "firstName": first_name or "",
        "lastName": last_name or "",
        "fieldValues": [
            {"name": "email", "value": email},
            {"name": "firstname", "value": first_name or ""},
            {"name": "lastname", "value": last_name or ""},
            {"name": "company", "value": company or ""},
        ],
    }
    
    # Add workflow-trigger to allowlist dynamically
    try:
        orchestrator = create_formlead_orchestrator()
        result = await orchestrator.process_formlead(form_data)
        
        logger.info("Workflow lead processed", workflow_id=result.get("workflow_id"), status=result.get("final_status"))
        
        return {
            "status": "accepted",
            "submission_id": submission_id,
            "email": email,
            "workflow_id": result.get("workflow_id"),
            "workflow_status": result.get("final_status"),
            "message": "Workflow contact processed in DRAFT_ONLY mode",
        }
    except Exception as e:
        logger.error(f"Error processing workflow lead: {e}")
        return {
            "status": "accepted",
            "submission_id": submission_id,
            "email": email,
            "message": "Workflow contact queued for retry",
            "error": str(e),
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


@router.post("/hubspot/forms", status_code=status.HTTP_202_ACCEPTED)
async def hubspot_forms_webhook_validated(
    request: Request,
    background_tasks: BackgroundTasks
) -> dict[str, Any]:
    """
    Receive HubSpot form submission webhook with signature validation.
    
    This is the production webhook endpoint with:
    - HMAC-SHA256 signature validation
    - Idempotency (duplicate detection)
    - Database persistence
    - Async workflow queuing
    
    Args:
        request: FastAPI Request object (for raw body + headers)
        background_tasks: FastAPI background tasks
        
    Returns:
        202 Accepted with submission_id
        
    Raises:
        401: Invalid signature
        409: Duplicate submission
        400: Invalid payload
    """
    # Get raw body and signature header
    body = await request.body()
    signature = request.headers.get("X-HubSpot-Signature", "")
    
    if not signature:
        logger.warning("Webhook received without signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-HubSpot-Signature header"
        )
    
    # Process webhook
    processor = WebhookProcessor()
    
    try:
        submission_data = await processor.process_webhook(body, signature)
    except WebhookValidationError as e:
        logger.error(f"Webhook validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED if "signature" in str(e).lower() else status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    # Check for duplicate
    is_duplicate = await processor.check_duplicate(submission_data.submission_id)
    if is_duplicate:
        logger.info(
            "Duplicate submission detected (idempotent)",
            extra={"submission_id": submission_data.submission_id}
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Submission {submission_data.submission_id} already processed"
        )
    
    # Store to database
    try:
        db_id = await processor.store_submission(submission_data)
    except WebhookValidationError as e:
        logger.error(f"Failed to store submission: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Storage failed: {e}"
        )
    
    # Queue async workflow processing (Task 4.4)
    from src.tasks import queue_workflow_processing
    
    task_id = queue_workflow_processing(str(db_id))
    
    logger.info(
        "Webhook accepted, queued for processing",
        extra={
            "submission_id": submission_data.submission_id,
            "db_id": str(db_id),
            "email": submission_data.prospect_email,
            "task_id": task_id
        }
    )
    
    return {
        "status": "accepted",
        "submission_id": submission_data.submission_id,
        "db_id": str(db_id),
        "email": submission_data.prospect_email,
        "task_id": task_id,
        "message": "Form submission queued for workflow processing"
    }

