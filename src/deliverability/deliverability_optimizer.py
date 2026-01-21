"""
Email Deliverability Optimizer
===============================
Optimizes email deliverability through spam scoring, warmup tracking,
domain health monitoring, and content optimization.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
import structlog

logger = structlog.get_logger(__name__)


class WarmupStage(str, Enum):
    """Email warmup stages."""
    NOT_STARTED = "not_started"
    INITIAL = "initial"           # 1-10 emails/day
    BUILDING = "building"         # 10-50 emails/day
    RAMPING = "ramping"           # 50-100 emails/day
    ESTABLISHED = "established"   # 100+ emails/day
    MATURE = "mature"             # Full volume


@dataclass
class SpamCheckResult:
    """Result of spam content check."""
    score: float  # 0-100, lower is better (less spammy)
    is_spam: bool
    issues: list[dict] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    checked_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "is_spam": self.is_spam,
            "issues": self.issues,
            "suggestions": self.suggestions,
            "checked_at": self.checked_at.isoformat(),
        }


@dataclass
class WarmupStatus:
    """Status of email warmup for a sending domain."""
    domain: str
    stage: WarmupStage
    started_at: Optional[datetime] = None
    current_daily_limit: int = 10
    target_daily_limit: int = 200
    emails_sent_today: int = 0
    emails_sent_total: int = 0
    days_active: int = 0
    bounce_rate: float = 0.0
    spam_complaint_rate: float = 0.0
    open_rate: float = 0.0
    reply_rate: float = 0.0
    is_healthy: bool = True
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            "domain": self.domain,
            "stage": self.stage.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "current_daily_limit": self.current_daily_limit,
            "target_daily_limit": self.target_daily_limit,
            "emails_sent_today": self.emails_sent_today,
            "emails_sent_total": self.emails_sent_total,
            "days_active": self.days_active,
            "bounce_rate": round(self.bounce_rate, 2),
            "spam_complaint_rate": round(self.spam_complaint_rate, 2),
            "open_rate": round(self.open_rate, 2),
            "reply_rate": round(self.reply_rate, 2),
            "is_healthy": self.is_healthy,
            "last_updated": self.last_updated.isoformat(),
        }
    
    def can_send_more(self) -> bool:
        """Check if we can send more emails today."""
        return self.emails_sent_today < self.current_daily_limit and self.is_healthy


@dataclass
class DomainHealth:
    """Health metrics for a sending domain."""
    domain: str
    has_spf: bool = False
    has_dkim: bool = False
    has_dmarc: bool = False
    spf_valid: bool = False
    dkim_valid: bool = False
    dmarc_policy: str = "none"  # none, quarantine, reject
    blacklist_status: dict = field(default_factory=dict)
    reputation_score: float = 0.0  # 0-100
    last_checked: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def is_fully_authenticated(self) -> bool:
        return self.has_spf and self.has_dkim and self.has_dmarc
    
    @property
    def is_healthy(self) -> bool:
        return (
            self.spf_valid and 
            self.dkim_valid and 
            self.reputation_score >= 70 and
            not any(self.blacklist_status.values())
        )
    
    def to_dict(self) -> dict:
        return {
            "domain": self.domain,
            "has_spf": self.has_spf,
            "has_dkim": self.has_dkim,
            "has_dmarc": self.has_dmarc,
            "spf_valid": self.spf_valid,
            "dkim_valid": self.dkim_valid,
            "dmarc_policy": self.dmarc_policy,
            "blacklist_status": self.blacklist_status,
            "reputation_score": self.reputation_score,
            "is_fully_authenticated": self.is_fully_authenticated,
            "is_healthy": self.is_healthy,
            "last_checked": self.last_checked.isoformat(),
        }


@dataclass
class DeliverabilityScore:
    """Overall deliverability score for an email."""
    overall_score: float  # 0-100
    content_score: float
    technical_score: float
    reputation_score: float
    factors: dict = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "overall_score": round(self.overall_score, 1),
            "content_score": round(self.content_score, 1),
            "technical_score": round(self.technical_score, 1),
            "reputation_score": round(self.reputation_score, 1),
            "factors": self.factors,
            "recommendations": self.recommendations,
        }


# Spam trigger words and patterns
SPAM_TRIGGERS = {
    "high": [
        "free", "winner", "congratulations", "act now", "limited time",
        "urgent", "call now", "click here", "buy now", "order now",
        "100% free", "no obligation", "risk free", "satisfaction guaranteed",
        "special promotion", "exclusive deal", "once in a lifetime",
    ],
    "medium": [
        "discount", "save", "offer", "deal", "cheap", "bargain",
        "lowest price", "best price", "affordable", "cash bonus",
        "earn money", "income", "profit", "opportunity", "investment",
    ],
    "low": [
        "subscribe", "unsubscribe", "newsletter", "promo", "sale",
        "limited", "hurry", "today only", "don't miss", "act fast",
    ],
}

# Formatting issues
FORMATTING_ISSUES = [
    (r'[A-Z]{5,}', "Excessive uppercase text"),
    (r'!{2,}', "Multiple exclamation marks"),
    (r'\$\d+', "Currency amounts in subject"),
    (r'%\d+', "Percentages that look promotional"),
    (r'[^\x00-\x7F]', "Non-ASCII characters"),
]


class DeliverabilityOptimizer:
    """
    Optimizes email deliverability through content analysis,
    warmup tracking, and domain health monitoring.
    """
    
    def __init__(self):
        self.warmup_statuses: dict[str, WarmupStatus] = {}
        self.domain_health: dict[str, DomainHealth] = {}
    
    def check_spam_score(
        self,
        subject: str,
        body: str,
        from_name: str = "",
    ) -> SpamCheckResult:
        """
        Check email content for spam triggers.
        Returns a score where lower is better.
        """
        issues = []
        suggestions = []
        score = 0
        
        combined_text = f"{subject} {body}".lower()
        
        # Check spam trigger words
        for severity, words in SPAM_TRIGGERS.items():
            for word in words:
                if word.lower() in combined_text:
                    weight = {"high": 15, "medium": 8, "low": 3}[severity]
                    score += weight
                    issues.append({
                        "type": "spam_word",
                        "word": word,
                        "severity": severity,
                        "weight": weight,
                    })
        
        # Check formatting issues
        for pattern, description in FORMATTING_ISSUES:
            if re.search(pattern, subject):
                score += 10
                issues.append({
                    "type": "formatting",
                    "location": "subject",
                    "description": description,
                    "weight": 10,
                })
            
            matches = re.findall(pattern, body)
            if len(matches) > 3:
                score += 5
                issues.append({
                    "type": "formatting",
                    "location": "body",
                    "description": description,
                    "count": len(matches),
                    "weight": 5,
                })
        
        # Check subject length
        if len(subject) > 60:
            score += 5
            issues.append({
                "type": "length",
                "location": "subject",
                "description": "Subject line too long",
                "length": len(subject),
            })
        
        # Check body length
        if len(body) < 50:
            score += 10
            issues.append({
                "type": "length",
                "location": "body",
                "description": "Email body too short",
            })
        elif len(body) > 5000:
            score += 5
            issues.append({
                "type": "length",
                "location": "body",
                "description": "Email body very long",
            })
        
        # Check link count
        link_count = len(re.findall(r'https?://', body))
        if link_count > 5:
            score += 10
            issues.append({
                "type": "links",
                "description": "Too many links",
                "count": link_count,
            })
        
        # Check image-to-text ratio (simplified)
        img_count = len(re.findall(r'<img', body.lower()))
        if img_count > 3:
            score += 8
            issues.append({
                "type": "images",
                "description": "Too many images",
                "count": img_count,
            })
        
        # Generate suggestions
        if score > 30:
            suggestions.append("Consider rewriting subject line to be more personal")
        if any(i["type"] == "spam_word" and i["severity"] == "high" for i in issues):
            suggestions.append("Remove high-risk spam trigger words")
        if any(i["type"] == "formatting" for i in issues):
            suggestions.append("Fix formatting issues (caps, exclamation marks)")
        if any(i["type"] == "links" for i in issues):
            suggestions.append("Reduce the number of links in the email")
        if not suggestions:
            suggestions.append("Email content looks good for deliverability")
        
        # Cap score at 100
        score = min(100, score)
        
        return SpamCheckResult(
            score=score,
            is_spam=score > 50,
            issues=issues,
            suggestions=suggestions,
        )
    
    def optimize_content(
        self,
        subject: str,
        body: str,
    ) -> dict:
        """
        Suggest optimizations for email content.
        """
        spam_check = self.check_spam_score(subject, body)
        
        optimizations = {
            "subject": [],
            "body": [],
            "general": [],
        }
        
        # Subject optimizations
        if len(subject) > 50:
            optimizations["subject"].append({
                "type": "shorten",
                "suggestion": "Keep subject under 50 characters for better mobile display",
                "current_length": len(subject),
            })
        
        if subject.upper() == subject:
            optimizations["subject"].append({
                "type": "case",
                "suggestion": "Avoid all caps - use sentence case instead",
            })
        
        if not re.search(r'\b(you|your)\b', subject.lower()):
            optimizations["subject"].append({
                "type": "personalization",
                "suggestion": "Consider adding personalization (recipient's name, company)",
            })
        
        # Body optimizations
        sentences = re.split(r'[.!?]', body)
        avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0
        
        if avg_sentence_length > 25:
            optimizations["body"].append({
                "type": "readability",
                "suggestion": "Shorten sentences for better readability",
                "avg_words_per_sentence": round(avg_sentence_length, 1),
            })
        
        # Check for personalization
        if not re.search(r'\{\{|\{%|{{', body):
            optimizations["body"].append({
                "type": "personalization",
                "suggestion": "Add merge fields for personalization",
            })
        
        # Check for CTA
        cta_patterns = [r'schedule', r'book', r'call', r'reply', r'click', r'visit']
        has_cta = any(re.search(p, body.lower()) for p in cta_patterns)
        if not has_cta:
            optimizations["body"].append({
                "type": "cta",
                "suggestion": "Add a clear call-to-action",
            })
        
        # General optimizations
        if spam_check.score > 30:
            optimizations["general"].append({
                "type": "spam_score",
                "suggestion": f"Spam score is {spam_check.score}/100 - consider revising content",
                "issues": spam_check.issues[:3],
            })
        
        return {
            "spam_check": spam_check.to_dict(),
            "optimizations": optimizations,
            "optimization_count": sum(len(v) for v in optimizations.values()),
        }
    
    def get_warmup_status(self, domain: str) -> WarmupStatus:
        """Get warmup status for a domain."""
        if domain not in self.warmup_statuses:
            self.warmup_statuses[domain] = WarmupStatus(
                domain=domain,
                stage=WarmupStage.NOT_STARTED,
            )
        return self.warmup_statuses[domain]
    
    def start_warmup(self, domain: str, target_daily_limit: int = 200) -> WarmupStatus:
        """Start warming up a domain."""
        status = self.get_warmup_status(domain)
        
        if status.stage == WarmupStage.NOT_STARTED:
            status.stage = WarmupStage.INITIAL
            status.started_at = datetime.utcnow()
            status.current_daily_limit = 10
            status.target_daily_limit = target_daily_limit
        
        logger.info("warmup_started", domain=domain, target=target_daily_limit)
        
        return status
    
    def record_email_sent(self, domain: str, bounced: bool = False, spam_complaint: bool = False) -> WarmupStatus:
        """Record an email sent for warmup tracking."""
        status = self.get_warmup_status(domain)
        
        status.emails_sent_today += 1
        status.emails_sent_total += 1
        status.last_updated = datetime.utcnow()
        
        # Update metrics
        if bounced:
            # Simplified bounce rate update
            status.bounce_rate = (status.bounce_rate * 0.95) + (0.05 * 100)
        if spam_complaint:
            status.spam_complaint_rate = (status.spam_complaint_rate * 0.95) + (0.05 * 100)
        
        # Check health
        status.is_healthy = (
            status.bounce_rate < 5 and
            status.spam_complaint_rate < 0.1
        )
        
        # Progress warmup stages
        self._progress_warmup(status)
        
        return status
    
    def _progress_warmup(self, status: WarmupStatus) -> None:
        """Progress warmup stage based on metrics."""
        if not status.is_healthy:
            return
        
        # Calculate days active
        if status.started_at:
            status.days_active = (datetime.utcnow() - status.started_at).days
        
        # Stage progression
        if status.stage == WarmupStage.INITIAL and status.days_active >= 7:
            status.stage = WarmupStage.BUILDING
            status.current_daily_limit = 30
        elif status.stage == WarmupStage.BUILDING and status.days_active >= 14:
            status.stage = WarmupStage.RAMPING
            status.current_daily_limit = 75
        elif status.stage == WarmupStage.RAMPING and status.days_active >= 21:
            status.stage = WarmupStage.ESTABLISHED
            status.current_daily_limit = 150
        elif status.stage == WarmupStage.ESTABLISHED and status.days_active >= 30:
            status.stage = WarmupStage.MATURE
            status.current_daily_limit = status.target_daily_limit
    
    def check_domain_health(self, domain: str) -> DomainHealth:
        """Check health of a sending domain."""
        # In production, this would make actual DNS queries
        # For now, return simulated healthy state
        
        health = DomainHealth(
            domain=domain,
            has_spf=True,
            has_dkim=True,
            has_dmarc=True,
            spf_valid=True,
            dkim_valid=True,
            dmarc_policy="quarantine",
            reputation_score=85.0,
        )
        
        self.domain_health[domain] = health
        
        logger.info(
            "domain_health_checked",
            domain=domain,
            healthy=health.is_healthy,
            score=health.reputation_score,
        )
        
        return health
    
    def get_deliverability_score(
        self,
        subject: str,
        body: str,
        from_domain: str,
    ) -> DeliverabilityScore:
        """Calculate overall deliverability score."""
        # Content score
        spam_check = self.check_spam_score(subject, body)
        content_score = 100 - spam_check.score
        
        # Technical score
        domain_health = self.check_domain_health(from_domain)
        technical_score = 0
        if domain_health.spf_valid:
            technical_score += 30
        if domain_health.dkim_valid:
            technical_score += 30
        if domain_health.has_dmarc:
            technical_score += 20
        if domain_health.dmarc_policy in ["quarantine", "reject"]:
            technical_score += 20
        
        # Reputation score
        reputation_score = domain_health.reputation_score
        
        # Overall weighted score
        overall_score = (
            content_score * 0.4 +
            technical_score * 0.3 +
            reputation_score * 0.3
        )
        
        # Factors affecting score
        factors = {
            "content": {
                "spam_score": spam_check.score,
                "issues_count": len(spam_check.issues),
            },
            "technical": {
                "spf": domain_health.spf_valid,
                "dkim": domain_health.dkim_valid,
                "dmarc": domain_health.has_dmarc,
            },
            "reputation": {
                "score": reputation_score,
                "is_healthy": domain_health.is_healthy,
            },
        }
        
        # Recommendations
        recommendations = []
        if content_score < 70:
            recommendations.extend(spam_check.suggestions)
        if technical_score < 80:
            if not domain_health.spf_valid:
                recommendations.append("Fix SPF record")
            if not domain_health.dkim_valid:
                recommendations.append("Configure DKIM")
            if not domain_health.has_dmarc:
                recommendations.append("Add DMARC record")
        if reputation_score < 70:
            recommendations.append("Improve domain reputation with engagement")
        
        return DeliverabilityScore(
            overall_score=overall_score,
            content_score=content_score,
            technical_score=technical_score,
            reputation_score=reputation_score,
            factors=factors,
            recommendations=recommendations,
        )
    
    def reset_daily_counts(self) -> int:
        """Reset daily email counts (call at midnight)."""
        count = 0
        for status in self.warmup_statuses.values():
            if status.emails_sent_today > 0:
                status.emails_sent_today = 0
                count += 1
        return count


# Singleton instance
_optimizer: Optional[DeliverabilityOptimizer] = None


def get_deliverability_optimizer() -> DeliverabilityOptimizer:
    """Get the deliverability optimizer singleton."""
    global _optimizer
    if _optimizer is None:
        _optimizer = DeliverabilityOptimizer()
    return _optimizer
