"""Auto-approval rules engine for evaluating drafts.

Simple rule-based system (no ML) that evaluates drafts and decides whether
they can be auto-approved or need manual operator review.

Rules are evaluated in priority order (lowest priority number first).
First matching rule wins. If no rules match, draft goes to manual review.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.db import get_db
from src.logger import get_logger
from src.models.auto_approval import (
    ApprovalDecision,
    ApprovedRecipient,
    AutoApprovalLog,
    AutoApprovalRule,
    RuleType,
)

logger = get_logger(__name__)
settings = get_settings()


class AutoApprovalEngine:
    """Evaluates drafts against auto-approval rules."""

    def __init__(self, session: AsyncSession):
        """Initialize engine with database session.

        Args:
            session: Async database session
        """
        self.session = session

    async def evaluate_draft(
        self,
        draft_id: str,
        recipient_email: str,
        draft_metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[ApprovalDecision, Optional[str], float, str]:
        """
        Evaluate draft against all enabled auto-approval rules.

        Rules are checked in priority order (lowest priority first).
        First matching rule determines the decision.

        Args:
            draft_id: Unique draft identifier
            recipient_email: Email address of recipient
            draft_metadata: Optional draft context (ICP score, domain, etc.)

        Returns:
            Tuple of (decision, matched_rule_id, confidence, reasoning)
            - decision: AUTO_APPROVED or NEEDS_REVIEW
            - matched_rule_id: ID of rule that matched (None if no match)
            - confidence: Confidence score 0.0-1.0
            - reasoning: Human-readable explanation

        Example:
            >>> engine = AutoApprovalEngine(session)
            >>> decision, rule_id, confidence, reason = await engine.evaluate_draft(
            ...     draft_id="draft-123",
            ...     recipient_email="john@example.com",
            ...     draft_metadata={"icp_score": 0.95, "domain": "example.com"}
            ... )
            >>> print(f"{decision}: {reason} (confidence: {confidence})")
            AUTO_APPROVED: Recipient replied before (confidence: 0.95)
        """
        if draft_metadata is None:
            draft_metadata = {}

        logger.info(
            f"Evaluating draft for auto-approval",
            draft_id=draft_id,
            recipient=recipient_email,
        )

        # Check if auto-approval is globally enabled
        if not getattr(settings, "auto_approve_enabled", True):
            reasoning = "Auto-approval disabled via emergency kill switch"
            await self._log_decision(
                draft_id=draft_id,
                recipient_email=recipient_email,
                decision=ApprovalDecision.NEEDS_REVIEW,
                matched_rule_id=None,
                matched_rule_type=None,
                confidence=0.0,
                reasoning=reasoning,
                metadata=draft_metadata,
            )
            return ApprovalDecision.NEEDS_REVIEW, None, 0.0, reasoning

        # Get all enabled rules sorted by priority
        result = await self.session.execute(
            select(AutoApprovalRule)
            .where(AutoApprovalRule.enabled == True)
            .order_by(AutoApprovalRule.priority.asc())
        )
        rules = result.scalars().all()

        if not rules:
            reasoning = "No auto-approval rules configured"
            await self._log_decision(
                draft_id=draft_id,
                recipient_email=recipient_email,
                decision=ApprovalDecision.NEEDS_REVIEW,
                matched_rule_id=None,
                matched_rule_type=None,
                confidence=0.0,
                reasoning=reasoning,
                metadata=draft_metadata,
            )
            return ApprovalDecision.NEEDS_REVIEW, None, 0.0, reasoning

        # Evaluate rules in priority order
        for rule in rules:
            matched, reasoning = await self._evaluate_rule(
                rule=rule,
                recipient_email=recipient_email,
                draft_metadata=draft_metadata,
            )

            if matched:
                decision = ApprovalDecision.AUTO_APPROVED
                logger.info(
                    f"Draft auto-approved by rule",
                    draft_id=draft_id,
                    rule_type=rule.rule_type,
                    confidence=rule.confidence,
                )

                await self._log_decision(
                    draft_id=draft_id,
                    recipient_email=recipient_email,
                    decision=decision,
                    matched_rule_id=rule.id,
                    matched_rule_type=rule.rule_type,
                    confidence=rule.confidence,
                    reasoning=reasoning,
                    metadata=draft_metadata,
                )

                return decision, rule.id, rule.confidence, reasoning

        # No rules matched - manual review required
        decision = ApprovalDecision.NEEDS_REVIEW
        reasoning = "No auto-approval rules matched - requires manual review"

        logger.info(f"Draft requires manual review", draft_id=draft_id)

        await self._log_decision(
            draft_id=draft_id,
            recipient_email=recipient_email,
            decision=decision,
            matched_rule_id=None,
            matched_rule_type=None,
            confidence=0.0,
            reasoning=reasoning,
            metadata=draft_metadata,
        )

        return decision, None, 0.0, reasoning

    async def _evaluate_rule(
        self,
        rule: AutoApprovalRule,
        recipient_email: str,
        draft_metadata: Dict[str, Any],
    ) -> Tuple[bool, str]:
        """
        Evaluate a single rule against draft metadata.

        Args:
            rule: Auto-approval rule to evaluate
            recipient_email: Recipient email address
            draft_metadata: Draft context data

        Returns:
            Tuple of (matched: bool, reasoning: str)
        """
        rule_type = rule.rule_type

        if rule_type == RuleType.REPLIED_BEFORE:
            return await self._check_replied_before(
                recipient_email=recipient_email,
                conditions=rule.conditions,
            )
        elif rule_type == RuleType.KNOWN_GOOD_RECIPIENT:
            return await self._check_known_good_recipient(
                recipient_email=recipient_email,
                conditions=rule.conditions,
            )
        elif rule_type == RuleType.HIGH_ICP_SCORE:
            return await self._check_high_icp_score(
                recipient_email=recipient_email,
                draft_metadata=draft_metadata,
                conditions=rule.conditions,
            )
        else:
            logger.warning(f"Unknown rule type: {rule_type}")
            return False, f"Unknown rule type: {rule_type}"

    async def _check_replied_before(
        self,
        recipient_email: str,
        conditions: Dict[str, Any],
    ) -> Tuple[bool, str]:
        """
        Check if recipient has replied to us in the past.

        This is the safest auto-approval rule - if someone has replied before,
        they're clearly engaged and expect communication.

        Args:
            recipient_email: Email to check
            conditions: Rule conditions (e.g., {'days_lookback': 90})

        Returns:
            Tuple of (matched, reasoning)
        """
        days_lookback = conditions.get("days_lookback", 90)

        # First check approved_recipients table (fast path)
        result = await self.session.execute(
            select(ApprovedRecipient).where(
                ApprovedRecipient.email == recipient_email,
                ApprovedRecipient.total_replies > 0,
            )
        )
        recipient = result.scalar_one_or_none()

        if recipient and recipient.total_replies > 0:
            return True, f"Recipient has replied {recipient.total_replies} times previously"
        
        # Check Gmail for actual replies (Sprint 70)
        try:
            has_reply, reply_reason = await self._check_gmail_for_replies(
                recipient_email, days_lookback
            )
            if has_reply:
                # Update the approved_recipients cache
                await self._record_reply(recipient_email)
                return True, reply_reason
        except Exception as e:
            logger.warning(f"Gmail reply check failed: {e}")

        return False, "No reply history found"
    
    async def _check_gmail_for_replies(
        self,
        recipient_email: str,
        days_lookback: int = 90,
    ) -> Tuple[bool, str]:
        """
        Search Gmail for replies from a recipient (Sprint 70).
        
        Args:
            recipient_email: Email address to check
            days_lookback: Number of days to search
            
        Returns:
            Tuple of (has_replied, reasoning)
        """
        import os
        
        try:
            from src.connectors.gmail import GmailConnector
            
            # Need valid credentials to search Gmail
            gmail_user = os.environ.get("GMAIL_USER_EMAIL")
            if not gmail_user:
                return False, "Gmail not configured"
            
            connector = GmailConnector()
            
            # Search for emails FROM the recipient (their replies to us)
            from datetime import datetime, timedelta
            after_date = datetime.utcnow() - timedelta(days=days_lookback)
            after_str = after_date.strftime("%Y/%m/%d")
            
            query = f"from:{recipient_email} after:{after_str}"
            
            # Use Gmail search
            messages = await connector.search_messages(query, max_results=1)
            
            if messages:
                return True, f"Found reply from {recipient_email} within {days_lookback} days"
            
            return False, "No replies found in Gmail"
            
        except Exception as e:
            logger.debug(f"Gmail reply search error: {e}")
            return False, f"Gmail search unavailable: {e}"
    
    async def _record_reply(self, recipient_email: str) -> None:
        """Record a reply from a recipient in the cache table."""
        try:
            result = await self.session.execute(
                select(ApprovedRecipient).where(
                    ApprovedRecipient.email == recipient_email
                )
            )
            recipient = result.scalar_one_or_none()
            
            if recipient:
                recipient.total_replies += 1
                recipient.last_reply_at = datetime.utcnow()
            else:
                new_recipient = ApprovedRecipient(
                    email=recipient_email,
                    total_sends=0,
                    total_replies=1,
                    last_reply_at=datetime.utcnow(),
                )
                self.session.add(new_recipient)
            
            await self.session.commit()
        except Exception as e:
            logger.warning(f"Failed to record reply: {e}")

    async def _check_known_good_recipient(
        self,
        recipient_email: str,
        conditions: Dict[str, Any],
    ) -> Tuple[bool, str]:
        """
        Check if recipient is in approved whitelist.

        Whitelist is populated from manually approved drafts with positive outcomes.

        Args:
            recipient_email: Email to check
            conditions: Rule conditions (e.g., {'min_sends': 1})

        Returns:
            Tuple of (matched, reasoning)
        """
        min_sends = conditions.get("min_sends", 1)

        result = await self.session.execute(
            select(ApprovedRecipient).where(
                ApprovedRecipient.email == recipient_email,
                ApprovedRecipient.total_sends >= min_sends,
            )
        )
        recipient = result.scalar_one_or_none()

        if recipient:
            return (
                True,
                f"Recipient in approved whitelist ({recipient.total_sends} sends, {recipient.total_replies} replies)",
            )

        return False, "Recipient not in approved whitelist"

    async def _check_high_icp_score(
        self,
        recipient_email: str,
        draft_metadata: Dict[str, Any],
        conditions: Dict[str, Any],
    ) -> Tuple[bool, str]:
        """
        Check if draft has high ideal customer profile (ICP) score.

        Requires both high ICP score AND domain verification to prevent
        auto-approving to wrong recipients.

        Args:
            recipient_email: Email to check
            draft_metadata: Draft context with ICP score
            conditions: Rule conditions (e.g., {'icp_score_min': 0.9})

        Returns:
            Tuple of (matched, reasoning)
        """
        icp_score_min = conditions.get("icp_score_min", 0.9)
        require_domain_match = conditions.get("require_domain_match", True)

        # Get ICP score from metadata
        icp_score = draft_metadata.get("icp_score", 0.0)

        if icp_score < icp_score_min:
            return False, f"ICP score {icp_score:.2f} below threshold {icp_score_min}"

        # Verify domain match if required
        if require_domain_match:
            email_domain = recipient_email.split("@")[1] if "@" in recipient_email else None
            expected_domain = draft_metadata.get("domain")

            if not email_domain or not expected_domain:
                return False, "Missing domain information for verification"

            if email_domain.lower() != expected_domain.lower():
                return False, f"Email domain {email_domain} doesn't match expected {expected_domain}"

        return True, f"High ICP score ({icp_score:.2f}) with domain verification"

    async def _log_decision(
        self,
        draft_id: str,
        recipient_email: str,
        decision: ApprovalDecision,
        matched_rule_id: Optional[str],
        matched_rule_type: Optional[str],
        confidence: float,
        reasoning: str,
        metadata: Dict[str, Any],
    ) -> None:
        """
        Log auto-approval decision to audit trail.

        Args:
            draft_id: Draft identifier
            recipient_email: Recipient email
            decision: Approval decision
            matched_rule_id: ID of matched rule (None if no match)
            matched_rule_type: Type of matched rule
            confidence: Confidence score
            reasoning: Human-readable explanation
            metadata: Additional context
        """
        log_entry = AutoApprovalLog(
            draft_id=draft_id,
            recipient_email=recipient_email,
            decision=decision.value,
            matched_rule_id=matched_rule_id,
            matched_rule_type=matched_rule_type,
            confidence=confidence,
            reasoning=reasoning,
            metadata=metadata,
        )

        self.session.add(log_entry)
        await self.session.commit()

        logger.info(
            f"Logged auto-approval decision",
            draft_id=draft_id,
            decision=decision.value,
            rule_type=matched_rule_type,
        )


async def seed_default_rules(session: AsyncSession) -> None:
    """
    Seed database with default auto-approval rules.

    Creates 3 standard rules with safe, conservative settings.
    Only runs if no rules exist in database.

    Args:
        session: Database session
    """
    # Check if rules already exist
    result = await session.execute(select(AutoApprovalRule))
    existing_rules = result.scalars().all()

    if existing_rules:
        logger.info("Auto-approval rules already exist - skipping seed")
        return

    # Rule 1: Replied Before (Safest - Priority 1)
    rule1 = AutoApprovalRule(
        rule_type=RuleType.REPLIED_BEFORE,
        name="Recipient Has Replied Before",
        description="Auto-approve if recipient has replied to us in the past 90 days",
        conditions={"days_lookback": 90},
        confidence=0.95,
        enabled=True,
        priority=1,
        created_by="system",
    )

    # Rule 2: Known Good Recipients (Safe - Priority 2)
    rule2 = AutoApprovalRule(
        rule_type=RuleType.KNOWN_GOOD_RECIPIENT,
        name="Known Good Recipient",
        description="Auto-approve if recipient is in approved whitelist",
        conditions={"min_sends": 1},
        confidence=0.90,
        enabled=True,
        priority=2,
        created_by="system",
    )

    # Rule 3: High ICP Score (Moderate - Priority 3)
    rule3 = AutoApprovalRule(
        rule_type=RuleType.HIGH_ICP_SCORE,
        name="High ICP Score with Domain Match",
        description="Auto-approve if ICP score >= 0.9 and email domain matches company domain",
        conditions={"icp_score_min": 0.9, "require_domain_match": True},
        confidence=0.85,
        enabled=True,
        priority=3,
        created_by="system",
    )

    session.add_all([rule1, rule2, rule3])
    await session.commit()

    logger.info("Seeded 3 default auto-approval rules")
