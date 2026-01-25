"""
Deal Velocity Routes - Pipeline velocity and deal acceleration tracking
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

router = APIRouter(prefix="/deal-velocity", tags=["Deal Velocity"])


class VelocityStatus(str, Enum):
    FAST = "fast"
    ON_TRACK = "on_track"
    SLOW = "slow"
    STALLED = "stalled"


class StageCategory(str, Enum):
    EARLY = "early"
    MID = "mid"
    LATE = "late"


# In-memory storage
velocity_metrics = {}
stage_benchmarks = {}
velocity_alerts = {}


class StageThresholdCreate(BaseModel):
    stage_name: str
    category: StageCategory
    target_days: int
    warning_days: int
    critical_days: int


# Deal Velocity Analysis
@router.get("/deal/{deal_id}")
async def get_deal_velocity(
    deal_id: str,
    tenant_id: str = Query(default="default")
):
    """Get velocity metrics for a specific deal"""
    now = datetime.utcnow()
    
    # Generate mock velocity data
    current_stage = random.choice(["Discovery", "Qualification", "Demo", "Proposal", "Negotiation"])
    days_in_stage = random.randint(3, 25)
    benchmark_days = random.randint(7, 14)
    
    velocity_status = VelocityStatus.ON_TRACK.value
    if days_in_stage > benchmark_days * 1.5:
        velocity_status = VelocityStatus.STALLED.value
    elif days_in_stage > benchmark_days * 1.2:
        velocity_status = VelocityStatus.SLOW.value
    elif days_in_stage < benchmark_days * 0.7:
        velocity_status = VelocityStatus.FAST.value
    
    return {
        "deal_id": deal_id,
        "analyzed_at": now.isoformat(),
        "current_stage": current_stage,
        "velocity_status": velocity_status,
        "days_in_pipeline": random.randint(15, 90),
        "days_in_current_stage": days_in_stage,
        "benchmark_days_for_stage": benchmark_days,
        "deviation_from_benchmark": round((days_in_stage - benchmark_days) / benchmark_days * 100, 1),
        "stage_progress": [
            {
                "stage": "Lead",
                "days": random.randint(2, 7),
                "benchmark": 5,
                "status": "completed"
            },
            {
                "stage": "Discovery",
                "days": random.randint(5, 12),
                "benchmark": 7,
                "status": "completed"
            },
            {
                "stage": "Qualification",
                "days": random.randint(7, 15),
                "benchmark": 10,
                "status": "completed"
            },
            {
                "stage": current_stage,
                "days": days_in_stage,
                "benchmark": benchmark_days,
                "status": "current"
            }
        ],
        "velocity_score": random.randint(40, 95),
        "projected_close_date": (now + timedelta(days=random.randint(15, 60))).strftime("%Y-%m-%d"),
        "acceleration_opportunities": [
            {"action": "Add executive sponsor", "potential_impact": "-5 days"},
            {"action": "Provide custom ROI analysis", "potential_impact": "-3 days"},
            {"action": "Schedule technical deep-dive", "potential_impact": "-4 days"}
        ]
    }


@router.get("/pipeline")
async def get_pipeline_velocity(
    days: int = Query(default=30, ge=7, le=90),
    tenant_id: str = Query(default="default")
):
    """Get overall pipeline velocity metrics"""
    return {
        "period_days": days,
        "analyzed_at": datetime.utcnow().isoformat(),
        "summary": {
            "avg_sales_cycle_days": random.randint(35, 75),
            "median_sales_cycle_days": random.randint(30, 60),
            "deals_closed": random.randint(20, 80),
            "total_deals_in_pipeline": random.randint(50, 200),
            "pipeline_value": random.randint(1000000, 5000000),
            "velocity_score": random.randint(60, 90)
        },
        "velocity_breakdown": {
            "fast": {"count": random.randint(10, 30), "pct": round(random.uniform(0.15, 0.30), 2)},
            "on_track": {"count": random.randint(30, 80), "pct": round(random.uniform(0.40, 0.55), 2)},
            "slow": {"count": random.randint(15, 40), "pct": round(random.uniform(0.15, 0.25), 2)},
            "stalled": {"count": random.randint(5, 20), "pct": round(random.uniform(0.05, 0.15), 2)}
        },
        "by_stage": [
            {
                "stage": "Discovery",
                "avg_days": random.randint(5, 12),
                "benchmark_days": 7,
                "deals": random.randint(20, 50)
            },
            {
                "stage": "Qualification",
                "avg_days": random.randint(8, 18),
                "benchmark_days": 10,
                "deals": random.randint(15, 40)
            },
            {
                "stage": "Demo",
                "avg_days": random.randint(10, 20),
                "benchmark_days": 12,
                "deals": random.randint(12, 35)
            },
            {
                "stage": "Proposal",
                "avg_days": random.randint(12, 25),
                "benchmark_days": 14,
                "deals": random.randint(10, 30)
            },
            {
                "stage": "Negotiation",
                "avg_days": random.randint(8, 18),
                "benchmark_days": 10,
                "deals": random.randint(8, 25)
            }
        ],
        "trends": {
            "velocity_change_vs_prior_period": round(random.uniform(-10, 15), 1),
            "avg_cycle_change": round(random.uniform(-5, 8), 1),
            "win_rate": round(random.uniform(0.20, 0.35), 2)
        }
    }


# Stage Benchmarks
@router.post("/benchmarks")
async def create_stage_benchmark(
    request: StageThresholdCreate,
    tenant_id: str = Query(default="default")
):
    """Create or update stage benchmark"""
    benchmark_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    benchmark = {
        "id": benchmark_id,
        "stage_name": request.stage_name,
        "category": request.category.value,
        "target_days": request.target_days,
        "warning_days": request.warning_days,
        "critical_days": request.critical_days,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    stage_benchmarks[benchmark_id] = benchmark
    
    return benchmark


@router.get("/benchmarks")
async def list_stage_benchmarks(
    category: Optional[StageCategory] = None,
    tenant_id: str = Query(default="default")
):
    """List all stage benchmarks"""
    result = [b for b in stage_benchmarks.values() if b.get("tenant_id") == tenant_id]
    
    if category:
        result = [b for b in result if b.get("category") == category.value]
    
    # Add default benchmarks if none exist
    if not result:
        result = [
            {"stage_name": "Lead", "target_days": 5, "warning_days": 7, "critical_days": 10},
            {"stage_name": "Discovery", "target_days": 7, "warning_days": 10, "critical_days": 14},
            {"stage_name": "Qualification", "target_days": 10, "warning_days": 14, "critical_days": 21},
            {"stage_name": "Demo", "target_days": 12, "warning_days": 18, "critical_days": 25},
            {"stage_name": "Proposal", "target_days": 14, "warning_days": 21, "critical_days": 30},
            {"stage_name": "Negotiation", "target_days": 10, "warning_days": 15, "critical_days": 21}
        ]
    
    return {"benchmarks": result, "total": len(result)}


# Stalled Deals
@router.get("/stalled")
async def get_stalled_deals(
    min_days: int = Query(default=14, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    tenant_id: str = Query(default="default")
):
    """Get stalled deals that need attention"""
    stalled_deals = [
        {
            "deal_id": f"deal_{i}",
            "deal_name": f"Stalled Enterprise Deal {i + 1}",
            "stage": random.choice(["Discovery", "Qualification", "Demo", "Proposal"]),
            "days_stalled": random.randint(min_days, min_days + 30),
            "deal_value": random.randint(25000, 250000),
            "owner": f"rep_{random.randint(1, 5)}",
            "last_activity": (datetime.utcnow() - timedelta(days=random.randint(7, 30))).isoformat(),
            "stall_reason": random.choice([
                "No response from prospect",
                "Waiting for internal approval",
                "Champion went dark",
                "Budget freeze",
                "Competitor evaluation"
            ]),
            "recommended_action": random.choice([
                "Schedule check-in call",
                "Escalate to executive sponsor",
                "Send breakup email",
                "Offer limited-time incentive",
                "Request meeting with champion's manager"
            ])
        }
        for i in range(random.randint(10, 30))
    ]
    
    # Sort by days stalled descending
    stalled_deals = sorted(stalled_deals, key=lambda x: x["days_stalled"], reverse=True)
    
    return {
        "stalled_deals": stalled_deals[:limit],
        "total": len(stalled_deals),
        "total_value_at_risk": sum(d["deal_value"] for d in stalled_deals)
    }


# Acceleration Recommendations
@router.get("/accelerate/{deal_id}")
async def get_acceleration_recommendations(
    deal_id: str,
    tenant_id: str = Query(default="default")
):
    """Get recommendations to accelerate a deal"""
    return {
        "deal_id": deal_id,
        "current_velocity": random.choice(["slow", "on_track"]),
        "recommendations": [
            {
                "priority": "high",
                "action": "Add multi-threading",
                "description": "Engage additional stakeholders to build consensus faster",
                "expected_impact": "-5 to -10 days",
                "effort": "medium",
                "success_rate": "78%"
            },
            {
                "priority": "high",
                "action": "Executive alignment call",
                "description": "Schedule call between your exec and their exec",
                "expected_impact": "-7 to -14 days",
                "effort": "high",
                "success_rate": "65%"
            },
            {
                "priority": "medium",
                "action": "Proof of Value",
                "description": "Propose a limited POV to reduce perceived risk",
                "expected_impact": "-10 to -20 days",
                "effort": "high",
                "success_rate": "72%"
            },
            {
                "priority": "medium",
                "action": "Reference customer call",
                "description": "Connect prospect with similar customer",
                "expected_impact": "-3 to -7 days",
                "effort": "low",
                "success_rate": "81%"
            },
            {
                "priority": "low",
                "action": "Custom ROI analysis",
                "description": "Provide detailed ROI specific to their business",
                "expected_impact": "-2 to -5 days",
                "effort": "medium",
                "success_rate": "68%"
            }
        ],
        "similar_deals_that_accelerated": [
            {
                "deal": "Similar Corp A",
                "action_taken": "Executive alignment",
                "days_saved": 12
            },
            {
                "deal": "Similar Corp B",
                "action_taken": "POV",
                "days_saved": 18
            }
        ]
    }


# Velocity by Segment
@router.get("/by-segment")
async def get_velocity_by_segment(
    segment_by: str = Query(default="deal_size"),
    tenant_id: str = Query(default="default")
):
    """Get velocity metrics segmented by different dimensions"""
    segments = []
    
    if segment_by == "deal_size":
        segments = [
            {"segment": "SMB ($0-$25K)", "avg_cycle_days": random.randint(20, 35), "count": random.randint(30, 80)},
            {"segment": "Mid-Market ($25K-$100K)", "avg_cycle_days": random.randint(35, 55), "count": random.randint(20, 50)},
            {"segment": "Enterprise ($100K-$500K)", "avg_cycle_days": random.randint(55, 85), "count": random.randint(10, 30)},
            {"segment": "Strategic ($500K+)", "avg_cycle_days": random.randint(85, 150), "count": random.randint(3, 12)}
        ]
    elif segment_by == "industry":
        segments = [
            {"segment": "Technology", "avg_cycle_days": random.randint(25, 45), "count": random.randint(30, 70)},
            {"segment": "Healthcare", "avg_cycle_days": random.randint(45, 75), "count": random.randint(15, 40)},
            {"segment": "Financial Services", "avg_cycle_days": random.randint(50, 80), "count": random.randint(15, 35)},
            {"segment": "Manufacturing", "avg_cycle_days": random.randint(40, 65), "count": random.randint(10, 30)},
            {"segment": "Retail", "avg_cycle_days": random.randint(30, 50), "count": random.randint(20, 50)}
        ]
    elif segment_by == "source":
        segments = [
            {"segment": "Inbound", "avg_cycle_days": random.randint(25, 40), "count": random.randint(40, 100)},
            {"segment": "Outbound", "avg_cycle_days": random.randint(35, 55), "count": random.randint(30, 70)},
            {"segment": "Partner", "avg_cycle_days": random.randint(30, 50), "count": random.randint(15, 40)},
            {"segment": "Referral", "avg_cycle_days": random.randint(20, 35), "count": random.randint(10, 30)}
        ]
    
    return {
        "segment_by": segment_by,
        "segments": segments,
        "overall_avg": round(sum(s["avg_cycle_days"] for s in segments) / len(segments), 1)
    }


# Rep Performance
@router.get("/by-rep")
async def get_velocity_by_rep(
    tenant_id: str = Query(default="default")
):
    """Get velocity metrics by sales rep"""
    return {
        "reps": [
            {
                "rep_id": f"rep_{i}",
                "name": f"Sales Rep {i + 1}",
                "avg_cycle_days": random.randint(30, 65),
                "deals_closed": random.randint(3, 15),
                "velocity_score": random.randint(55, 95),
                "stalled_deals": random.randint(0, 5),
                "best_in": random.choice(["Discovery", "Demo", "Negotiation"])
            }
            for i in range(8)
        ],
        "team_avg_cycle_days": random.randint(40, 55)
    }


# Trends
@router.get("/trends")
async def get_velocity_trends(
    periods: int = Query(default=6, ge=3, le=12),
    period_type: str = Query(default="month"),
    tenant_id: str = Query(default="default")
):
    """Get velocity trends over time"""
    now = datetime.utcnow()
    trends = []
    
    base_cycle = random.randint(40, 55)
    for i in range(periods):
        period_date = now - timedelta(days=30 * i) if period_type == "month" else now - timedelta(days=7 * i)
        trends.append({
            "period": period_date.strftime("%Y-%m") if period_type == "month" else period_date.strftime("%Y-W%W"),
            "avg_cycle_days": base_cycle + random.randint(-8, 8),
            "deals_closed": random.randint(10, 40),
            "velocity_score": random.randint(60, 85),
            "stage_with_most_delay": random.choice(["Discovery", "Proposal", "Negotiation"])
        })
    
    return {
        "period_type": period_type,
        "trends": list(reversed(trends)),
        "improvement_pct": round(random.uniform(-10, 20), 1)
    }


# Bottleneck Analysis
@router.get("/bottlenecks")
async def analyze_bottlenecks(
    tenant_id: str = Query(default="default")
):
    """Identify pipeline bottlenecks"""
    return {
        "bottlenecks": [
            {
                "stage": "Proposal",
                "severity": "high",
                "avg_delay_days": random.randint(5, 12),
                "affected_deals": random.randint(15, 40),
                "value_at_risk": random.randint(500000, 2000000),
                "root_causes": [
                    "Proposal template delays",
                    "Pricing approvals taking too long",
                    "Legal review backlog"
                ],
                "recommendations": [
                    "Streamline pricing approval process",
                    "Create more proposal templates",
                    "Add dedicated legal support"
                ]
            },
            {
                "stage": "Discovery",
                "severity": "medium",
                "avg_delay_days": random.randint(3, 7),
                "affected_deals": random.randint(10, 25),
                "value_at_risk": random.randint(200000, 800000),
                "root_causes": [
                    "Difficulty scheduling meetings",
                    "Incomplete qualification"
                ],
                "recommendations": [
                    "Implement better scheduling tools",
                    "Improve qualification criteria"
                ]
            }
        ],
        "total_delay_cost_estimate": random.randint(100000, 500000),
        "potential_revenue_acceleration": random.randint(500000, 2000000)
    }


# Compare Deals
@router.get("/compare")
async def compare_deal_velocities(
    deal_ids: str = Query(description="Comma-separated deal IDs"),
    tenant_id: str = Query(default="default")
):
    """Compare velocity between multiple deals"""
    deals = deal_ids.split(",")
    
    comparisons = [
        {
            "deal_id": deal_id.strip(),
            "days_in_pipeline": random.randint(15, 80),
            "current_stage": random.choice(["Discovery", "Demo", "Proposal"]),
            "velocity_score": random.randint(40, 95),
            "status": random.choice(list(VelocityStatus)).value,
            "projected_close": (datetime.utcnow() + timedelta(days=random.randint(15, 60))).strftime("%Y-%m-%d")
        }
        for deal_id in deals
    ]
    
    return {
        "comparisons": comparisons,
        "fastest": max(comparisons, key=lambda x: x["velocity_score"])["deal_id"],
        "slowest": min(comparisons, key=lambda x: x["velocity_score"])["deal_id"]
    }
