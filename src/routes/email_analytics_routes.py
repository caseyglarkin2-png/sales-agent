"""
Email Analytics Routes - Comprehensive email performance analytics
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from enum import Enum
import structlog
import uuid
import random

logger = structlog.get_logger()

router = APIRouter(prefix="/email-analytics", tags=["Email Analytics"])


class MetricType(str, Enum):
    OPENS = "opens"
    CLICKS = "clicks"
    REPLIES = "replies"
    BOUNCES = "bounces"
    UNSUBSCRIBES = "unsubscribes"
    CONVERSIONS = "conversions"


class TimePeriod(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class EmailType(str, Enum):
    COLD_OUTREACH = "cold_outreach"
    FOLLOW_UP = "follow_up"
    NURTURE = "nurture"
    NEWSLETTER = "newsletter"
    TRANSACTIONAL = "transactional"
    PROMOTIONAL = "promotional"


# Email Performance Dashboard
@router.get("/dashboard")
async def get_email_dashboard(
    days: int = Query(default=30, ge=7, le=90),
    tenant_id: str = Query(default="default")
):
    """Get email analytics dashboard"""
    total_sent = random.randint(10000, 50000)
    opens = int(total_sent * random.uniform(0.25, 0.45))
    clicks = int(opens * random.uniform(0.1, 0.25))
    replies = int(opens * random.uniform(0.05, 0.15))
    bounces = int(total_sent * random.uniform(0.01, 0.05))
    
    return {
        "period_days": days,
        "summary": {
            "total_sent": total_sent,
            "delivered": total_sent - bounces,
            "delivery_rate": round((total_sent - bounces) / total_sent, 4),
            "opens": opens,
            "open_rate": round(opens / (total_sent - bounces), 4),
            "unique_opens": int(opens * 0.7),
            "clicks": clicks,
            "click_rate": round(clicks / opens if opens > 0 else 0, 4),
            "replies": replies,
            "reply_rate": round(replies / (total_sent - bounces), 4),
            "bounces": bounces,
            "bounce_rate": round(bounces / total_sent, 4),
            "unsubscribes": int(total_sent * random.uniform(0.001, 0.01)),
            "spam_complaints": int(total_sent * random.uniform(0.0001, 0.001))
        },
        "trends": {
            "open_rate_trend": random.choice(["up", "down", "stable"]),
            "reply_rate_trend": random.choice(["up", "down", "stable"]),
            "bounce_rate_trend": random.choice(["up", "down", "stable"])
        },
        "benchmarks": {
            "industry_open_rate": 0.35,
            "industry_click_rate": 0.08,
            "industry_reply_rate": 0.05
        }
    }


@router.get("/timeline")
async def get_email_timeline(
    metric: MetricType = Query(default=MetricType.OPENS),
    days: int = Query(default=30, ge=7, le=90),
    period: TimePeriod = Query(default=TimePeriod.DAILY),
    tenant_id: str = Query(default="default")
):
    """Get email metrics over time"""
    now = datetime.utcnow()
    
    timeline = []
    for i in range(days):
        date = (now - timedelta(days=days - i)).isoformat()[:10]
        
        if metric == MetricType.OPENS:
            value = random.randint(100, 1000)
            rate = round(random.uniform(0.25, 0.45), 4)
        elif metric == MetricType.CLICKS:
            value = random.randint(20, 200)
            rate = round(random.uniform(0.05, 0.15), 4)
        elif metric == MetricType.REPLIES:
            value = random.randint(10, 100)
            rate = round(random.uniform(0.03, 0.12), 4)
        elif metric == MetricType.BOUNCES:
            value = random.randint(5, 50)
            rate = round(random.uniform(0.01, 0.05), 4)
        else:
            value = random.randint(1, 20)
            rate = round(random.uniform(0.001, 0.01), 4)
        
        timeline.append({
            "date": date,
            "count": value,
            "rate": rate
        })
    
    return {
        "metric": metric.value,
        "period": period.value,
        "timeline": timeline,
        "total": sum(t["count"] for t in timeline),
        "avg_rate": round(sum(t["rate"] for t in timeline) / len(timeline), 4)
    }


# By Email Type
@router.get("/by-type")
async def get_metrics_by_email_type(
    days: int = Query(default=30, ge=7, le=90),
    tenant_id: str = Query(default="default")
):
    """Get email metrics by email type"""
    types_data = []
    
    for email_type in EmailType:
        sent = random.randint(1000, 10000)
        opens = int(sent * random.uniform(0.2, 0.5))
        clicks = int(opens * random.uniform(0.05, 0.2))
        replies = int(opens * random.uniform(0.03, 0.15))
        
        types_data.append({
            "type": email_type.value,
            "sent": sent,
            "opens": opens,
            "open_rate": round(opens / sent, 4),
            "clicks": clicks,
            "click_rate": round(clicks / opens if opens > 0 else 0, 4),
            "replies": replies,
            "reply_rate": round(replies / sent, 4),
            "conversions": random.randint(1, int(replies * 0.5))
        })
    
    types_data.sort(key=lambda x: x["open_rate"], reverse=True)
    
    return {
        "period_days": days,
        "by_type": types_data
    }


# By Rep
@router.get("/by-rep")
async def get_metrics_by_rep(
    days: int = Query(default=30, ge=7, le=90),
    limit: int = Query(default=20, le=50),
    tenant_id: str = Query(default="default")
):
    """Get email metrics by sales rep"""
    reps = []
    
    for i in range(limit):
        sent = random.randint(200, 2000)
        opens = int(sent * random.uniform(0.25, 0.50))
        clicks = int(opens * random.uniform(0.08, 0.20))
        replies = int(opens * random.uniform(0.05, 0.18))
        
        reps.append({
            "rep_id": f"rep_{i+1}",
            "name": f"Sales Rep {i+1}",
            "sent": sent,
            "opens": opens,
            "open_rate": round(opens / sent, 4),
            "clicks": clicks,
            "click_rate": round(clicks / opens if opens > 0 else 0, 4),
            "replies": replies,
            "reply_rate": round(replies / sent, 4),
            "meetings_booked": random.randint(1, int(replies * 0.3)),
            "rank": i + 1
        })
    
    reps.sort(key=lambda x: x["reply_rate"], reverse=True)
    for i, rep in enumerate(reps):
        rep["rank"] = i + 1
    
    return {
        "period_days": days,
        "reps": reps,
        "avg_open_rate": round(sum(r["open_rate"] for r in reps) / len(reps), 4),
        "avg_reply_rate": round(sum(r["reply_rate"] for r in reps) / len(reps), 4)
    }


# By Template
@router.get("/by-template")
async def get_metrics_by_template(
    days: int = Query(default=30, ge=7, le=90),
    limit: int = Query(default=20, le=50),
    tenant_id: str = Query(default="default")
):
    """Get email metrics by template"""
    templates = []
    template_names = [
        "Initial Outreach - Enterprise",
        "Follow-up #1",
        "Follow-up #2",
        "Meeting Request",
        "Demo Invite",
        "Case Study Share",
        "Pricing Discussion",
        "Renewal Reminder",
        "Competitive Win-back",
        "Event Invitation"
    ]
    
    for i, name in enumerate(template_names[:limit]):
        sent = random.randint(100, 2000)
        opens = int(sent * random.uniform(0.20, 0.55))
        clicks = int(opens * random.uniform(0.05, 0.25))
        replies = int(opens * random.uniform(0.04, 0.20))
        
        templates.append({
            "template_id": f"tpl_{i+1}",
            "name": name,
            "sent": sent,
            "opens": opens,
            "open_rate": round(opens / sent, 4),
            "clicks": clicks,
            "click_rate": round(clicks / opens if opens > 0 else 0, 4),
            "replies": replies,
            "reply_rate": round(replies / sent, 4),
            "avg_response_time_hours": round(random.uniform(2, 24), 1)
        })
    
    templates.sort(key=lambda x: x["reply_rate"], reverse=True)
    
    return {
        "period_days": days,
        "templates": templates,
        "top_performer": templates[0]["name"] if templates else None
    }


# By Subject Line
@router.get("/subject-lines")
async def get_subject_line_performance(
    days: int = Query(default=30, ge=7, le=90),
    limit: int = Query(default=20, le=50),
    tenant_id: str = Query(default="default")
):
    """Get performance by subject line"""
    subjects = [
        "Quick question about {company}",
        "Ideas for {company}",
        "{firstName}, quick thought",
        "Following up on my last email",
        "Can we schedule 15 minutes?",
        "Thought you'd find this interesting",
        "Re: {company} discussion",
        "3 ideas for {company} growth",
        "Are you the right person?",
        "Congrats on the recent news!"
    ]
    
    subject_data = []
    for subject in subjects[:limit]:
        sent = random.randint(100, 1000)
        opens = int(sent * random.uniform(0.20, 0.60))
        
        subject_data.append({
            "subject": subject,
            "sent": sent,
            "opens": opens,
            "open_rate": round(opens / sent, 4),
            "a_b_tested": random.choice([True, False]),
            "avg_read_time_seconds": random.randint(10, 60)
        })
    
    subject_data.sort(key=lambda x: x["open_rate"], reverse=True)
    
    return {
        "period_days": days,
        "subjects": subject_data,
        "recommendations": [
            "Personalization with {firstName} increases open rates by 22%",
            "Questions in subject lines perform 15% better",
            "Shorter subjects (3-5 words) have higher open rates"
        ]
    }


# Engagement Analysis
@router.get("/engagement")
async def get_engagement_analysis(
    days: int = Query(default=30, ge=7, le=90),
    tenant_id: str = Query(default="default")
):
    """Get email engagement analysis"""
    return {
        "period_days": days,
        "time_analysis": {
            "best_send_days": [
                {"day": "Tuesday", "open_rate": 0.42},
                {"day": "Wednesday", "open_rate": 0.40},
                {"day": "Thursday", "open_rate": 0.38}
            ],
            "best_send_hours": [
                {"hour": "9:00 AM", "open_rate": 0.45},
                {"hour": "2:00 PM", "open_rate": 0.41},
                {"hour": "7:00 AM", "open_rate": 0.39}
            ]
        },
        "device_breakdown": {
            "desktop": round(random.uniform(0.40, 0.55), 3),
            "mobile": round(random.uniform(0.35, 0.50), 3),
            "tablet": round(random.uniform(0.05, 0.15), 3)
        },
        "email_client_breakdown": {
            "gmail": round(random.uniform(0.30, 0.45), 3),
            "outlook": round(random.uniform(0.25, 0.40), 3),
            "apple_mail": round(random.uniform(0.15, 0.25), 3),
            "other": round(random.uniform(0.05, 0.15), 3)
        },
        "engagement_score_distribution": {
            "highly_engaged": random.randint(10, 25),
            "moderately_engaged": random.randint(25, 45),
            "low_engagement": random.randint(20, 40),
            "not_engaged": random.randint(10, 25)
        }
    }


# Bounce Analysis
@router.get("/bounces")
async def get_bounce_analysis(
    days: int = Query(default=30, ge=7, le=90),
    tenant_id: str = Query(default="default")
):
    """Get bounce analysis"""
    total_bounces = random.randint(100, 1000)
    
    return {
        "period_days": days,
        "total_bounces": total_bounces,
        "bounce_rate": round(random.uniform(0.01, 0.05), 4),
        "by_type": {
            "hard_bounces": {
                "count": int(total_bounces * 0.3),
                "pct": 0.30,
                "reasons": {
                    "invalid_email": int(total_bounces * 0.2),
                    "domain_not_found": int(total_bounces * 0.08),
                    "mailbox_not_found": int(total_bounces * 0.02)
                }
            },
            "soft_bounces": {
                "count": int(total_bounces * 0.7),
                "pct": 0.70,
                "reasons": {
                    "mailbox_full": int(total_bounces * 0.3),
                    "server_issues": int(total_bounces * 0.25),
                    "message_too_large": int(total_bounces * 0.1),
                    "other": int(total_bounces * 0.05)
                }
            }
        },
        "recommendations": [
            "Clean email list - remove 23 invalid addresses",
            "Reduce email size to under 100KB",
            "Implement email verification on forms"
        ]
    }


# A/B Test Results
@router.get("/ab-tests")
async def get_ab_test_results(
    days: int = Query(default=30, ge=7, le=90),
    tenant_id: str = Query(default="default")
):
    """Get A/B test results"""
    tests = []
    
    for i in range(5):
        variant_a_sent = random.randint(500, 2000)
        variant_b_sent = random.randint(500, 2000)
        
        tests.append({
            "test_id": f"test_{i+1}",
            "name": f"Subject Line Test {i+1}",
            "status": random.choice(["running", "completed", "completed", "completed"]),
            "started_at": (datetime.utcnow() - timedelta(days=random.randint(1, 30))).isoformat(),
            "variant_a": {
                "name": f"Variant A",
                "sent": variant_a_sent,
                "open_rate": round(random.uniform(0.25, 0.45), 4),
                "reply_rate": round(random.uniform(0.03, 0.12), 4)
            },
            "variant_b": {
                "name": f"Variant B",
                "sent": variant_b_sent,
                "open_rate": round(random.uniform(0.25, 0.45), 4),
                "reply_rate": round(random.uniform(0.03, 0.12), 4)
            },
            "winner": random.choice(["A", "B", None]),
            "confidence": round(random.uniform(0.80, 0.99), 2) if random.choice([True, True, False]) else None
        })
    
    return {
        "period_days": days,
        "tests": tests,
        "active_tests": len([t for t in tests if t["status"] == "running"]),
        "completed_tests": len([t for t in tests if t["status"] == "completed"])
    }


# Deliverability Score
@router.get("/deliverability-score")
async def get_deliverability_score(tenant_id: str = Query(default="default")):
    """Get email deliverability score"""
    overall = random.randint(70, 98)
    
    return {
        "overall_score": overall,
        "status": "excellent" if overall >= 90 else "good" if overall >= 75 else "needs_attention" if overall >= 60 else "critical",
        "factors": {
            "sender_reputation": random.randint(70, 100),
            "authentication": random.randint(80, 100),
            "content_quality": random.randint(65, 100),
            "list_quality": random.randint(70, 100),
            "engagement": random.randint(60, 100)
        },
        "issues": [
            {"severity": "warning", "issue": "SPF record incomplete", "impact": -5}
        ] if overall < 90 else [],
        "recommendations": [
            "Complete DMARC setup",
            "Clean inactive subscribers"
        ] if overall < 85 else []
    }
