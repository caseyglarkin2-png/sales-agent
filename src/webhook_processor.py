"""
HubSpot webhook processing logic.

Handles form submission webhooks with signature validation and storage.
"""
import hashlib
import hmac
import json
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator

from src.config import get_settings
from src.logger import get_logger

logger = get_logger(__name__)


class HubSpotFormField(BaseModel):
    """Individual form field from HubSpot webhook."""
    name: str
    value: str
    

class HubSpotWebhookPayload(BaseModel):
    """HubSpot form submission webhook payload."""
    portalId: int
    formId: str
    formGuid: Optional[str] = None
    formSubmissionId: str = Field(..., alias="submissionId")
    fields: list[HubSpotFormField]
    submittedAt: Optional[int] = None  # Unix timestamp
    pageUrl: Optional[str] = None
    pageName: Optional[str] = None
    
    class Config:
        populate_by_name = True


class FormSubmissionData(BaseModel):
    """Parsed form submission data for storage."""
    submission_id: str
    portal_id: int
    form_id: str
    prospect_email: str
    prospect_name: Optional[str] = None
    prospect_company: Optional[str] = None
    raw_fields: dict
    raw_payload: dict
    submitted_at: Optional[datetime] = None


class WebhookValidationError(Exception):
    """Raised when webhook validation fails."""
    pass


