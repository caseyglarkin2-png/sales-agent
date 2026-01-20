"""Demo agent for cold-start showcase."""
from typing import Any, Dict

from src.agents.base import BaseAgent
from src.logger import get_logger

logger = get_logger(__name__)


class DemoAgent(BaseAgent):
    """Agent for cold-start demo and capability showcase."""

    def __init__(self):
        """Initialize demo agent."""
        super().__init__(
            name="Demo Agent",
            description="Demonstrates system capabilities in operator mode",
        )

    async def validate_input(self, context: Dict[str, Any]) -> bool:
        """Validate input has required fields."""
        required = ["demo_type", "company_domain"]
        return all(field in context for field in required)

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute demo scenario."""
        logger.info(f"Running demo: {context.get('demo_type')}")

        if not await self.validate_input(context):
            logger.error("Invalid input for demo")
            return {"error": "Missing required fields"}

        try:
            demo_type = context["demo_type"]
            company_domain = context["company_domain"]

            # Generate demo scenario based on type
            if demo_type == "prospecting":
                scenario = self._generate_prospecting_demo(company_domain)
            elif demo_type == "nurturing":
                scenario = self._generate_nurturing_demo(company_domain)
            elif demo_type == "validation":
                scenario = self._generate_validation_demo()
            else:
                scenario = {"error": f"Unknown demo type: {demo_type}"}

            logger.info(f"Demo scenario generated: {demo_type}")
            return scenario

        except Exception as e:
            logger.error(f"Error running demo: {e}")
            return {"error": str(e)}

    @staticmethod
    def _generate_prospecting_demo(company_domain: str) -> Dict[str, Any]:
        """Generate prospecting demo scenario."""
        return {
            "demo_type": "prospecting",
            "company_domain": company_domain,
            "scenario": {
                "incoming_message": {
                    "from": f"contact@{company_domain}",
                    "subject": "Interested in your sales automation platform",
                    "body": "We're looking for a tool to help our team manage outbound prospecting. Are you open to a brief call?",
                },
                "analysis": {
                    "intent_score": 0.85,
                    "key_signals": ["interested", "looking for tool", "open to call"],
                    "next_action": "Generate response draft",
                },
                "suggested_response": "Thank you for reaching out! We'd love to discuss how our platform can streamline your prospecting workflow. How does next Tuesday work for a 20-minute overview call?",
            },
        }

    @staticmethod
    def _generate_nurturing_demo(company_domain: str) -> Dict[str, Any]:
        """Generate nurturing demo scenario."""
        return {
            "demo_type": "nurturing",
            "company_domain": company_domain,
            "scenario": {
                "contact": {
                    "name": "Jane Doe",
                    "company": company_domain,
                    "engagement_stage": "engaged",
                },
                "engagement_history": [
                    {"date": "2026-01-10", "type": "initial_outreach", "result": "opened"},
                    {"date": "2026-01-15", "type": "follow_up", "result": "replied"},
                ],
                "next_action": {
                    "type": "case_study_share",
                    "content": "Share case study of similar company (SaaS, 50-500 employees)",
                    "timing": "2026-01-25",
                },
            },
        }

    @staticmethod
    def _generate_validation_demo() -> Dict[str, Any]:
        """Generate validation demo scenario."""
        return {
            "demo_type": "validation",
            "scenario": {
                "draft": {
                    "to": "prospect@example.com",
                    "subject": "Quick question about your growth plans",
                    "body": "Hi Sarah, I came across your company and was impressed by your recent funding round. Would you be open to discussing how we might help accelerate your go-to-market strategy? Best regards, Alex",
                },
                "validation_results": {
                    "compliance_check": {"passed": True, "issues": []},
                    "quality_check": {"passed": True, "issues": []},
                    "tone_check": {"passed": True, "issues": []},
                    "overall_status": "approved",
                },
                "operator_action": "ready_for_send",
            },
        }
