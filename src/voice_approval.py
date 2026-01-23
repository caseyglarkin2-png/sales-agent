"""Voice-enabled approval interface - Jarvis-style human-in-the-loop.

This module provides voice interaction for reviewing and approving
agent outputs (email drafts, campaigns, etc.).

INTEGRATED with src/operator_mode.py for actual draft management.
"""
import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

from openai import AsyncOpenAI
from pydantic import BaseModel

from src.logger import get_logger

logger = get_logger(__name__)


class ApprovalAction(str, Enum):
    """Actions that can be taken on items pending approval."""
    APPROVE = "approve"
    REJECT = "reject"
    EDIT = "edit"
    SKIP = "skip"
    REQUEST_INFO = "request_info"
    APPROVE_ALL = "approve_all"
    REJECT_ALL = "reject_all"


class VoiceCommand(BaseModel):
    """Parsed voice command."""
    action: ApprovalAction
    target_id: Optional[str] = None
    reason: Optional[str] = None
    edits: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = {}


class ApprovalItem(BaseModel):
    """Item pending approval."""
    id: str
    type: str  # email_draft, campaign, outreach, etc.
    title: str
    content: Dict[str, Any]
    context: Dict[str, Any]
    created_at: str
    agent_source: str  # which agent created this
    priority: str = "normal"  # low, normal, high, urgent


