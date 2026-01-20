"""Specialized agents for formlead orchestration."""
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from src.logger import get_logger

logger = get_logger(__name__)


class ThreadReaderAgent:
    """Reads and summarizes Gmail threads for context."""

    async def read_thread(self, thread_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze thread and extract key context."""
        try:
            messages = thread_data.get("messages", [])
            if not messages:
                return {"status": "empty", "context": None}

            # Extract key information from thread
            first_message = messages[0]
            last_message = messages[-1]
            
            thread_summary = {
                "message_count": len(messages),
                "first_date": first_message.get("internalDate"),
                "last_date": last_message.get("internalDate"),
                "snippet": thread_data.get("snippet", ""),
                "key_context": self._extract_key_context(messages),
            }

            logger.info(f"Thread analysis: {len(messages)} messages, context extracted")
            return {
                "status": "success",
                "context": thread_summary,
            }
        except Exception as e:
            logger.error(f"Error reading thread: {e}")
            return {"status": "error", "context": None, "error": str(e)}

    def _extract_key_context(self, messages: List[Dict[str, Any]]) -> str:
        """Extract key information from messages."""
        context_items = []
        for msg in messages[-3:]:  # Last 3 messages
            snippet = msg.get("snippet", "")
            if snippet:
                context_items.append(snippet)
        
        return " | ".join(context_items) if context_items else "No context available"


class LongMemoryAgent:
    """Retrieves similar patterns from sent mail history."""

    def __init__(self, gmail_connector=None):
        """Initialize with optional Gmail connector for sent mail search."""
        self.gmail_connector = gmail_connector

    async def find_similar_patterns(
        self,
        prospect_company: str,
        prospect_title: Optional[str] = None,
        limit: int = 3,
    ) -> Dict[str, Any]:
        """Find similar past situations from sent mail."""
        try:
            patterns = []
            
            # If Gmail connector available, search sent mail for similar companies
            if self.gmail_connector:
                try:
                    # Search for similar industry/company outreach
                    query = f"in:sent {prospect_company}"
                    threads = await self.gmail_connector.search_threads(query, max_results=5)
                    
                    if threads:
                        patterns.append({
                            "pattern": f"Prior outreach to similar companies",
                            "success_rate": 0.35,
                            "approach": "Reference past successful approaches",
                            "thread_count": len(threads),
                        })
                except Exception as e:
                    logger.warning(f"Could not search sent mail: {e}")
            
            # Add default patterns as fallback
            if not patterns:
                patterns = [
                    {
                        "pattern": "Initial outreach to tech companies",
                        "success_rate": 0.35,
                        "approach": "Mention specific tech fit",
                    },
                    {
                        "pattern": "VP-level outreach",
                        "success_rate": 0.28,
                        "approach": "Executive briefing angle",
                    },
                ]

            relevant_patterns = patterns[:limit]

            logger.info(f"Found {len(relevant_patterns)} relevant patterns")
            return {
                "status": "success",
                "patterns": relevant_patterns,
                "abstraction_level": "high",  # No client leakage
            }
        except Exception as e:
            logger.error(f"Error finding patterns: {e}")
            return {"status": "error", "patterns": [], "error": str(e)}


class AssetHunterAgent:
    """Searches Google Drive for relevant assets with allowlist enforcement."""

    # Allowlist configuration
    ALLOWLIST = {
        "pesti_sales": {
            "root_id": "0ACIUuJIAAt4IUk9PVA",
            "include_prefixes": [
                "CHAINge Proposals",
                "CP Client Reports",
                "CP Proposals",
                "Manifest 2026",
            ],
            "exclude_prefixes": ["CP Closed"],
        },
        "charlie_pesti": {
            "root_id": "0AB_H1WFgMn8uUk9PVA",
            "include_all": True,
        },
    }
    
    def __init__(self, drive_connector=None):
        """Initialize with optional Drive connector."""
        self.drive_connector = drive_connector

    async def hunt_assets(
        self,
        prospect_company: str,
        max_results: int = 3,
        charlie_pesti_folder_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Search for relevant assets."""
        try:
            if charlie_pesti_folder_id:
                self.ALLOWLIST["charlie_pesti"]["root_id"] = charlie_pesti_folder_id

            assets = []

            # Use real Drive connector if available
            if self.drive_connector:
                try:
                    search_results = await self.drive_connector.search_assets(
                        query=prospect_company,
                        company_name=prospect_company,
                        max_results=max_results,
                    )
                    for result in search_results:
                        if self._validate_asset_in_allowlist(result):
                            assets.append(result)
                except Exception as e:
                    logger.warning(f"Drive search failed: {e}, using mock assets")

            # Fallback to mock assets if no results
            if not assets:
                mock_assets = [
                    {
                        "name": "CHAINge Proposals/TechCorp_Proposal_2026.pdf",
                        "folder": "pesti_sales",
                        "relevance": 0.85,
                        "webViewLink": "https://drive.google.com/file/d/mock/view",
                    },
                    {
                        "name": "CP Client Reports/Industry_Analysis_2026.pdf",
                        "folder": "pesti_sales",
                        "relevance": 0.72,
                        "webViewLink": "https://drive.google.com/file/d/mock2/view",
                    },
                ]
                for asset in mock_assets:
                    if self._validate_asset_in_allowlist(asset):
                        assets.append(asset)

            logger.info(f"Found {len(assets)} assets within allowlist")
            return {
                "status": "success",
                "assets": assets[:max_results],
                "allowlist_enforced": True,
            }
        except Exception as e:
            logger.error(f"Error hunting assets: {e}")
            return {"status": "error", "assets": [], "error": str(e)}

    def _validate_asset_in_allowlist(self, asset: Dict[str, Any]) -> bool:
        """Validate asset is within allowlist."""
        folder = asset.get("folder", "")
        name = asset.get("name", "")

        if folder not in self.ALLOWLIST:
            return False

        allowlist_entry = self.ALLOWLIST[folder]

        # If include_all, asset is allowed
        if allowlist_entry.get("include_all"):
            return True

        # Check include prefixes
        include_prefixes = allowlist_entry.get("include_prefixes", [])
        exclude_prefixes = allowlist_entry.get("exclude_prefixes", [])

        # Must match at least one include prefix
        matches_include = any(name.startswith(p) for p in include_prefixes)

        # Must not match any exclude prefix
        matches_exclude = any(name.startswith(p) for p in exclude_prefixes)

        return matches_include and not matches_exclude


class MeetingSlotAgent:
    """Proposes meeting slots using Calendar freebusy."""

    def __init__(self, calendar_connector=None):
        """Initialize with optional Calendar connector."""
        self.calendar_connector = calendar_connector

    async def propose_slots(
        self,
        num_slots: int = 3,
        duration_minutes: int = 30,
        max_days_out: int = 3,
    ) -> Dict[str, Any]:
        """Propose 2-3 meeting slots in next 1-3 business days."""
        try:
            slots = []
            
            # Use real Calendar connector if available
            if self.calendar_connector:
                try:
                    calendar_slots = await self.calendar_connector.get_available_slots(
                        num_slots=num_slots,
                        duration_minutes=duration_minutes,
                        max_days_ahead=max_days_out,
                    )
                    if calendar_slots:
                        for slot in calendar_slots[:num_slots]:
                            slots.append({
                                "start": slot.get("start"),
                                "end": slot.get("end"),
                                "display": slot.get("display", ""),
                            })
                except Exception as e:
                    logger.warning(f"Calendar lookup failed: {e}, using generated slots")
            
            # Fallback to generated slots
            if not slots:
                current_date = datetime.now(timezone.utc)
                business_days_checked = 0
                business_days_target = min(max_days_out, 3)

                while len(slots) < num_slots and business_days_checked < business_days_target * 2:
                    current_date += timedelta(days=1)

                    # Skip weekends
                    if current_date.weekday() >= 5:
                        continue

                    # Generate time slots for this day
                    for hour in [10, 14]:  # 10 AM and 2 PM
                        if len(slots) >= num_slots:
                            break

                        slot_start = current_date.replace(hour=hour, minute=0, second=0, microsecond=0)
                        slot_end = slot_start + timedelta(minutes=duration_minutes)
                        
                        # Format display string
                        display = slot_start.strftime("%A, %B %d at %I:%M %p") + " EST"

                        slots.append({
                            "start": slot_start.isoformat(),
                            "end": slot_end.isoformat(),
                            "display": display,
                            "day_offset": business_days_checked,
                        })

                    business_days_checked += 1

            logger.info(f"Proposed {len(slots)} meeting slots")
            return {
                "status": "success",
                "slots": slots[:num_slots],
                "default_duration_minutes": duration_minutes,
            }
        except Exception as e:
            logger.error(f"Error proposing slots: {e}")
            return {"status": "error", "slots": [], "error": str(e)}


class NextStepPlannerAgent:
    """Selects primary CTA based on prospect context."""

    async def plan_next_step(
        self,
        prospect_data: Dict[str, Any],
        prior_patterns: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Select primary CTA: book 30-minute working session."""
        try:
            # Always default to working session for formlead context
            cta = {
                "primary": "Schedule 30-minute working session",
                "urgency": "medium",  # Urgent but not needy
                "type": "meeting_booking",
                "slots_required": 3,
                "reasoning": "Form submission indicates active interest; working session allows deep discovery",
            }

            logger.info(f"Selected CTA: {cta['primary']}")
            return {
                "status": "success",
                "cta": cta,
            }
        except Exception as e:
            logger.error(f"Error planning next step: {e}")
            return {"status": "error", "cta": None, "error": str(e)}


class DraftWriterAgent:
    """Writes Gmail draft using voice profile and DraftGenerator."""

    def __init__(self, draft_generator=None):
        """Initialize with optional DraftGenerator."""
        self.draft_generator = draft_generator

    async def write_draft(
        self,
        prospect_data: Dict[str, Any],
        meeting_slots: List[Dict[str, Any]],
        drive_asset: Optional[Dict[str, Any]] = None,
        voice_profile: Optional[Dict[str, Any]] = None,
        thread_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create Gmail draft with voice profile (no em-dashes)."""
        try:
            # Use DraftGenerator if available (OpenAI-powered)
            if self.draft_generator:
                try:
                    from src.voice_profile import get_voice_profile, VoiceProfile
                    
                    # Get voice profile object
                    vp = None
                    if voice_profile and isinstance(voice_profile, VoiceProfile):
                        vp = voice_profile
                    else:
                        vp = get_voice_profile()
                    
                    asset_link = drive_asset.get("webViewLink") if drive_asset else None
                    
                    result = await self.draft_generator.generate_draft(
                        prospect_email=prospect_data.get("email", ""),
                        prospect_name=prospect_data.get("first_name", ""),
                        company_name=prospect_data.get("company", ""),
                        thread_context=thread_context,
                        meeting_slots=meeting_slots,
                        asset_link=asset_link,
                        voice_profile=vp,
                    )
                    
                    if result.get("subject") and result.get("body"):
                        logger.info("Draft created using OpenAI DraftGenerator")
                        return {
                            "status": "success",
                            "subject": result["subject"],
                            "body": result["body"],
                            "voice_profile_used": True,
                            "ai_generated": True,
                        }
                except Exception as e:
                    logger.warning(f"DraftGenerator failed: {e}, using template")
            
            # Fallback to template-based draft
            if not voice_profile:
                logger.warning("Voice profile missing; using default formal tone")
                voice_profile = {"tone": "professional", "patterns": []}

            # Build draft body
            first_name = prospect_data.get("first_name", "there")
            greeting = f"Hi {first_name},"
            
            body_parts = [
                greeting,
                "",
                "Thanks for reaching out via the form. I'd like to explore how we might work together.",
                "",
                "I have a few time slots available for a 30-minute working session over the next couple of days:",
                "",
            ]

            # Add meeting slots with display format
            for i, slot in enumerate(meeting_slots[:3], 1):
                display = slot.get("display", "")
                if display:
                    body_parts.append(f"  {i}. {display}")
                else:
                    start = slot.get("start", "")
                    if start:
                        try:
                            start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                            formatted_time = start_dt.strftime("%A, %B %d at %I:%M %p") + " EST"
                            body_parts.append(f"  {i}. {formatted_time}")
                        except:
                            body_parts.append(f"  {i}. {start}")

            body_parts.extend([
                "",
                "During our time, we can discuss your current situation and see if there's a good fit.",
            ])

            # Add drive asset link if available
            if drive_asset:
                asset_name = drive_asset.get("name", "document")
                asset_link = drive_asset.get("webViewLink", "")
                if asset_link:
                    body_parts.extend([
                        "",
                        f"I'm also sharing a relevant resource: {asset_name}",
                        f"Link: {asset_link}",
                    ])
                else:
                    body_parts.extend([
                        "",
                        f"I'm also attaching a relevant resource: {asset_name}",
                    ])

            body_parts.extend([
                "",
                "What works best for you?",
                "",
                "Best,",
                "",
                "P.S. Feel free to reply with your preference or suggest a different time.",
            ])

            draft_body = "\n".join(body_parts)

            # Remove em-dashes (prohibited in voice profile)
            draft_body = draft_body.replace("—", "-")

            subject = f"Let's explore working together - {prospect_data.get('company', 'opportunity')}"

            logger.info("Draft created using template with voice profile")
            return {
                "status": "success",
                "subject": subject,
                "body": draft_body,
                "voice_profile_used": True,
                "ai_generated": False,
            }
        except Exception as e:
            logger.error(f"Error writing draft: {e}")
            return {"status": "error", "subject": None, "body": None, "error": str(e)}
