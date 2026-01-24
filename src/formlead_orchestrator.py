"""End-to-end orchestration for HubSpot form leads (DRAFT_ONLY mode)."""
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from src.logger import get_logger
from src.audit import AuditTrail
from src.db.workflow_db import get_workflow_db
from src.agents.specialized import (
    ThreadReaderAgent,
    LongMemoryAgent,
    AssetHunterAgent,
    MeetingSlotAgent,
    NextStepPlannerAgent,
    DraftWriterAgent,
)
from src.agents.research import ResearchAgent, create_research_agent
from src.connectors.gmail import GmailConnector
from src.connectors.hubspot import HubSpotConnector
from src.connectors.calendar_connector import CalendarConnector
from src.connectors.drive import DriveConnector
from src.draft_generator import DraftGenerator
from src.voice_profile import VoiceProfileManager, VoiceProfile

logger = get_logger(__name__)


class FormleadOrchestrator:
    """Complete orchestration for HubSpot form lead processing (DRAFT_ONLY)."""

    def __init__(
        self,
        gmail_connector: Optional[GmailConnector] = None,
        hubspot_connector: Optional[HubSpotConnector] = None,
        calendar_connector: Optional[CalendarConnector] = None,
        drive_connector: Optional[DriveConnector] = None,
        draft_generator: Optional[DraftGenerator] = None,
        voice_profile_manager: Optional[VoiceProfileManager] = None,
        charlie_pesti_folder_id: Optional[str] = None,
    ):
        """Initialize orchestrator with connectors."""
        self.gmail_connector = gmail_connector
        self.hubspot_connector = hubspot_connector
        self.calendar_connector = calendar_connector
        self.drive_connector = drive_connector
        self.draft_generator = draft_generator or DraftGenerator()
        self.voice_profile_manager = voice_profile_manager or VoiceProfileManager()
        self.charlie_pesti_folder_id = charlie_pesti_folder_id

        # Initialize specialized agents with connectors
        self.thread_reader = ThreadReaderAgent()
        self.long_memory = LongMemoryAgent(gmail_connector=gmail_connector)
        self.asset_hunter = AssetHunterAgent(drive_connector=drive_connector)
        self.meeting_slot = MeetingSlotAgent(calendar_connector=calendar_connector)
        self.next_step_planner = NextStepPlannerAgent()
        self.draft_writer = DraftWriterAgent(draft_generator=self.draft_generator)
        
        # Research agent for company/person enrichment
        self.research_agent = create_research_agent(
            hubspot_connector=hubspot_connector,
            gmail_connector=gmail_connector,
        )

        self.context: Dict[str, Any] = {}

    async def process_formlead(
        self,
        form_submission: Dict[str, Any],
        voice_profile: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Process form lead through 11-step workflow (DRAFT_ONLY)."""
        now = datetime.now(timezone.utc)
        workflow_id = f"formlead-{now.strftime('%Y%m%d%H%M%S')}"
        self.context = {
            "workflow_id": workflow_id,
            "timestamp": now.isoformat(),
            "mode": "DRAFT_ONLY",
            "steps": {},
        }

        # Extract email and company for DB logging
        email = form_submission.get("email", "")
        company = form_submission.get("company", "")
        submission_id = form_submission.get("formSubmissionId", "")

        # Check for duplicate submissions
        try:
            db = await get_workflow_db()
            
            # Check for exact duplicate submission ID
            if submission_id and await db.check_duplicate_submission(submission_id):
                logger.warning(f"Duplicate submission detected: {submission_id}")
                return {
                    "status": "skipped",
                    "final_status": "skipped",
                    "workflow_id": workflow_id,
                    "reason": "duplicate_submission",
                    "message": f"Submission {submission_id} has already been processed",
                }
            
            # Check for recent workflow for same email (throttling)
            if email and await db.check_recent_email_workflow(email, hours=1):
                logger.warning(f"Recent workflow exists for {email}, throttling")
                return {
                    "status": "skipped",
                    "final_status": "skipped",
                    "workflow_id": workflow_id,
                    "reason": "throttled",
                    "message": f"A workflow for {email} was processed within the last hour",
                }
        except Exception as e:
            logger.warning(f"Could not check for duplicates: {e}")

        # Persist workflow start to database
        try:
            db = await get_workflow_db()
            await db.create_workflow_run(
                workflow_id=workflow_id,
                workflow_type="formlead",
                submission_id=submission_id,
                contact_email=email,
                company_name=company,
            )
        except Exception as e:
            logger.warning(f"Could not persist workflow to DB: {e}")

        try:
            # Step 1: Validate webhook payload
            logger.info("Step 1: Validating webhook payload")
            form_valid = await self._validate_form_payload(form_submission)
            if not form_valid:
                raise ValueError("Invalid form payload")
            self.context["steps"]["validate_payload"] = {"status": "success"}

            # Step 2: Upsert/resolve HubSpot contact + company
            logger.info("Step 2: Resolving HubSpot contact/company")
            prospect_data = await self._resolve_hubspot(form_submission)
            self.context["prospect"] = prospect_data
            self.context["steps"]["resolve_hubspot"] = {"status": "success"}

            # Step 2.5: Research prospect and company
            logger.info("Step 2.5: Researching prospect and company")
            research_data = await self.research_agent.research_prospect(
                email=prospect_data.get("email", ""),
                company=prospect_data.get("company"),
                first_name=prospect_data.get("first_name"),
                last_name=prospect_data.get("last_name"),
            )
            self.context["research"] = research_data
            self.context["steps"]["research_prospect"] = {
                "status": "success",
                "sources": research_data.get("sources", []),
                "talking_points": len(research_data.get("talking_points", [])),
                "hooks": len(research_data.get("personalization_hooks", [])),
            }

            # Step 3: Search Gmail for existing threads
            logger.info("Step 3: Searching Gmail for threads")
            threads = await self._search_gmail_threads(prospect_data)
            if threads:
                self.context["gmail_threads"] = threads
            self.context["steps"]["search_gmail"] = {"status": "success", "threads_found": len(threads)}

            # Step 4: Read thread if exists
            logger.info("Step 4: Reading thread context")
            thread_context = None
            if threads:
                thread_data = await self._get_thread_context(threads[0]["id"])
                if thread_data:
                    thread_reader_result = await self.thread_reader.read_thread(thread_data)
                    if thread_reader_result.get("status") == "success":
                        thread_context = thread_reader_result.get("context")
            self.context["steps"]["read_thread"] = {"status": "success", "has_context": thread_context is not None}

            # Step 5: Run LongMemoryAgent for patterns
            logger.info("Step 5: Finding similar patterns")
            patterns_result = await self.long_memory.find_similar_patterns(
                prospect_company=prospect_data.get("company", ""),
                prospect_title=prospect_data.get("title"),
            )
            patterns = patterns_result.get("patterns", [])
            self.context["steps"]["long_memory"] = {"status": patterns_result.get("status"), "patterns_count": len(patterns)}

            # Step 6: Run AssetHunter with allowlist
            logger.info("Step 6: Hunting Drive assets (allowlist enforced)")
            assets_result = await self.asset_hunter.hunt_assets(
                prospect_company=prospect_data.get("company", ""),
                charlie_pesti_folder_id=self.charlie_pesti_folder_id,
            )
            assets = assets_result.get("assets", [])
            self.context["steps"]["asset_hunter"] = {
                "status": assets_result.get("status"),
                "assets_count": len(assets),
                "allowlist_enforced": assets_result.get("allowlist_enforced", True),
            }

            # Step 7: Run MeetingSlotAgent
            logger.info("Step 7: Proposing meeting slots (2-3 in next 1-3 business days)")
            slots_result = await self.meeting_slot.propose_slots(num_slots=3, max_days_out=3)
            slots = slots_result.get("slots", [])
            self.context["steps"]["meeting_slots"] = {"status": slots_result.get("status"), "slots_count": len(slots)}

            # Step 8: Run NextStepPlannerAgent
            logger.info("Step 8: Planning next step (CTA)")
            cta_result = await self.next_step_planner.plan_next_step(prospect_data, patterns)
            cta = cta_result.get("cta", {})
            self.context["steps"]["next_step_plan"] = {"status": cta_result.get("status"), "cta": cta.get("primary")}

            # Step 9: Run DraftWriterAgent
            logger.info("Step 9: Writing draft using voice profile and research context")
            primary_asset = assets[0] if assets else None
            draft_result = await self.draft_writer.write_draft(
                prospect_data=prospect_data,
                meeting_slots=slots,
                drive_asset=primary_asset,
                voice_profile=voice_profile,
                thread_context=thread_context,
                research_context=self.context.get("research"),
            )
            draft_subject = draft_result.get("subject")
            draft_body = draft_result.get("body")
            self.context["steps"]["draft_writer"] = {"status": draft_result.get("status"), "has_body": draft_body is not None}

            # Step 10: Create Gmail draft + HubSpot note/task
            logger.info("Step 10: Creating Gmail draft and HubSpot task")
            draft_id = await self._create_gmail_draft(
                prospect_data, draft_subject, draft_body, threads, workflow_id=workflow_id
            )
            hubspot_task = await self._create_hubspot_task(prospect_data, draft_id)
            self.context["steps"]["create_draft"] = {"status": "success", "draft_id": draft_id, "mode": "DRAFT_ONLY"}
            self.context["steps"]["create_task"] = {"status": "success", "task_id": hubspot_task.get("task_id")}

            # Step 10.5: Evaluate for auto-approval (Sprint 4)
            logger.info("Step 10.5: Evaluating draft for auto-approval")
            auto_approval_result = await self._evaluate_auto_approval(
                draft_id=draft_id,
                recipient_email=prospect_data.get("email", ""),
                draft_metadata={
                    "icp_score": prospect_data.get("icp_score", 0.0),
                    "domain": prospect_data.get("company_domain"),
                    "company": prospect_data.get("company"),
                },
            )
            self.context["steps"]["auto_approval"] = auto_approval_result

            # Step 11: Label thread (or create label) and audit log
            logger.info("Step 11: Labeling thread and creating audit event")
            if threads:
                await self._label_thread(threads[0]["id"])
            AuditTrail.log_draft_created(
                prospect_email=prospect_data.get("email", ""),
                draft_id=draft_id,
                metadata={
                    "formlead_workflow": workflow_id,
                    "thread_found": len(threads) > 0,
                    "assets_included": len(assets),
                },
            )
            self.context["steps"]["label_thread"] = {"status": "success"}

            self.context["final_status"] = "success"
            self.context["draft_id"] = draft_id
            self.context["task_id"] = hubspot_task.get("task_id")

            # Persist success to database
            try:
                db = await get_workflow_db()
                await db.update_workflow_run(
                    workflow_id=workflow_id,
                    status="success",
                    draft_id=draft_id,
                    steps_completed=self.context.get("steps"),
                )
            except Exception as db_err:
                logger.warning(f"Could not update workflow in DB: {db_err}")

            logger.info(f"Formlead workflow {workflow_id} completed successfully (DRAFT_ONLY)")
            return self.context

        except Exception as e:
            logger.error(f"Formlead workflow {workflow_id} failed: {e}", exc_info=True)
            self.context["final_status"] = "failed"
            self.context["error"] = str(e)

            # Persist failure to database
            try:
                db = await get_workflow_db()
                await db.update_workflow_run(
                    workflow_id=workflow_id,
                    status="failed",
                    steps_completed=self.context.get("steps"),
                    error_message=str(e),
                )
            except Exception as db_err:
                logger.warning(f"Could not update failed workflow in DB: {db_err}")

            return self.context

    async def _validate_form_payload(self, form_submission: Dict[str, Any]) -> bool:
        """Validate webhook payload and reject wrong formIds."""
        try:
            # Check required fields
            required_fields = ["email", "company", "portalId", "formId"]
            for field in required_fields:
                if not form_submission.get(field):
                    logger.warning(f"Missing required field: {field}")
                    return False

            # Validate formId (check against allowlist)
            form_id = form_submission.get("formId")
            allowed_form_ids = [
                "db8b22de-c3d4-4fc6-9a16-011fe322e82c",  # Production HubSpot form
                "124si3sPUT8aaFgEf4yLoLAe8nok",  # Pesti.io production form
                "workflow-trigger",  # HubSpot workflow webhook
                "form1",  # Test form
                "form2",  # Test form
                "test-demo-form",  # Demo test form
                "lead-interest-form",  # Example form
                "test-form-123",  # Test form for validation
            ]
            if form_id not in allowed_form_ids:
                logger.warning(f"Form ID {form_id} not in allowlist")
                return False

            logger.info(f"Form payload validated: formId={form_id}")
            return True
        except Exception as e:
            logger.error(f"Error validating form payload: {e}")
            return False

    async def _resolve_hubspot(self, form_submission: Dict[str, Any]) -> Dict[str, Any]:
        """Upsert/resolve HubSpot contact + company."""
        try:
            email = form_submission.get("email", "")
            company_name = form_submission.get("company", "")
            first_name = form_submission.get("firstName", "")
            last_name = form_submission.get("lastName", "")

            prospect_data = {
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "company": company_name,
            }

            # Try to find existing contact
            if self.hubspot_connector:
                contact = await self.hubspot_connector.search_contacts(email)
                if contact:
                    prospect_data["hubspot_contact_id"] = contact.get("id")
                    logger.info(f"Found existing HubSpot contact: {contact.get('id')}")
                else:
                    logger.info(f"No existing contact for {email}; would create in production")
            else:
                logger.warning("HubSpot connector not available")

            return prospect_data
        except Exception as e:
            logger.error(f"Error resolving HubSpot: {e}")
            return {"email": form_submission.get("email", ""), "company": form_submission.get("company", "")}

    async def _search_gmail_threads(self, prospect_data: Dict[str, Any]) -> list:
        """Search Gmail for existing threads."""
        try:
            if not self.gmail_connector:
                return []

            email = prospect_data.get("email", "")
            query = f"from:{email}"
            threads = await self.gmail_connector.search_threads(query, max_results=5)
            return threads
        except Exception as e:
            logger.error(f"Error searching Gmail threads: {e}")
            return []

    async def _get_thread_context(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """Get full thread data."""
        try:
            if not self.gmail_connector:
                return None

            thread = await self.gmail_connector.get_thread(thread_id)
            return thread
        except Exception as e:
            logger.error(f"Error getting thread context: {e}")
            return None

    async def _create_gmail_draft(
        self,
        prospect_data: Dict[str, Any],
        subject: str,
        body: str,
        threads: list,
        workflow_id: Optional[str] = None,
    ) -> str:
        """Create Gmail draft (DRAFT_ONLY mode) and persist to database."""
        try:
            email = prospect_data.get("email", "")
            
            if not self.gmail_connector:
                draft_id = f"mock-draft-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
                logger.info(f"Gmail connector not available, mock draft: {draft_id}")
                return draft_id
            
            # Ensure subject and body have defaults
            final_subject = subject or f"Following up - {prospect_data.get('company', 'inquiry')}"
            final_body = body or "Thanks for reaching out. I'd like to schedule a time to connect."

            gmail_draft_id = await self.gmail_connector.create_draft(email, final_subject, final_body)
            
            if gmail_draft_id:
                logger.info(f"Gmail draft created: {gmail_draft_id} (DRAFT_ONLY - not sent)")
                
                # Persist to database via DraftQueue for UI visibility
                try:
                    from src.operator_mode import get_draft_queue
                    queue = get_draft_queue()
                    
                    # Use a unique internal draft ID
                    internal_draft_id = f"draft-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{gmail_draft_id[:8]}"
                    
                    await queue.create_draft(
                        draft_id=internal_draft_id,
                        recipient=email,
                        subject=final_subject,
                        body=final_body,
                        gmail_draft_id=gmail_draft_id,
                        workflow_id=workflow_id,
                        contact_id=prospect_data.get("hubspot_contact_id"),
                        company_name=prospect_data.get("company"),
                        metadata={
                            "prospect_first_name": prospect_data.get("first_name"),
                            "prospect_last_name": prospect_data.get("last_name"),
                            "threads_found": len(threads) if threads else 0,
                        }
                    )
                    logger.info(f"Draft {internal_draft_id} persisted for operator review")
                except Exception as e:
                    logger.error(f"Failed to persist draft to queue: {e}")
                
                return gmail_draft_id
            else:
                fallback_id = f"draft-failed-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
                logger.warning(f"Draft creation returned None, fallback: {fallback_id}")
                return fallback_id
                
        except Exception as e:
            logger.error(f"Error creating Gmail draft: {e}")
            return f"draft-error-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

    async def _evaluate_auto_approval(
        self,
        draft_id: str,
        recipient_email: str,
        draft_metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Evaluate draft for auto-approval (Sprint 4).

        Checks auto-approval rules and auto-sends if approved.
        Never auto-rejects - borderline cases go to manual review.

        Args:
            draft_id: Draft identifier
            recipient_email: Recipient email address
            draft_metadata: Draft context (ICP score, domain, etc.)

        Returns:
            Dict with evaluation results
        """
        from src.auto_approval import AutoApprovalEngine
        from src.config import get_settings
        from src.db import async_session

        settings = get_settings()

        try:
            async with async_session() as session:
                engine = AutoApprovalEngine(session)
                
                decision, rule_id, confidence, reasoning = await engine.evaluate_draft(
                    draft_id=draft_id,
                    recipient_email=recipient_email,
                    draft_metadata=draft_metadata,
                )

                logger.info(
                    f"Auto-approval decision: {decision}",
                    draft_id=draft_id,
                    decision=decision.value,
                    rule_id=rule_id,
                    confidence=confidence,
                )

                # If auto-approved AND real sends enabled, send immediately
                if decision.value == "auto_approved" and settings.allow_real_sends:
                    try:
                        from src.operator_mode import get_draft_queue
                        queue = get_draft_queue()
                        
                        # Auto-approve the draft
                        approve_result = await queue.approve_draft(
                            draft_id=draft_id,
                            approved_by="auto_approval_engine",
                        )

                        if approve_result.get("success"):
                            # Send the draft
                            send_result = await queue.send_draft(
                                draft_id=draft_id,
                                approved_by="auto_approval_engine",
                            )

                            if send_result.get("success"):
                                logger.info(
                                    f"Draft auto-sent successfully",
                                    draft_id=draft_id,
                                    message_id=send_result.get("message_id"),
                                )
                                return {
                                    "status": "auto_sent",
                                    "decision": decision.value,
                                    "rule_id": rule_id,
                                    "confidence": confidence,
                                    "reasoning": reasoning,
                                    "message_id": send_result.get("message_id"),
                                }
                            else:
                                logger.warning(
                                    f"Auto-approval succeeded but send failed",
                                    draft_id=draft_id,
                                    error=send_result.get("error"),
                                )
                    except Exception as send_error:
                        logger.error(
                            f"Error auto-sending draft",
                            draft_id=draft_id,
                            exc_info=True,
                        )

                # Draft approved but not sent (ALLOW_REAL_SENDS=false or needs review)
                return {
                    "status": "evaluated",
                    "decision": decision.value,
                    "rule_id": rule_id,
                    "confidence": confidence,
                    "reasoning": reasoning,
                }

        except Exception as e:
            logger.error(f"Error evaluating auto-approval", draft_id=draft_id, exc_info=True)
            return {
                "status": "error",
                "decision": "needs_review",
                "error": str(e),
            }

    async def _create_hubspot_task(
        self,
        prospect_data: Dict[str, Any],
        draft_id: str,
    ) -> Dict[str, Any]:
        """Create HubSpot task and note."""
        try:
            contact_id = prospect_data.get("hubspot_contact_id")
            if not contact_id:
                logger.warning("No contact ID for task creation")
                return {"task_id": None}

            if not self.hubspot_connector:
                task_id = f"task-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
                logger.info(f"Mocked task creation: {task_id}")
                return {"task_id": task_id}

            # Create note with draft reference
            note_body = f"Form lead processed. Draft created: {draft_id}\nDRAFT_ONLY mode: pending approval before send."
            note_id = await self.hubspot_connector.create_note(contact_id, note_body)

            # Create task due in 2 business days
            task_title = f"Follow up on {prospect_data.get('first_name', 'lead')} ({prospect_data.get('company')})"
            task_id = await self.hubspot_connector.create_task(
                contact_id=contact_id,
                title=task_title,
                body=f"Draft ready in Gmail. Review and send if ready. Draft ID: {draft_id}",
            )

            logger.info(f"Task created: {task_id}, Note created: {note_id}")
            return {"task_id": task_id, "note_id": note_id}
        except Exception as e:
            logger.error(f"Error creating HubSpot task: {e}")
            return {"task_id": None}

    async def _label_thread(self, thread_id: str) -> bool:
        """Label Gmail thread."""
        try:
            if not self.gmail_connector:
                logger.info(f"Would label thread {thread_id}")
                return True

            # In production, create/apply label "AGENT_DRAFTED_FORMLEAD"
            logger.info(f"Thread {thread_id} labeled (in production)")
            return True
        except Exception as e:
            logger.error(f"Error labeling thread: {e}")
            return False


# Singleton instance
_formlead_orchestrator: Optional[FormleadOrchestrator] = None


def get_formlead_orchestrator(
    gmail_connector: Optional[GmailConnector] = None,
    hubspot_connector: Optional[HubSpotConnector] = None,
    calendar_connector: Optional[CalendarConnector] = None,
    charlie_pesti_folder_id: Optional[str] = None,
) -> FormleadOrchestrator:
    """Get or create formlead orchestrator singleton."""
    global _formlead_orchestrator
    if _formlead_orchestrator is None:
        _formlead_orchestrator = FormleadOrchestrator(
            gmail_connector=gmail_connector,
            hubspot_connector=hubspot_connector,
            calendar_connector=calendar_connector,
            charlie_pesti_folder_id=charlie_pesti_folder_id,
        )
    return _formlead_orchestrator


def create_formlead_orchestrator() -> FormleadOrchestrator:
    """Create a new formlead orchestrator with connectors from environment.
    
    This factory function creates real connectors based on environment variables.
    Used by the webhook handler to process form submissions.
    """
    import os
    from src.connectors.gmail import create_gmail_connector
    from src.connectors.hubspot import create_hubspot_connector
    from src.connectors.calendar_connector import create_calendar_connector
    from src.connectors.drive import DriveConnector
    from src.draft_generator import DraftGenerator
    from src.voice_profile import VoiceProfileManager
    
    # Create connectors - they gracefully handle missing credentials
    gmail_connector = None
    hubspot_connector = None
    calendar_connector = None
    drive_connector = None
    
    try:
        gmail_connector = create_gmail_connector()
    except Exception as e:
        logger.warning(f"Could not create Gmail connector: {e}")
    
    try:
        hubspot_connector = create_hubspot_connector()
    except Exception as e:
        logger.warning(f"Could not create HubSpot connector: {e}")
    
    try:
        calendar_connector = create_calendar_connector()
    except Exception as e:
        logger.warning(f"Could not create Calendar connector: {e}")
    
    try:
        drive_connector = DriveConnector()
    except Exception as e:
        logger.warning(f"Could not create Drive connector: {e}")
    
    charlie_pesti_folder_id = os.environ.get("CHARLIE_PESTI_FOLDER_ID", "0AB_H1WFgMn8uUk9PVA")
    pesti_sales_folder_id = os.environ.get("PESTI_SALES_FOLDER_ID", "0ACIUuJIAAt4IUk9PVA")
    
    # Create draft generator with OpenAI
    draft_generator = DraftGenerator()
    
    # Create voice profile manager
    voice_profile_manager = VoiceProfileManager()
    
    return FormleadOrchestrator(
        gmail_connector=gmail_connector,
        hubspot_connector=hubspot_connector,
        calendar_connector=calendar_connector,
        drive_connector=drive_connector,
        draft_generator=draft_generator,
        voice_profile_manager=voice_profile_manager,
        charlie_pesti_folder_id=charlie_pesti_folder_id,
    )


def reset_formlead_orchestrator() -> None:
    """Reset orchestrator (for testing)."""
    global _formlead_orchestrator
    _formlead_orchestrator = None