class WebhookProcessor:
    """
    Processes HubSpot form webhooks with validation and storage.
    
    Key responsibilities:
    - Validate HMAC-SHA256 signature
    - Parse form fields into structured data
    - Check for duplicate submissions (idempotency)
    - Store to database for async processing
    """
    
    def __init__(self):
        self.settings = get_settings()
        self._webhook_secret = self.settings.hubspot_webhook_secret
        
    def validate_signature(self, body: bytes, signature: str) -> bool:
        """
        Validate HubSpot webhook signature.
        
        Args:
            body: Raw request body (bytes)
            signature: X-HubSpot-Signature header value
            
        Returns:
            True if signature is valid
            
        Raises:
            WebhookValidationError: If signature invalid or secret not configured
        """
        if not self._webhook_secret:
            raise WebhookValidationError(
                "HUBSPOT_WEBHOOK_SECRET not configured - cannot validate webhooks"
            )
            
        # HubSpot uses SHA-256 HMAC
        expected_signature = hmac.new(
            key=self._webhook_secret.encode('utf-8'),
            msg=body,
            digestmod=hashlib.sha256
        ).hexdigest()
        
        is_valid = hmac.compare_digest(expected_signature, signature)
        
        if not is_valid:
            logger.warning(
                "Invalid webhook signature",
                extra={"expected": expected_signature[:16], "received": signature[:16]}
            )
            
        return is_valid
        
    def parse_form_fields(self, fields: list[HubSpotFormField]) -> dict:
        """
        Parse form fields into dict for easy access.
        
        Args:
            fields: List of form fields from webhook
            
        Returns:
            Dict mapping field names to values
        """
        return {field.name: field.value for field in fields}
        
    def extract_prospect_data(self, fields: dict, raw_payload: dict) -> FormSubmissionData:
        """
        Extract prospect information from form fields.
        
        Args:
            fields: Parsed form fields dict
            raw_payload: Original webhook payload
            
        Returns:
            FormSubmissionData with extracted prospect info
            
        Raises:
            WebhookValidationError: If required fields missing
        """
        # Extract email (required)
        email = fields.get('email') or fields.get('Email') or fields.get('EMAIL')
        if not email:
            raise WebhookValidationError("Missing required field: email")
            
        # Extract name (try multiple field name variations)
        first_name = (
            fields.get('firstname') or 
            fields.get('firstName') or 
            fields.get('first_name') or 
            fields.get('FirstName') or 
            ''
        )
        last_name = (
            fields.get('lastname') or 
            fields.get('lastName') or 
            fields.get('last_name') or 
            fields.get('LastName') or 
            ''
        )
        
        full_name = f"{first_name} {last_name}".strip() or None
        
        # Extract company
        company = (
            fields.get('company') or 
            fields.get('Company') or 
            fields.get('COMPANY') or 
            None
        )
        
        # Extract timestamps
        submitted_at = None
        if raw_payload.get('submittedAt'):
            # Convert Unix timestamp (milliseconds) to datetime
            submitted_at = datetime.fromtimestamp(raw_payload['submittedAt'] / 1000.0)
        
        return FormSubmissionData(
            submission_id=raw_payload['formSubmissionId'],
            portal_id=raw_payload['portalId'],
            form_id=raw_payload['formId'],
            prospect_email=email,
            prospect_name=full_name,
            prospect_company=company,
            raw_fields=fields,
            raw_payload=raw_payload,
            submitted_at=submitted_at
        )
        
    async def process_webhook(
        self, 
        body: bytes, 
        signature: str
    ) -> FormSubmissionData:
        """
        Process HubSpot webhook end-to-end.
        
        Args:
            body: Raw request body
            signature: X-HubSpot-Signature header
            
        Returns:
            Parsed form submission data
            
        Raises:
            WebhookValidationError: If validation fails
        """
        # Validate signature
        if not self.validate_signature(body, signature):
            raise WebhookValidationError("Invalid webhook signature")
            
        # Parse JSON payload
        try:
            raw_payload = json.loads(body)
            payload = HubSpotWebhookPayload(**raw_payload)
        except json.JSONDecodeError as e:
            raise WebhookValidationError(f"Invalid JSON payload: {e}")
        except Exception as e:
            raise WebhookValidationError(f"Invalid payload structure: {e}")
            
        # Parse fields
        fields = self.parse_form_fields(payload.fields)
        
        # Extract prospect data
        submission_data = self.extract_prospect_data(fields, raw_payload)
        
        logger.info(
            "Webhook processed successfully",
            extra={
                "submission_id": submission_data.submission_id,
                "prospect_email": submission_data.prospect_email,
                "form_id": submission_data.form_id
            }
        )
        
        return submission_data
        
    async def check_duplicate(self, submission_id: str) -> bool:
        """
        Check if submission already processed (idempotency).
        
        Args:
            submission_id: HubSpot submission ID
            
        Returns:
            True if duplicate exists
        """
        # TODO: Query database for existing submission
        # For now, return False (no duplicate detection until DB integrated)
        from src.models.form_submission import FormSubmission
        from src.db import async_session
        
        async with async_session() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(FormSubmission).where(
                    FormSubmission.form_submission_id == submission_id
                )
            )
            existing = result.scalar_one_or_none()
            return existing is not None
            
    async def store_submission(self, data: FormSubmissionData) -> UUID:
        """
        Store form submission to database.
        
        Args:
            data: Parsed submission data
            
        Returns:
            UUID of created form_submission record
            
        Raises:
            WebhookValidationError: If storage fails
        """
        from src.models.form_submission import FormSubmission
        from src.db import async_session
        
        try:
            async with async_session() as session:
                submission = FormSubmission(
                    form_submission_id=data.submission_id,
                    portal_id=data.portal_id,
                    form_id=data.form_id,
                    prospect_email=data.prospect_email,
                    prospect_full_name=data.prospect_name,
                    prospect_company=data.prospect_company,
                    raw_fields=data.raw_fields,
                    raw_payload=data.raw_payload,
                    submitted_at=data.submitted_at,
                    is_processed=False,
                    is_pending=True
                )
                
                session.add(submission)
                await session.commit()
                await session.refresh(submission)
                
                logger.info(
                    "Form submission stored",
                    extra={"id": str(submission.id), "email": data.prospect_email}
                )
                
                return submission.id
                
        except Exception as e:
            logger.error(f"Failed to store submission: {e}")
            raise WebhookValidationError(f"Storage failed: {e}")
