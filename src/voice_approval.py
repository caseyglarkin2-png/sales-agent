"""Voice-enabled approval interface - Jarvis-style human-in-the-loop.

This module provides voice interaction for reviewing and approving
agent outputs (email drafts, campaigns, etc.).
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
        """Approve an item."""
        if not item_id or item_id not in self.pending_items:
            return {"action": "error", "message": "Item not found"}
        
        item = self.pending_items.pop(item_id)
        logger.info(f"Approved: {item.id} - {item.title}")
        
        # Move to next item
        next_item = await self._next_item()
        
        return {
            "action": "approved",
            "item_id": item_id,
            "item_title": item.title,
            "next_item": next_item.get("item") if next_item else None,
            "remaining": len(self.pending_items)
        }
    
    async def _reject_item(self, item_id: Optional[str], reason: Optional[str] = None) -> Dict[str, Any]:
        """Reject an item."""
        if not item_id or item_id not in self.pending_items:
            return {"action": "error", "message": "Item not found"}
        
        item = self.pending_items.pop(item_id)
        logger.info(f"Rejected: {item.id} - {item.title} (Reason: {reason})")
        
        # Move to next item
        next_item = await self._next_item()
        
        return {
            "action": "rejected",
            "item_id": item_id,
            "item_title": item.title,
            "reason": reason,
            "next_item": next_item.get("item") if next_item else None,
            "remaining": len(self.pending_items)
        }
    
    async def _edit_item(self, item_id: Optional[str], edits: Dict[str, Any]) -> Dict[str, Any]:
        """Edit an item."""
        if not item_id or item_id not in self.pending_items:
            return {"action": "error", "message": "Item not found"}
        
        item = self.pending_items[item_id]
        
        # Apply edits
        for field, value in edits.items():
            if field in item.content:
                item.content[field] = value
        
        logger.info(f"Edited: {item.id} - {list(edits.keys())}")
        
        return {
            "action": "edited",
            "item_id": item_id,
            "edits_applied": list(edits.keys()),
            "updated_content": item.content
        }
    
    async def _next_item(self) -> Dict[str, Any]:
        """Move to next item in queue."""
        if not self.pending_items:
            self.current_item = None
            return {"action": "queue_empty", "message": "No more items to review"}
        
        # Get next item (prioritize by priority field)
        next_id = list(self.pending_items.keys())[0]
        self.current_item = self.pending_items[next_id]
        
        return {
            "action": "next",
            "item": self._format_item_for_presentation(self.current_item)
        }
    
    async def _get_item_details(self, item_id: Optional[str]) -> Dict[str, Any]:
        """Get detailed information about an item."""
        if not item_id or item_id not in self.pending_items:
            return {"action": "error", "message": "Item not found"}
        
        item = self.pending_items[item_id]
        
        return {
            "action": "details",
            "item": self._format_item_for_presentation(item),
            "full_context": item.context
        }
    
    async def _approve_all(self) -> Dict[str, Any]:
        """Approve all pending items."""
        count = len(self.pending_items)
        self.pending_items.clear()
        self.current_item = None
        
        logger.info(f"Approved all {count} items")
        
        return {
            "action": "approved_all",
            "count": count
        }
    
    async def _reject_all(self, reason: Optional[str] = None) -> Dict[str, Any]:
        """Reject all pending items."""
        count = len(self.pending_items)
        self.pending_items.clear()
        self.current_item = None
        
        logger.info(f"Rejected all {count} items (Reason: {reason})")
        
        return {
            "action": "rejected_all",
            "count": count,
            "reason": reason
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
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of approval queue."""
        return {
            "pending_count": len(self.pending_items),
            "current_item": self._format_item_for_presentation(self.current_item) if self.current_item else None,
            "queue": [
                self._format_item_for_presentation(item)
                for item in list(self.pending_items.values())[:10]
            ]
        }


# Global instance
_voice_approval: Optional[VoiceApprovalInterface] = None


def get_voice_approval() -> VoiceApprovalInterface:
    """Get or create the voice approval interface."""
    global _voice_approval
    if _voice_approval is None:
        _voice_approval = VoiceApprovalInterface()
    return _voice_approval
