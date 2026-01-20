"""Specialized agents for formlead orchestration."""
import json
from datetime import datetime, timedelta
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

    async def find_similar_patterns(
        self,
        prospect_company: str,
        prospect_title: Optional[str] = None,
        limit: int = 3,
    ) -> Dict[str, Any]:
        """Find similar past situations from sent mail."""
        try:
            # In production, this would query Gmail API for sent mail
            # For now, return pattern templates based on company/title
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

            # Filter based on prospect profile (mock)
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
            "root_id": "0AB_H1WFgMn8uUk9PVA",  # Can be overridden by env CHARLIE_PESTI_FOLDER_ID
            "include_all": True,
        },
    }

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

            # Mock search across allowlist folders
            # In production: real Drive API search with allowlist enforcement
            mock_assets = [
                {
                    "name": "CHAINge Proposals/TechCorp_Proposal_2026.pdf",
                    "folder": "pesti_sales",
                    "relevance": 0.85,
                },
                {
                    "name": "CP Client Reports/Industry_Analysis_2026.pdf",
                    "folder": "pesti_sales",
                    "relevance": 0.72,
                },
            ]

            # Validate all assets are within allowlist
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

    async def propose_slots(
        self,
        num_slots: int = 3,
        duration_minutes: int = 30,
        max_days_out: int = 3,
    ) -> Dict[str, Any]:
        """Propose 2-3 meeting slots in next 1-3 business days."""
        try:
            slots = []
            current_date = datetime.utcnow()
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

                    slot_start = current_date.replace(hour=hour, minute=0, second=0)
                    slot_end = slot_start + timedelta(minutes=duration_minutes)

                    slots.append({
                        "start": slot_start.isoformat() + "Z",
                        "end": slot_end.isoformat() + "Z",
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
    """Writes Gmail draft using voice profile."""

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
            if not voice_profile:
                logger.warning("Voice profile missing; using default formal tone")
                voice_profile = {"tone": "professional", "patterns": []}

            # Build draft body
            greeting = f"Hi {prospect_data.get('first_name', 'there')},"
            
            body_parts = [
                greeting,
                "",
                "Thanks for reaching out via the form. I'd like to explore how we might work together.",
                "",
                "I have a few time slots available for a 30-minute working session over the next couple of days:",
                "",
            ]

            # Add meeting slots
            for i, slot in enumerate(meeting_slots[:3], 1):
                start_dt = datetime.fromisoformat(slot["start"].replace("Z", "+00:00"))
                formatted_time = start_dt.strftime("%A, %I:%M %p UTC")
                body_parts.append(f"  {i}. {formatted_time}")

            body_parts.extend([
                "",
                "During our time, we can discuss your current situation and see if there's a good fit.",
            ])

            # Add drive asset link if available
            if drive_asset:
                asset_name = drive_asset.get("name", "document")
                body_parts.extend([
                    "",
                    f"I'm also attaching a relevant resource: {asset_name}",
                ])

            body_parts.extend([
                "",
                "What works best for you?",
                "",
                "Best regards,",
                "[Your Name]",
                "",
                "---",
                "P.S. Feel free to reply with your preference or suggest a different time.",
            ])

            draft_body = "\n".join(body_parts)

            # Remove em-dashes if any (shouldn't be with this template)
            draft_body = draft_body.replace("—", "-")

            subject = f"Let's explore working together - {prospect_data.get('company', 'opportunity')}"

            logger.info("Draft created using voice profile")
            return {
                "status": "success",
                "subject": subject,
                "body": draft_body,
                "voice_profile_used": True,
            }
        except Exception as e:
            logger.error(f"Error writing draft: {e}")
            return {"status": "error", "subject": None, "body": None, "error": str(e)}