class VoiceApprovalInterface:
    """Jarvis-style voice interface for approving agent outputs."""
    
    def __init__(self, openai_api_key: Optional[str] = None):
        """Initialize voice approval interface."""
        api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key required for voice interface")
        
        self.client = AsyncOpenAI(api_key=api_key)
        self.pending_items: Dict[str, ApprovalItem] = {}
        self.current_item: Optional[ApprovalItem] = None
        self.conversation_history: List[Dict[str, str]] = []
        
        logger.info("Voice approval interface initialized")
    
    async def process_voice_input(
        self,
        audio_data: Optional[bytes] = None,
        text_input: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process voice or text input and return response with action.
        
        Args:
            audio_data: Raw audio bytes (will be transcribed)
            text_input: Direct text input (alternative to audio)
            
        Returns:
            Response dict with:
            - spoken_response: Text to be spoken back
            - action_taken: What action was performed
            - next_item: Next item to review (if any)
            - status: Current approval queue status
        """
        # Transcribe audio if provided
        if audio_data:
            transcription = await self._transcribe_audio(audio_data)
            logger.info(f"Transcribed: {transcription}")
        elif text_input:
            transcription = text_input
        else:
            return {"error": "No input provided"}
        
        # Parse command from transcription
        command = await self._parse_voice_command(transcription)
        
        # Execute command
        result = await self._execute_command(command)
        
        # Generate spoken response
        response = await self._generate_response(command, result)
        
        # Update conversation history
        self.conversation_history.append({
            "timestamp": datetime.now().isoformat(),
            "user": transcription,
            "jarvis": response["spoken_response"],
            "action": result.get("action", "none")
        })
        
        return response
    
    async def _transcribe_audio(self, audio_data: bytes) -> str:
        """Transcribe audio using OpenAI Whisper."""
        try:
            # Save audio temporarily
            temp_file = f"/tmp/voice_input_{datetime.now().timestamp()}.mp3"
            with open(temp_file, "wb") as f:
                f.write(audio_data)
            
            # Transcribe
            with open(temp_file, "rb") as audio_file:
                transcription = await self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="en"
                )
            
            # Cleanup
            os.remove(temp_file)
            
            return transcription.text
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            raise
    
    async def _parse_voice_command(self, text: str) -> VoiceCommand:
        """Parse natural language command using GPT-4.
        
        Understands commands like:
        - "Approve this email"
        - "Reject and tell me why"
        - "Edit the subject line to be more casual"
        - "Show me the next one"
        - "Approve all the drafts for Bristol Myers Squibb"
        """
        context = self._build_command_context()
        
        prompt = f"""You are Jarvis, an AI assistant parsing voice commands for approval workflows.

Current Context:
{context}

User said: "{text}"

Parse this into a structured command. Return JSON:
{{
  "action": "approve|reject|edit|skip|request_info|approve_all|reject_all",
  "target_id": "specific item ID if mentioned, or null for current item",
  "reason": "user's reason/explanation if provided",
  "edits": {{"field": "new_value"}} if editing,
  "metadata": {{
    "confidence": 0.0-1.0,
    "requires_clarification": true/false,
    "suggested_question": "clarifying question if needed"
  }}
}}

Common patterns:
- "approve" / "looks good" / "send it" → approve current
- "reject" / "no" / "skip this one" → reject current
- "change [field] to [value]" → edit
- "next" / "show me another" → skip to next
- "why" / "explain" → request_info
- "approve everything" → approve_all"""

        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.3
        )
        
        parsed = json.loads(response.choices[0].message.content)
        
        return VoiceCommand(
            action=ApprovalAction(parsed["action"]),
            target_id=parsed.get("target_id"),
            reason=parsed.get("reason"),
            edits=parsed.get("edits"),
            metadata=parsed.get("metadata", {})
        )
    
    async def _execute_command(self, command: VoiceCommand) -> Dict[str, Any]:
        """Execute the parsed command."""
        if command.action == ApprovalAction.APPROVE:
            return await self._approve_item(command.target_id or (self.current_item.id if self.current_item else None))
        
        elif command.action == ApprovalAction.REJECT:
            return await self._reject_item(
                command.target_id or (self.current_item.id if self.current_item else None),
                reason=command.reason
            )
        
        elif command.action == ApprovalAction.EDIT:
            return await self._edit_item(
                command.target_id or (self.current_item.id if self.current_item else None),
                edits=command.edits or {}
            )
        
        elif command.action == ApprovalAction.SKIP:
            return await self._next_item()
        
        elif command.action == ApprovalAction.REQUEST_INFO:
            return await self._get_item_details(
                command.target_id or (self.current_item.id if self.current_item else None)
            )
        
        elif command.action == ApprovalAction.APPROVE_ALL:
            return await self._approve_all()
        
        elif command.action == ApprovalAction.REJECT_ALL:
            return await self._reject_all(reason=command.reason)
        
        return {"action": "unknown", "error": "Command not recognized"}
    
    async def _approve_item(self, item_id: Optional[str]) -> Dict[str, Any]:
        """Approve an item - integrates with actual draft queue."""
        # If no item_id, try to get the first pending draft
        if not item_id:
            pending = await self._get_pending_drafts()
            if pending:
                item_id = pending[0].get("id")
            else:
                return {"action": "error", "message": "No pending drafts to approve"}
        
        # Approve via the actual operator API
        try:
            from src.operator_mode import get_draft_queue
            queue = get_draft_queue()
            success = await queue.approve_draft(item_id, "jarvis_voice")
            
            if success:
                draft = await queue.get_draft(item_id)
                logger.info(f"Voice approved: {item_id}")
                
                # Get next pending draft
                next_drafts = await self._get_pending_drafts()
                next_item = next_drafts[0] if next_drafts else None
                
                return {
                    "action": "approved",
                    "action_taken": True,
                    "success": True,
                    "item_id": item_id,
                    "item_title": draft.get("subject", "Draft"),
                    "next_item": next_item,
                    "remaining": len(next_drafts),
                    "message": f"Approved draft for {draft.get('recipient', 'recipient')}"
                }
            else:
                return {"action": "error", "message": f"Could not approve draft {item_id}"}
                
        except Exception as e:
            logger.error(f"Error approving draft: {e}")
            return {"action": "error", "message": str(e)}
    
    async def _reject_item(self, item_id: Optional[str], reason: Optional[str] = None) -> Dict[str, Any]:
        """Reject an item - integrates with actual draft queue."""
        # If no item_id, try to get the first pending draft
        if not item_id:
            pending = await self._get_pending_drafts()
            if pending:
                item_id = pending[0].get("id")
            else:
                return {"action": "error", "message": "No pending drafts to reject"}
        
        # Reject via the actual operator API
        try:
            from src.operator_mode import get_draft_queue
            queue = get_draft_queue()
            success = await queue.reject_draft(item_id, reason or "Rejected via voice", "jarvis_voice")
            
            if success:
                draft = await queue.get_draft(item_id)
                logger.info(f"Voice rejected: {item_id} (Reason: {reason})")
                
                # Get next pending draft
                next_drafts = await self._get_pending_drafts()
                next_item = next_drafts[0] if next_drafts else None
                
                return {
                    "action": "rejected",
                    "action_taken": True,
                    "success": True,
                    "item_id": item_id,
                    "item_title": draft.get("subject", "Draft"),
                    "reason": reason,
                    "next_item": next_item,
                    "remaining": len(next_drafts),
                    "message": f"Rejected draft for {draft.get('recipient', 'recipient')}"
                }
            else:
                return {"action": "error", "message": f"Could not reject draft {item_id}"}
                
        except Exception as e:
            logger.error(f"Error rejecting draft: {e}")
            return {"action": "error", "message": str(e)}
    
    async def _get_pending_drafts(self) -> List[Dict[str, Any]]:
        """Get pending drafts from the actual queue."""
        try:
            from src.operator_mode import get_draft_queue
            queue = get_draft_queue()
            return await queue.get_pending_approvals()
        except Exception as e:
            logger.error(f"Error getting pending drafts: {e}")
            return []
    
    async def _edit_item(self, item_id: Optional[str], edits: Dict[str, Any]) -> Dict[str, Any]:
        """Edit an item - NOT YET IMPLEMENTED for real drafts."""
        return {
            "action": "edit_pending",
            "message": "Draft editing via voice is not yet implemented. Please edit in the dashboard.",
            "action_taken": False,
            "success": False
        }
    
    async def _next_item(self) -> Dict[str, Any]:
        """Get info about next item in queue."""
        pending = await self._get_pending_drafts()
        if not pending:
            return {"action": "queue_empty", "message": "No more items to review"}
        
        next_draft = pending[0]
        return {
            "action": "next",
            "action_taken": False,
            "item": {
                "id": next_draft.get("id"),
                "recipient": next_draft.get("recipient"),
                "subject": next_draft.get("subject"),
                "company": next_draft.get("company_name"),
                "preview": next_draft.get("body", "")[:150]
            }
        }
    
    async def _get_item_details(self, item_id: Optional[str]) -> Dict[str, Any]:
        """Get detailed information about an item."""
        pending = await self._get_pending_drafts()
        
        if item_id:
            draft = next((d for d in pending if d.get("id") == item_id), None)
        elif pending:
            draft = pending[0]
        else:
            return {"action": "error", "message": "No drafts to show"}
        
        if not draft:
            return {"action": "error", "message": "Draft not found"}
        
        return {
            "action": "details",
            "action_taken": False,
            "item": draft,
            "message": f"Draft for {draft.get('recipient')}: {draft.get('subject')}"
        }
    
    async def _approve_all(self) -> Dict[str, Any]:
        """Approve all pending items (limited to first N for safety)."""
        MAX_BATCH = 10  # Safety limit
        pending = await self._get_pending_drafts()
        
        if not pending:
            return {"action": "queue_empty", "message": "No pending drafts to approve"}
        
        approved = 0
        errors = 0
        
        # Approve up to MAX_BATCH
        from src.operator_mode import get_draft_queue
        queue = get_draft_queue()
        
        for draft in pending[:MAX_BATCH]:
            try:
                success = await queue.approve_draft(draft.get("id"), "jarvis_voice_batch")
                if success:
                    approved += 1
                else:
                    errors += 1
            except Exception as e:
                logger.error(f"Batch approve error: {e}")
                errors += 1
        
        remaining = await self._get_pending_drafts()
        
        logger.info(f"Batch approved {approved} items, {errors} errors")
        
        return {
            "action": "approved_all",
            "action_taken": True,
            "success": True,
            "count": approved,
            "errors": errors,
            "remaining": len(remaining),
            "message": f"Approved {approved} drafts. {len(remaining)} remaining."
        }
    
    async def _reject_all(self, reason: Optional[str] = None) -> Dict[str, Any]:
        """Reject all pending items (limited to first N for safety)."""
        MAX_BATCH = 10
        pending = await self._get_pending_drafts()
        
        if not pending:
            return {"action": "queue_empty", "message": "No pending drafts to reject"}
        
        rejected = 0
        errors = 0
        
        from src.operator_mode import get_draft_queue
        queue = get_draft_queue()
        
        for draft in pending[:MAX_BATCH]:
            try:
                success = await queue.reject_draft(
                    draft.get("id"), 
                    reason or "Batch rejected via voice", 
                    "jarvis_voice_batch"
                )
                if success:
                    rejected += 1
                else:
                    errors += 1
            except Exception as e:
                logger.error(f"Batch reject error: {e}")
                errors += 1
        
        remaining = await self._get_pending_drafts()
        
        logger.info(f"Batch rejected {rejected} items (Reason: {reason})")
        
        return {
            "action": "rejected_all",
            "action_taken": True,
            "success": True,
            "count": rejected,
            "errors": errors,
            "remaining": len(remaining),
            "reason": reason,
            "message": f"Rejected {rejected} drafts. {len(remaining)} remaining."
        }
    
    async def _generate_response(self, command: VoiceCommand, result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate natural spoken response using GPT-4."""
        
        prompt = f"""You are Jarvis, an AI assistant helping review and approve items.

User Command: {command.action}
Result: {json.dumps(result, indent=2)}

Generate a natural, conversational spoken response. Be:
- Concise but friendly
- Confirm the action taken
- Mention next steps if relevant
- Sound like Tony Stark's Jarvis (professional, helpful, slightly witty)

Keep response under 50 words unless providing details.

Examples:
- "Email approved. Moving to the next draft - this one is for Bristol Myers Squibb regarding their supply chain needs."
- "Rejected. I've noted your feedback. Shall we review the next item?"
- "Understood. I've updated the subject line. Would you like to approve this version?"
- "All clear. You have 5 more items pending review. Ready to continue?"
"""

        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=150
        )
        
        spoken_response = response.choices[0].message.content.strip()
        
        return {
            "spoken_response": spoken_response,
            "action_taken": result.get("action"),
            "next_item": result.get("next_item"),
            "status": {
                "pending_count": len(self.pending_items),
                "current_item": self.current_item.id if self.current_item else None
            },
            **result
        }
    
    def _build_command_context(self) -> str:
        """Build context string for command parsing."""
        context = []
        
        if self.current_item:
            context.append(f"Current item: {self.current_item.type} #{self.current_item.id}")
            context.append(f"Title: {self.current_item.title}")
        
        context.append(f"Pending items: {len(self.pending_items)}")
        
        return "\n".join(context)
    
    def _format_item_for_presentation(self, item: ApprovalItem) -> Dict[str, Any]:
        """Format item for voice presentation."""
        return {
            "id": item.id,
            "type": item.type,
            "title": item.title,
            "summary": self._generate_item_summary(item),
            "content_preview": str(item.content)[:200],
            "priority": item.priority,
            "agent": item.agent_source
        }
    
    def _generate_item_summary(self, item: ApprovalItem) -> str:
        """Generate a concise summary for voice reading."""
        if item.type == "email_draft":
            to = item.content.get("to", "unknown recipient")
            subject = item.content.get("subject", "no subject")
            return f"Email to {to}: {subject}"
        
        return f"{item.type} - {item.title}"
    
    # Public API for adding items
    
    def add_item(self, item: ApprovalItem) -> None:
        """Add an item to the approval queue."""
        self.pending_items[item.id] = item
        logger.info(f"Added to queue: {item.type} - {item.title}")
        
        # Set as current if queue was empty
        if not self.current_item:
            self.current_item = item
    
    def add_email_draft(
        self,
        draft_id: str,
        to_email: str,
        to_name: str,
        subject: str,
        body: str,
        context: Dict[str, Any],
        agent: str = "email_drafter"
    ) -> None:
        """Convenience method to add email draft for approval."""
        item = ApprovalItem(
            id=draft_id,
            type="email_draft",
            title=f"Email to {to_name}",
            content={
                "to": to_email,
                "to_name": to_name,
                "subject": subject,
                "body": body
            },
            context=context,
            created_at=datetime.now().isoformat(),
            agent_source=agent
        )
        self.add_item(item)
    
    async def get_status_async(self) -> Dict[str, Any]:
        """Get current status of approval queue from real draft queue."""
        try:
            pending = await self._get_pending_drafts()
            current = pending[0] if pending else None
            
            return {
                "pending_count": len(pending),
                "current_item": current,
                "queue": pending[:10]
            }
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {
                "pending_count": 0,
                "current_item": None,
                "queue": [],
                "error": str(e)
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Sync wrapper for get_status_async - for backwards compatibility."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If already in async context, create a task
                future = asyncio.ensure_future(self.get_status_async())
                return {"pending_count": len(self.pending_items), "note": "Use async get_status_async for real data"}
            return loop.run_until_complete(self.get_status_async())
        except Exception:
            return {"pending_count": len(self.pending_items), "current_item": None, "queue": []}


# Global instance
_voice_approval: Optional[VoiceApprovalInterface] = None


def get_voice_approval() -> VoiceApprovalInterface:
    """Get or create the voice approval interface."""
    global _voice_approval
    if _voice_approval is None:
        _voice_approval = VoiceApprovalInterface()
    return _voice_approval
