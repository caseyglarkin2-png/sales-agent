"""RevenueOpsAgent - Pipeline and revenue operations intelligence.

Tracks pipeline health, revenue metrics, forecasting, and deal analytics.
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from enum import Enum

from src.agents.base import BaseAgent
from src.logger import get_logger

logger = get_logger(__name__)


class DealStage(str, Enum):
    """Standard deal stages."""
    LEAD = "lead"
    QUALIFIED = "qualified"
    DISCOVERY = "discovery"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


class MetricType(str, Enum):
    """Revenue metrics."""
    ARR = "arr"                    # Annual recurring revenue
    MRR = "mrr"                    # Monthly recurring revenue
    PIPELINE = "pipeline"          # Total pipeline value
    FORECAST = "forecast"          # Weighted pipeline
    AVG_DEAL_SIZE = "avg_deal_size"
    WIN_RATE = "win_rate"
    SALES_CYCLE = "sales_cycle"    # Days to close
    VELOCITY = "velocity"          # Pipeline velocity


class RevenueOpsAgent(BaseAgent):
    """Provides pipeline and revenue operations intelligence.
    
    Features:
    - Pipeline health monitoring
    - Revenue metrics tracking
    - Deal velocity analysis
    - Forecast generation
    - At-risk deal identification
    - Conversion funnel analysis
    
    Example:
        agent = RevenueOpsAgent(hubspot_connector)
        result = await agent.execute({
            "action": "pipeline_health",
            "period": "current_quarter",
        })
    """

    # Stage probabilities for weighted pipeline
    STAGE_PROBABILITIES = {
        DealStage.LEAD.value: 0.05,
        DealStage.QUALIFIED.value: 0.15,
        DealStage.DISCOVERY.value: 0.30,
        DealStage.PROPOSAL.value: 0.50,
        DealStage.NEGOTIATION.value: 0.75,
        DealStage.CLOSED_WON.value: 1.0,
        DealStage.CLOSED_LOST.value: 0.0,
    }

    def __init__(self, hubspot_connector=None):
        """Initialize revenue ops agent."""
        super().__init__(
            name="Revenue Ops Agent",
            description="Provides pipeline and revenue operations intelligence"
        )
        self.hubspot_connector = hubspot_connector
        
        # In-memory deal storage (would come from HubSpot in production)
        self._deals: Dict[str, Dict[str, Any]] = {}
        self._metrics_history: List[Dict[str, Any]] = []

    async def validate_input(self, context: Dict[str, Any]) -> bool:
        """Validate input."""
        return True  # Most actions don't require specific inputs

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute revenue ops action."""
        action = context.get("action", "dashboard")
        
        if action == "dashboard":
            return await self._get_dashboard(context)
        elif action == "pipeline_health":
            return await self._pipeline_health(context)
        elif action == "forecast":
            return await self._generate_forecast(context)
        elif action == "at_risk_deals":
            return await self._get_at_risk_deals(context)
        elif action == "funnel":
            return await self._analyze_funnel(context)
        elif action == "velocity":
            return await self._analyze_velocity(context)
        elif action == "add_deal":
            return await self._add_deal(context)
        elif action == "update_deal":
            return await self._update_deal(context)
        else:
            return {"status": "error", "error": f"Unknown action: {action}"}

    async def _get_dashboard(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get comprehensive revenue dashboard."""
        period = context.get("period", "current_month")
        
        # Get all active deals
        active_deals = [
            d for d in self._deals.values()
            if d["stage"] not in [DealStage.CLOSED_WON.value, DealStage.CLOSED_LOST.value]
        ]
        
        # Calculate metrics
        total_pipeline = sum(d["amount"] for d in active_deals)
        weighted_pipeline = sum(
            d["amount"] * self.STAGE_PROBABILITIES.get(d["stage"], 0)
            for d in active_deals
        )
        
        won_deals = [d for d in self._deals.values() if d["stage"] == DealStage.CLOSED_WON.value]
        lost_deals = [d for d in self._deals.values() if d["stage"] == DealStage.CLOSED_LOST.value]
        
        total_closed = len(won_deals) + len(lost_deals)
        win_rate = (len(won_deals) / total_closed * 100) if total_closed > 0 else 0
        
        revenue_won = sum(d["amount"] for d in won_deals)
        avg_deal_size = (revenue_won / len(won_deals)) if won_deals else 0
        
        # Deal count by stage
        by_stage = {}
        for stage in DealStage:
            stage_deals = [d for d in self._deals.values() if d["stage"] == stage.value]
            by_stage[stage.value] = {
                "count": len(stage_deals),
                "value": sum(d["amount"] for d in stage_deals),
            }
        
        return {
            "status": "success",
            "dashboard": {
                "period": period,
                "generated_at": datetime.utcnow().isoformat(),
                "summary": {
                    "total_pipeline": total_pipeline,
                    "weighted_pipeline": round(weighted_pipeline, 2),
                    "active_deals": len(active_deals),
                    "win_rate": round(win_rate, 1),
                    "avg_deal_size": round(avg_deal_size, 2),
                    "revenue_won": revenue_won,
                },
                "by_stage": by_stage,
                "top_deals": sorted(active_deals, key=lambda x: x["amount"], reverse=True)[:5],
            },
        }

    async def _pipeline_health(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze pipeline health and identify issues."""
        active_deals = [
            d for d in self._deals.values()
            if d["stage"] not in [DealStage.CLOSED_WON.value, DealStage.CLOSED_LOST.value]
        ]
        
        health_issues = []
        
        # Check for stalled deals
        stalled = []
        for deal in active_deals:
            last_activity = datetime.fromisoformat(deal.get("last_activity", deal["created_at"]))
            days_stalled = (datetime.utcnow() - last_activity).days
            if days_stalled > 14:
                stalled.append({
                    "deal": deal["name"],
                    "stage": deal["stage"],
                    "days_stalled": days_stalled,
                    "amount": deal["amount"],
                })
        
        if stalled:
            health_issues.append({
                "issue": "Stalled deals",
                "severity": "high" if len(stalled) > 3 else "medium",
                "count": len(stalled),
                "details": stalled[:5],
            })
        
        # Check stage distribution
        stage_counts = {}
        for deal in active_deals:
            stage_counts[deal["stage"]] = stage_counts.get(deal["stage"], 0) + 1
        
        # Alert if pipeline is top-heavy (too many in early stages)
        early_stage = stage_counts.get(DealStage.LEAD.value, 0) + stage_counts.get(DealStage.QUALIFIED.value, 0)
        late_stage = stage_counts.get(DealStage.PROPOSAL.value, 0) + stage_counts.get(DealStage.NEGOTIATION.value, 0)
        
        if early_stage > late_stage * 3:
            health_issues.append({
                "issue": "Top-heavy pipeline",
                "severity": "medium",
                "details": "Too many deals in early stages. Focus on advancing current opportunities.",
            })
        
        # Check coverage
        target = context.get("target", 100000)
        weighted = sum(d["amount"] * self.STAGE_PROBABILITIES.get(d["stage"], 0) for d in active_deals)
        coverage = weighted / target if target > 0 else 0
        
        if coverage < 1.5:
            health_issues.append({
                "issue": "Low pipeline coverage",
                "severity": "high" if coverage < 1.0 else "medium",
                "details": f"Coverage ratio is {coverage:.1f}x. Recommend 3x target.",
            })
        
        # Overall health score
        health_score = 100
        for issue in health_issues:
            if issue["severity"] == "high":
                health_score -= 25
            elif issue["severity"] == "medium":
                health_score -= 10
        health_score = max(0, health_score)
        
        return {
            "status": "success",
            "pipeline_health": {
                "health_score": health_score,
                "health_status": "healthy" if health_score >= 80 else "needs_attention" if health_score >= 50 else "critical",
                "issues": health_issues,
                "metrics": {
                    "total_deals": len(active_deals),
                    "total_value": sum(d["amount"] for d in active_deals),
                    "weighted_value": round(weighted, 2),
                    "coverage_ratio": round(coverage, 2),
                },
            },
        }

    async def _generate_forecast(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate revenue forecast."""
        period = context.get("period", "current_quarter")
        
        active_deals = [
            d for d in self._deals.values()
            if d["stage"] not in [DealStage.CLOSED_WON.value, DealStage.CLOSED_LOST.value]
        ]
        
        # Calculate different forecast scenarios
        best_case = sum(d["amount"] for d in active_deals)
        
        commit = sum(
            d["amount"] for d in active_deals
            if d["stage"] in [DealStage.NEGOTIATION.value, DealStage.PROPOSAL.value]
        )
        
        weighted = sum(
            d["amount"] * self.STAGE_PROBABILITIES.get(d["stage"], 0)
            for d in active_deals
        )
        
        # Already won
        won_deals = [d for d in self._deals.values() if d["stage"] == DealStage.CLOSED_WON.value]
        closed = sum(d["amount"] for d in won_deals)
        
        return {
            "status": "success",
            "forecast": {
                "period": period,
                "generated_at": datetime.utcnow().isoformat(),
                "closed": round(closed, 2),
                "commit": round(commit, 2),
                "best_case": round(best_case, 2),
                "weighted": round(weighted, 2),
                "expected_total": round(closed + weighted, 2),
                "by_stage": {
                    stage.value: sum(
                        d["amount"] for d in active_deals 
                        if d["stage"] == stage.value
                    )
                    for stage in DealStage
                },
            },
        }

    async def _get_at_risk_deals(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Identify at-risk deals."""
        active_deals = [
            d for d in self._deals.values()
            if d["stage"] not in [DealStage.CLOSED_WON.value, DealStage.CLOSED_LOST.value]
        ]
        
        at_risk = []
        
        for deal in active_deals:
            risk_factors = []
            risk_score = 0
            
            # Check for stalled activity
            last_activity = datetime.fromisoformat(deal.get("last_activity", deal["created_at"]))
            days_since_activity = (datetime.utcnow() - last_activity).days
            if days_since_activity > 14:
                risk_factors.append("No activity for 14+ days")
                risk_score += 30
            elif days_since_activity > 7:
                risk_factors.append("Low recent activity")
                risk_score += 15
            
            # Check for approaching close date
            if deal.get("expected_close"):
                close_date = datetime.fromisoformat(deal["expected_close"])
                days_until_close = (close_date - datetime.utcnow()).days
                if days_until_close < 0:
                    risk_factors.append("Past expected close date")
                    risk_score += 25
                elif days_until_close < 7:
                    risk_factors.append("Close date approaching")
                    risk_score += 10
            
            # Check for early stage with high value
            if deal["amount"] > 50000 and deal["stage"] in [DealStage.LEAD.value, DealStage.QUALIFIED.value]:
                risk_factors.append("High-value deal in early stage")
                risk_score += 15
            
            # Check for competitor involvement
            if deal.get("competitor_involved"):
                risk_factors.append("Competitor actively involved")
                risk_score += 20
            
            if risk_score > 25:
                at_risk.append({
                    "deal_id": deal["id"],
                    "name": deal["name"],
                    "amount": deal["amount"],
                    "stage": deal["stage"],
                    "risk_score": risk_score,
                    "risk_factors": risk_factors,
                    "recommended_action": self._recommend_action(risk_factors),
                })
        
        # Sort by risk score
        at_risk = sorted(at_risk, key=lambda x: x["risk_score"], reverse=True)
        
        return {
            "status": "success",
            "at_risk_deals": at_risk,
            "total_at_risk_value": sum(d["amount"] for d in at_risk),
        }

    async def _analyze_funnel(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze conversion funnel."""
        all_deals = list(self._deals.values())
        
        # Count by stage
        stage_counts = {stage.value: 0 for stage in DealStage}
        for deal in all_deals:
            stage_counts[deal["stage"]] += 1
        
        # Calculate conversion rates
        funnel = []
        stages = [DealStage.LEAD, DealStage.QUALIFIED, DealStage.DISCOVERY, 
                  DealStage.PROPOSAL, DealStage.NEGOTIATION, DealStage.CLOSED_WON]
        
        for i, stage in enumerate(stages):
            count = stage_counts.get(stage.value, 0)
            prev_count = stage_counts.get(stages[i-1].value, count) if i > 0 else count
            conversion_rate = (count / prev_count * 100) if prev_count > 0 else 0
            
            funnel.append({
                "stage": stage.value,
                "count": count,
                "conversion_rate": round(conversion_rate, 1) if i > 0 else 100,
            })
        
        # Calculate overall conversion
        total_leads = stage_counts.get(DealStage.LEAD.value, 0) + sum(
            stage_counts.get(s.value, 0) for s in stages[1:]
        )
        total_won = stage_counts.get(DealStage.CLOSED_WON.value, 0)
        overall_conversion = (total_won / total_leads * 100) if total_leads > 0 else 0
        
        return {
            "status": "success",
            "funnel": {
                "stages": funnel,
                "overall_conversion": round(overall_conversion, 1),
                "total_entered": total_leads,
                "total_won": total_won,
            },
        }

    async def _analyze_velocity(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze deal velocity (time through pipeline)."""
        won_deals = [d for d in self._deals.values() if d["stage"] == DealStage.CLOSED_WON.value]
        
        if not won_deals:
            return {
                "status": "success",
                "velocity": {
                    "avg_days_to_close": 0,
                    "deals_analyzed": 0,
                    "message": "No closed deals to analyze",
                },
            }
        
        # Calculate average days to close
        days_list = []
        for deal in won_deals:
            if deal.get("closed_at"):
                created = datetime.fromisoformat(deal["created_at"])
                closed = datetime.fromisoformat(deal["closed_at"])
                days = (closed - created).days
                days_list.append(days)
        
        avg_days = sum(days_list) / len(days_list) if days_list else 0
        
        # Calculate pipeline velocity (value * count * win_rate / cycle_time)
        active_deals = [
            d for d in self._deals.values()
            if d["stage"] not in [DealStage.CLOSED_WON.value, DealStage.CLOSED_LOST.value]
        ]
        
        pipeline_value = sum(d["amount"] for d in active_deals)
        deal_count = len(active_deals)
        
        total_closed = len(won_deals) + len([d for d in self._deals.values() if d["stage"] == DealStage.CLOSED_LOST.value])
        win_rate = len(won_deals) / total_closed if total_closed > 0 else 0
        
        velocity = (pipeline_value * deal_count * win_rate / avg_days) if avg_days > 0 else 0
        
        return {
            "status": "success",
            "velocity": {
                "avg_days_to_close": round(avg_days, 1),
                "deals_analyzed": len(days_list),
                "pipeline_value": pipeline_value,
                "win_rate": round(win_rate * 100, 1),
                "velocity_score": round(velocity, 2),
            },
        }

    async def _add_deal(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new deal."""
        deal_id = f"deal-{datetime.utcnow().timestamp()}"
        
        deal = {
            "id": deal_id,
            "name": context.get("name", "Unnamed Deal"),
            "company": context.get("company"),
            "amount": context.get("amount", 0),
            "stage": context.get("stage", DealStage.LEAD.value),
            "expected_close": context.get("expected_close"),
            "owner": context.get("owner", "casey"),
            "competitor_involved": context.get("competitor_involved", False),
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
        }
        
        self._deals[deal_id] = deal
        
        logger.info(f"Added deal: {deal['name']} - ${deal['amount']}")
        
        return {
            "status": "success",
            "deal": deal,
        }

    async def _update_deal(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Update a deal."""
        deal_id = context.get("deal_id")
        
        if deal_id not in self._deals:
            return {"status": "error", "error": f"Deal not found: {deal_id}"}
        
        deal = self._deals[deal_id]
        
        for field in ["stage", "amount", "expected_close", "owner", "competitor_involved"]:
            if field in context:
                deal[field] = context[field]
        
        deal["last_activity"] = datetime.utcnow().isoformat()
        
        # Track stage changes
        if "stage" in context and context["stage"] == DealStage.CLOSED_WON.value:
            deal["closed_at"] = datetime.utcnow().isoformat()
        
        return {
            "status": "success",
            "deal": deal,
        }

    def _recommend_action(self, risk_factors: List[str]) -> str:
        """Recommend action based on risk factors."""
        if "No activity for 14+ days" in risk_factors:
            return "Schedule an immediate check-in call"
        if "Past expected close date" in risk_factors:
            return "Confirm timeline and identify blockers"
        if "Competitor actively involved" in risk_factors:
            return "Request executive sponsor meeting"
        return "Review deal strategy and next steps"
