"""Prospecting agent orchestrator - chains agents and connectors for complete workflows."""
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.agents.prospecting import ProspectingAgent
from src.agents.nurturing import NurturingAgent
from src.agents.validation import ValidationAgent
from src.connectors.gmail import GmailConnector
from src.connectors.hubspot import HubSpotConnector
from src.connectors.calendar_connector import CalendarConnector
from src.logger import get_logger
from src.models import Prospect, Task

logger = get_logger(__name__)


class ProspectingOrchestrator:
    """Orchestrates prospecting workflow: intake → resolve → research → schedule → draft → task."""

    def __init__(
        self,
        prospecting_agent: Optional[ProspectingAgent] = None,
        nurturing_agent: Optional[NurturingAgent] = None,
        validation_agent: Optional[ValidationAgent] = None,
        gmail_connector: Optional[GmailConnector] = None,
        hubspot_connector: Optional[HubSpotConnector] = None,
        calendar_connector: Optional[CalendarConnector] = None,
    ):
        """Initialize orchestrator with agents and connectors."""
        self.prospecting_agent = prospecting_agent
        self.nurturing_agent = nurturing_agent
        self.validation_agent = validation_agent
        self.gmail_connector = gmail_connector
        self.hubspot_connector = hubspot_connector
        self.calendar_connector = calendar_connector
        self.context: Dict[str, Any] = {}

    async def run_complete_workflow(
        self,
        form_submission: Dict[str, Any],
        draft_only: bool = True,
    ) -> Dict[str, Any]:
        """Execute complete prospecting workflow from form submission to draft + task."""
        workflow_id = f"workflow-{datetime.utcnow().isoformat()}"
        self.context = {
            "workflow_id": workflow_id,
            "timestamp": datetime.utcnow().isoformat(),
            "draft_only": draft_only,
            "steps": {},
        }

        try:
            # Step 1: Extract prospect from form
            logger.info("Step 1: Extracting prospect from form submission")
            prospect = await self._extract_prospect(form_submission)
            if not prospect:
                raise ValueError("Failed to extract prospect from form")
            self.context["prospect"] = prospect.dict()

            # Step 2: Resolve contact/company in HubSpot
            logger.info("Step 2: Resolving contact/company in HubSpot")
            hubspot_data = await self._resolve_hubspot(prospect)
            if hubspot_data:
                self.context["hubspot"] = hubspot_data

            # Step 3: Search Gmail for existing conversations
            logger.info("Step 3: Searching Gmail for existing conversations")
            email_context = await self._search_email_context(prospect)
            if email_context:
                self.context["email_context"] = email_context

            # Step 4: Check calendar availability
            logger.info("Step 4: Checking calendar availability")
            available_slots = await self._get_available_slots()
            if available_slots:
                self.context["available_slots"] = available_slots

            # Step 5: Generate prospecting message
            logger.info("Step 5: Generating prospecting message")
            message = await self._generate_message(prospect, email_context)
            if not message:
                raise ValueError("Failed to generate prospecting message")
            self.context["message"] = message

            # Step 6: Create draft email (DRAFT_ONLY enforced)
            logger.info("Step 6: Creating draft email (DRAFT_ONLY mode)")
            draft_id = await self._create_draft(prospect, message)
            if draft_id:
                self.context["draft_id"] = draft_id
            else:
                logger.warning("Draft creation failed or skipped")

            # Step 7: Create HubSpot task/note
            logger.info("Step 7: Creating HubSpot task and note")
            task_data = await self._create_hubspot_task(prospect, message, draft_id)
            if task_data:
                self.context["task"] = task_data

            self.context["status"] = "success"
            logger.info(f"Workflow {workflow_id} completed successfully")
            return self.context

        except Exception as e:
            logger.error(f"Workflow {workflow_id} failed: {e}")
            self.context["status"] = "failed"
            self.context["error"] = str(e)
            return self.context

    async def _extract_prospect(self, form_submission: Dict[str, Any]) -> Optional[Prospect]:
        """Extract prospect data from form submission."""
        try:
            # Use validation agent to extract and validate
            if self.validation_agent:
                prospect = await self.validation_agent.validate_prospect(form_submission)
                self.context["steps"]["extract_prospect"] = {
                    "status": "success",
                    "prospect_id": prospect.id if prospect else None,
                }
                return prospect
            else:
                # Fallback: manually construct prospect
                prospect = Prospect(
                    email=form_submission.get("email"),
                    first_name=form_submission.get("first_name", ""),
                    last_name=form_submission.get("last_name", ""),
                    company=form_submission.get("company", ""),
                )
                return prospect
        except Exception as e:
            logger.error(f"Error extracting prospect: {e}")
            self.context["steps"]["extract_prospect"] = {"status": "failed", "error": str(e)}
            return None

    async def _resolve_hubspot(self, prospect: Prospect) -> Optional[Dict[str, Any]]:
        """Resolve prospect in HubSpot (find or create contact/company)."""
        try:
            if not self.hubspot_connector:
                logger.warning("HubSpot connector not available")
                return None

            # Search for existing contact
            contact = await self.hubspot_connector.search_contacts(prospect.email)
            if contact:
                contact_id = contact["id"]
                logger.info(f"Found existing HubSpot contact {contact_id}")
            else:
                # Would create new contact here in production
                logger.info(f"No existing contact found for {prospect.email}")
                contact_id = None

            # Get associated companies
            company_id = None
            if contact_id:
                associations = await self.hubspot_connector.get_contact_associations(contact_id)
                if associations and len(associations) > 0:
                    company_id = associations[0]["id"]

            self.context["steps"]["resolve_hubspot"] = {
                "status": "success",
                "contact_id": contact_id,
                "company_id": company_id,
            }

            return {
                "contact_id": contact_id,
                "company_id": company_id,
                "prospect_email": prospect.email,
            }
        except Exception as e:
            logger.error(f"Error resolving HubSpot data: {e}")
            self.context["steps"]["resolve_hubspot"] = {"status": "failed", "error": str(e)}
            return None

    async def _search_email_context(self, prospect: Prospect) -> Optional[Dict[str, Any]]:
        """Search Gmail for existing email threads with prospect."""
        try:
            if not self.gmail_connector:
                logger.warning("Gmail connector not available")
                return None

            # Search for threads with this email
            query = f"from:{prospect.email}"
            threads = await self.gmail_connector.search_threads(query, max_results=3)

            if threads:
                thread_context = {
                    "thread_count": len(threads),
                    "threads": [],
                }

                # Get details of most recent thread
                for thread in threads[:1]:
                    thread_details = await self.gmail_connector.get_thread(thread["id"])
                    if thread_details:
                        thread_context["threads"].append({
                            "id": thread["id"],
                            "snippet": thread.get("snippet", ""),
                            "message_count": len(thread_details.get("messages", [])),
                        })

                self.context["steps"]["search_email"] = {
                    "status": "success",
                    "threads_found": len(threads),
                }
                return thread_context
            else:
                self.context["steps"]["search_email"] = {
                    "status": "success",
                    "threads_found": 0,
                }
                return None
        except Exception as e:
            logger.error(f"Error searching email context: {e}")
            self.context["steps"]["search_email"] = {"status": "failed", "error": str(e)}
            return None

    async def _get_available_slots(self) -> Optional[List[Dict[str, Any]]]:
        """Get available calendar slots."""
        try:
            if not self.calendar_connector:
                logger.warning("Calendar connector not available")
                return None

            slots = await self.calendar_connector.find_available_slots(
                duration_minutes=30,
                num_slots=3,
            )

            if slots:
                self.context["steps"]["calendar_availability"] = {
                    "status": "success",
                    "slots_found": len(slots),
                }
                return slots
            else:
                self.context["steps"]["calendar_availability"] = {
                    "status": "success",
                    "slots_found": 0,
                }
                return None
        except Exception as e:
            logger.error(f"Error getting available slots: {e}")
            self.context["steps"]["calendar_availability"] = {"status": "failed", "error": str(e)}
            return None

    async def _generate_message(
        self,
        prospect: Prospect,
        email_context: Optional[Dict[str, Any]],
    ) -> Optional[str]:
        """Generate prospecting message."""
        try:
            if self.prospecting_agent:
                message = await self.prospecting_agent.generate_message(
                    prospect=prospect,
                    context=email_context or {},
                    available_slots=self.context.get("available_slots", []),
                )
                self.context["steps"]["generate_message"] = {
                    "status": "success",
                    "message_length": len(message) if message else 0,
                }
                return message
            else:
                # Fallback message
                message = (
                    f"Hi {prospect.first_name},\n\n"
                    f"I noticed you're at {prospect.company}. "
                    f"Would love to chat about how we can help.\n\n"
                    f"Best regards"
                )
                return message
        except Exception as e:
            logger.error(f"Error generating message: {e}")
            self.context["steps"]["generate_message"] = {"status": "failed", "error": str(e)}
            return None

    async def _create_draft(self, prospect: Prospect, message: str) -> Optional[str]:
        """Create draft email (DRAFT_ONLY mode - NOT SENT)."""
        try:
            if not self.gmail_connector:
                logger.warning("Gmail connector not available, skipping draft creation")
                return None

            subject = f"Quick thought on {prospect.company}"
            draft_id = await self.gmail_connector.create_draft(
                to=prospect.email,
                subject=subject,
                body=message,
            )

            if draft_id:
                self.context["steps"]["create_draft"] = {
                    "status": "success",
                    "draft_id": draft_id,
                    "mode": "DRAFT_ONLY",
                }
                logger.info(f"Created draft {draft_id} (DRAFT_ONLY mode - not sent)")
                return draft_id
            else:
                self.context["steps"]["create_draft"] = {"status": "failed"}
                return None
        except Exception as e:
            logger.error(f"Error creating draft: {e}")
            self.context["steps"]["create_draft"] = {"status": "failed", "error": str(e)}
            return None

    async def _create_hubspot_task(
        self,
        prospect: Prospect,
        message: str,
        draft_id: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """Create HubSpot task and note."""
        try:
            if not self.hubspot_connector:
                logger.warning("HubSpot connector not available")
                return None

            hubspot_data = self.context.get("hubspot", {})
            contact_id = hubspot_data.get("contact_id")

            if not contact_id:
                logger.warning("No contact ID found, skipping task creation")
                return None

            # Create note with message
            note_body = f"Draft prospecting message created ({draft_id}):\n\n{message}"
            note_id = await self.hubspot_connector.create_note(contact_id, note_body)

            # Create follow-up task
            task_id = await self.hubspot_connector.create_task(
                contact_id=contact_id,
                title=f"Follow up with {prospect.first_name} ({prospect.company})",
                body=f"Draft ready for review. Check Gmail drafts for message. Draft ID: {draft_id}",
            )

            task_data = {
                "task_id": task_id,
                "note_id": note_id,
                "contact_id": contact_id,
                "draft_id": draft_id,
            }

            self.context["steps"]["create_hubspot_task"] = {
                "status": "success" if task_id else "partial",
                "task_id": task_id,
                "note_id": note_id,
            }

            return task_data
        except Exception as e:
            logger.error(f"Error creating HubSpot task: {e}")
            self.context["steps"]["create_hubspot_task"] = {"status": "failed", "error": str(e)}
            return None


# Singleton instance
_orchestrator_instance: Optional[ProspectingOrchestrator] = None


def get_orchestrator(
    prospecting_agent: Optional[ProspectingAgent] = None,
    nurturing_agent: Optional[NurturingAgent] = None,
    validation_agent: Optional[ValidationAgent] = None,
    gmail_connector: Optional[GmailConnector] = None,
    hubspot_connector: Optional[HubSpotConnector] = None,
    calendar_connector: Optional[CalendarConnector] = None,
) -> ProspectingOrchestrator:
    """Get or create orchestrator singleton."""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = ProspectingOrchestrator(
            prospecting_agent=prospecting_agent,
            nurturing_agent=nurturing_agent,
            validation_agent=validation_agent,
            gmail_connector=gmail_connector,
            hubspot_connector=hubspot_connector,
            calendar_connector=calendar_connector,
        )
    return _orchestrator_instance


def reset_orchestrator() -> None:
    """Reset orchestrator instance (for testing)."""
    global _orchestrator_instance
    _orchestrator_instance = None
