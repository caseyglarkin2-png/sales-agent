"""Nurturing agent implementation."""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.connectors.hubspot import HubSpotConnector
from src.logger import get_logger

logger = get_logger(__name__)


class NurturingAgent(BaseAgent):
    """Agent for nurturing leads through email sequences."""

    def __init__(self, hubspot_connector: HubSpotConnector):
        """Initialize nurturing agent."""
        super().__init__(
            name="Nurturing Agent",
            description="Manages follow-up sequences and lead engagement",
        )
        self.hubspot = hubspot_connector

    async def validate_input(self, context: Dict[str, Any]) -> bool:
        """Validate input has required fields."""
        required = ["contact_id", "company_id", "engagement_stage"]
        return all(field in context for field in required)

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute nurturing workflow for contact."""
        logger.info(f"Nurturing workflow for contact {context.get('contact_id')}")

        if not await self.validate_input(context):
            logger.error("Invalid input for nurturing workflow")
            return {"error": "Missing required fields"}

        try:
            contact_id = context["contact_id"]
            company_id = context["company_id"]
            stage = context["engagement_stage"]

            # Determine next action based on engagement stage
            next_action = self._get_next_action(stage)
            follow_up_date = self._calculate_follow_up_date(stage)

            # Create task in HubSpot
            task_id = await self.hubspot.create_task(
                contact_id=contact_id,
                title=f"Follow-up: {next_action['title']}",
                body=next_action["body"],
                due_date=follow_up_date.isoformat(),
            )

            result = {
                "contact_id": contact_id,
                "company_id": company_id,
                "stage": stage,
                "next_action": next_action,
                "follow_up_date": follow_up_date.isoformat(),
                "task_id": task_id,
            }

            logger.info(f"Nurturing workflow completed: {result}")
            return result

        except Exception as e:
            logger.error(f"Error in nurturing workflow: {e}")
            return {"error": str(e)}

    @staticmethod
    def _get_next_action(stage: str) -> Dict[str, str]:
        """Determine next action based on engagement stage."""
        actions = {
            "initial_contact": {
                "title": "Initial Introduction",
                "body": "Send personalized introduction with value proposition",
            },
            "engaged": {
                "title": "Deeper Engagement",
                "body": "Share case study or relevant content",
            },
            "qualified": {
                "title": "Demo/Call Request",
                "body": "Propose meeting to discuss solution fit",
            },
            "proposal": {
                "title": "Proposal Follow-up",
                "body": "Check in on proposal review progress",
            },
        }
        return actions.get(stage, actions["initial_contact"])

    @staticmethod
    def _calculate_follow_up_date(stage: str) -> datetime:
        """Calculate optimal follow-up date based on stage."""
        days_map = {
            "initial_contact": 3,
            "engaged": 5,
            "qualified": 2,
            "proposal": 7,
        }
        days = days_map.get(stage, 3)
        return datetime.utcnow() + timedelta(days=days)
