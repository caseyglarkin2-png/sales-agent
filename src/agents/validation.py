"""Validation agent implementation."""
from typing import Any, Dict, List

from src.agents.base import BaseAgent
from src.logger import get_logger

logger = get_logger(__name__)


class ValidationAgent(BaseAgent):
    """Agent for validating and approving outbound messages."""

    def __init__(self):
        """Initialize validation agent."""
        super().__init__(
            name="Validation Agent",
            description="Validates drafts against compliance and quality standards",
        )
        self.compliance_rules = self._load_compliance_rules()

    async def validate_input(self, context: Dict[str, Any]) -> bool:
        """Validate input has required fields."""
        required = ["draft_id", "recipient", "subject", "body"]
        return all(field in context for field in required)

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate draft for compliance and quality."""
        logger.info(f"Validating draft {context.get('draft_id')}")

        if not await self.validate_input(context):
            logger.error("Invalid input for validation")
            return {"error": "Missing required fields"}

        try:
            draft_id = context["draft_id"]
            recipient = context["recipient"]
            subject = context["subject"]
            body = context["body"]

            # Run validation checks
            checks = {
                "compliance": await self._check_compliance(body),
                "quality": await self._check_quality(subject, body),
                "tone": await self._check_tone(body),
                "length": await self._check_length(subject, body),
            }

            # Determine approval status
            passed_checks = sum(1 for v in checks.values() if v["passed"])
            total_checks = len(checks)
            approval_status = "approved" if passed_checks == total_checks else "requires_review"

            result = {
                "draft_id": draft_id,
                "recipient": recipient,
                "checks": checks,
                "passed_checks": passed_checks,
                "total_checks": total_checks,
                "approval_status": approval_status,
                "issues": self._compile_issues(checks),
            }

            logger.info(f"Validation complete: status={approval_status}, passed={passed_checks}/{total_checks}")
            return result

        except Exception as e:
            logger.error(f"Error in validation: {e}")
            return {"error": str(e)}

    async def _check_compliance(self, body: str) -> Dict[str, Any]:
        """Check for compliance violations."""
        violations = []

        # Check for prohibited content
        prohibited_terms = ["guarantee", "promise", "won't", "can't"]
        for term in prohibited_terms:
            if term.lower() in body.lower():
                violations.append(f"Prohibited term: '{term}'")

        # Check for unsubscribe link
        if "unsubscribe" not in body.lower():
            violations.append("Missing unsubscribe mechanism")

        return {
            "passed": len(violations) == 0,
            "violations": violations,
        }

    async def _check_quality(self, subject: str, body: str) -> Dict[str, Any]:
        """Check quality metrics."""
        issues = []

        # Check subject line length
        if len(subject) < 5:
            issues.append("Subject line too short")
        if len(subject) > 100:
            issues.append("Subject line too long")

        # Check body length
        if len(body) < 50:
            issues.append("Message too short")
        if len(body) > 2000:
            issues.append("Message too long")

        # Check for generic greetings
        if body.strip().startswith("Hi"):
            issues.append("Consider personalizing greeting")

        return {
            "passed": len(issues) == 0,
            "issues": issues,
        }

    async def _check_tone(self, body: str) -> Dict[str, Any]:
        """Check tone and voice consistency."""
        # Placeholder for tone analysis (would use LLM in production)
        issues = []

        # Check for aggressive language
        aggressive_terms = ["must", "demand", "urgent", "immediately"]
        for term in aggressive_terms:
            if term.lower() in body.lower():
                issues.append(f"Potentially aggressive tone: '{term}'")

        return {
            "passed": len(issues) == 0,
            "issues": issues,
        }

    async def _check_length(self, subject: str, body: str) -> Dict[str, Any]:
        """Check overall length appropriateness."""
        total_length = len(subject) + len(body)

        issues = []
        if total_length < 100:
            issues.append("Message too brief")
        if total_length > 3000:
            issues.append("Message too long")

        return {
            "passed": len(issues) == 0,
            "issues": issues,
        }

    @staticmethod
    def _compile_issues(checks: Dict[str, Dict[str, Any]]) -> List[str]:
        """Compile all issues from checks."""
        issues = []
        for check_name, check_result in checks.items():
            if not check_result["passed"]:
                check_issues = check_result.get("issues", check_result.get("violations", []))
                issues.extend(check_issues)
        return issues

    @staticmethod
    def _load_compliance_rules() -> Dict[str, Any]:
        """Load compliance rules."""
        return {
            "max_follow_ups_per_week": 2,
            "max_emails_per_day": 20,
            "prohibited_terms": ["guarantee", "promise"],
            "required_elements": ["unsubscribe"],
        }
