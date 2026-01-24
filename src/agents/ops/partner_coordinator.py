"""PartnerCoordinatorAgent - Manage partner relationships and activities.

Handles partner onboarding, co-sell opportunities, referral tracking, and
partner program management.
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from enum import Enum

from src.agents.base import BaseAgent
from src.logger import get_logger

logger = get_logger(__name__)


class PartnerType(str, Enum):
    """Types of partners."""
    REFERRAL = "referral"          # Sends referrals for fee
    RESELLER = "reseller"          # Sells our services
    TECHNOLOGY = "technology"      # Tech integration partner
    AGENCY = "agency"              # White-label/agency partner
    STRATEGIC = "strategic"        # Strategic alliance


class PartnerTier(str, Enum):
    """Partner program tiers."""
    REGISTERED = "registered"
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"


class ReferralStatus(str, Enum):
    """Status of a referral."""
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"
    EXPIRED = "expired"


class PartnerCoordinatorAgent(BaseAgent):
    """Manages partner relationships and activities.
    
    Features:
    - Partner profile management
    - Referral tracking and attribution
    - Co-sell opportunity management
    - Partner performance analytics
    - Partner communication automation
    
    Example:
        agent = PartnerCoordinatorAgent()
        result = await agent.execute({
            "action": "submit_referral",
            "partner_id": "partner-123",
            "referral": {
                "company": "Acme Corp",
                "contact_email": "john@acme.com",
                "estimated_value": 25000,
            },
        })
    """

    # Commission structure by tier
    COMMISSION_RATES = {
        PartnerTier.REGISTERED.value: 0.05,   # 5%
        PartnerTier.BRONZE.value: 0.10,       # 10%
        PartnerTier.SILVER.value: 0.15,       # 15%
        PartnerTier.GOLD.value: 0.20,         # 20%
        PartnerTier.PLATINUM.value: 0.25,     # 25%
    }

    def __init__(self, hubspot_connector=None, gmail_connector=None):
        """Initialize partner coordinator agent."""
        super().__init__(
            name="Partner Coordinator Agent",
            description="Manages partner relationships and referral programs"
        )
        self.hubspot_connector = hubspot_connector
        self.gmail_connector = gmail_connector
        
        # In-memory storage (would be DB in production)
        self._partners: Dict[str, Dict[str, Any]] = {}
        self._referrals: Dict[str, Dict[str, Any]] = {}
        self._activities: List[Dict[str, Any]] = []

    async def validate_input(self, context: Dict[str, Any]) -> bool:
        """Validate input."""
        action = context.get("action", "list_partners")
        if action == "add_partner":
            return "name" in context
        elif action == "submit_referral":
            return "partner_id" in context and "referral" in context
        return True

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute partner coordination action."""
        action = context.get("action", "list_partners")
        
        if action == "add_partner":
            return await self._add_partner(context)
        elif action == "submit_referral":
            return await self._submit_referral(context)
        elif action == "update_referral":
            return await self._update_referral(context)
        elif action == "list_partners":
            return await self._list_partners(context)
        elif action == "list_referrals":
            return await self._list_referrals(context)
        elif action == "partner_dashboard":
            return await self._partner_dashboard(context)
        elif action == "calculate_commission":
            return await self._calculate_commission(context)
        elif action == "log_activity":
            return await self._log_activity(context)
        else:
            return {"status": "error", "error": f"Unknown action: {action}"}

    async def _add_partner(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new partner."""
        partner_id = f"partner-{datetime.utcnow().timestamp()}"
        
        partner = {
            "id": partner_id,
            "name": context["name"],
            "company": context.get("company"),
            "email": context.get("email"),
            "phone": context.get("phone"),
            "partner_type": context.get("partner_type", PartnerType.REFERRAL.value),
            "tier": context.get("tier", PartnerTier.REGISTERED.value),
            "status": "active",
            "territory": context.get("territory"),
            "specializations": context.get("specializations", []),
            "referral_count": 0,
            "total_revenue": 0,
            "commission_earned": 0,
            "commission_paid": 0,
            "notes": context.get("notes", ""),
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
        }
        
        self._partners[partner_id] = partner
        
        logger.info(f"Added partner: {partner['name']}")
        
        return {
            "status": "success",
            "partner": partner,
            "message": f"Welcome to the partner program! Commission rate: {self.COMMISSION_RATES.get(partner['tier'], 0.05)*100}%",
        }

    async def _submit_referral(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Submit a new referral from a partner."""
        partner_id = context["partner_id"]
        
        if partner_id not in self._partners:
            return {"status": "error", "error": f"Partner not found: {partner_id}"}
        
        partner = self._partners[partner_id]
        referral_data = context["referral"]
        referral_id = f"ref-{datetime.utcnow().timestamp()}"
        
        referral = {
            "id": referral_id,
            "partner_id": partner_id,
            "partner_name": partner["name"],
            "company": referral_data.get("company"),
            "contact_name": referral_data.get("contact_name"),
            "contact_email": referral_data.get("contact_email"),
            "contact_phone": referral_data.get("contact_phone"),
            "estimated_value": referral_data.get("estimated_value", 0),
            "notes": referral_data.get("notes", ""),
            "status": ReferralStatus.SUBMITTED.value,
            "submitted_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(days=90)).isoformat(),  # 90-day attribution window
            "commission_rate": self.COMMISSION_RATES.get(partner["tier"], 0.05),
            "commission_amount": 0,
            "closed_value": 0,
        }
        
        self._referrals[referral_id] = referral
        
        # Update partner stats
        partner["referral_count"] += 1
        partner["last_activity"] = datetime.utcnow().isoformat()
        
        # Log activity
        await self._log_activity({
            "partner_id": partner_id,
            "activity_type": "referral_submitted",
            "details": f"Referral submitted for {referral['company']}",
        })
        
        logger.info(f"Referral submitted: {referral['company']} from {partner['name']}")
        
        return {
            "status": "success",
            "referral": referral,
            "message": f"Referral accepted! Attribution window: 90 days. Commission rate: {referral['commission_rate']*100}%",
        }

    async def _update_referral(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Update referral status."""
        referral_id = context.get("referral_id")
        
        if referral_id not in self._referrals:
            return {"status": "error", "error": f"Referral not found: {referral_id}"}
        
        referral = self._referrals[referral_id]
        new_status = context.get("status")
        
        if new_status:
            referral["status"] = new_status
            
            if new_status == ReferralStatus.CLOSED_WON.value:
                closed_value = context.get("closed_value", referral["estimated_value"])
                referral["closed_value"] = closed_value
                referral["commission_amount"] = closed_value * referral["commission_rate"]
                referral["closed_at"] = datetime.utcnow().isoformat()
                
                # Update partner totals
                partner = self._partners.get(referral["partner_id"])
                if partner:
                    partner["total_revenue"] += closed_value
                    partner["commission_earned"] += referral["commission_amount"]
                    
                    # Check for tier upgrade
                    new_tier = self._check_tier_upgrade(partner)
                    if new_tier != partner["tier"]:
                        partner["tier"] = new_tier
        
        return {
            "status": "success",
            "referral": referral,
        }

    async def _list_partners(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """List partners with optional filters."""
        partner_type = context.get("partner_type")
        tier = context.get("tier")
        status = context.get("status", "active")
        
        partners = list(self._partners.values())
        
        if partner_type:
            partners = [p for p in partners if p["partner_type"] == partner_type]
        if tier:
            partners = [p for p in partners if p["tier"] == tier]
        if status:
            partners = [p for p in partners if p["status"] == status]
        
        # Sort by total revenue
        partners = sorted(partners, key=lambda x: x["total_revenue"], reverse=True)
        
        return {
            "status": "success",
            "count": len(partners),
            "partners": partners,
        }

    async def _list_referrals(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """List referrals with optional filters."""
        partner_id = context.get("partner_id")
        status = context.get("status")
        
        referrals = list(self._referrals.values())
        
        if partner_id:
            referrals = [r for r in referrals if r["partner_id"] == partner_id]
        if status:
            referrals = [r for r in referrals if r["status"] == status]
        
        # Sort by submission date
        referrals = sorted(referrals, key=lambda x: x["submitted_at"], reverse=True)
        
        return {
            "status": "success",
            "count": len(referrals),
            "referrals": referrals,
        }

    async def _partner_dashboard(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get partner program dashboard."""
        partners = list(self._partners.values())
        referrals = list(self._referrals.values())
        
        # Summary stats
        active_partners = len([p for p in partners if p["status"] == "active"])
        total_referrals = len(referrals)
        pending_referrals = len([r for r in referrals if r["status"] in [ReferralStatus.SUBMITTED.value, ReferralStatus.IN_PROGRESS.value]])
        won_referrals = len([r for r in referrals if r["status"] == ReferralStatus.CLOSED_WON.value])
        
        total_revenue = sum(r["closed_value"] for r in referrals if r["status"] == ReferralStatus.CLOSED_WON.value)
        total_commission = sum(r["commission_amount"] for r in referrals if r["status"] == ReferralStatus.CLOSED_WON.value)
        commission_owed = sum(p["commission_earned"] - p["commission_paid"] for p in partners)
        
        # Conversion rate
        closed_referrals = len([r for r in referrals if r["status"] in [ReferralStatus.CLOSED_WON.value, ReferralStatus.CLOSED_LOST.value]])
        conversion_rate = (won_referrals / closed_referrals * 100) if closed_referrals > 0 else 0
        
        # Top partners
        top_partners = sorted(partners, key=lambda x: x["total_revenue"], reverse=True)[:5]
        
        # By tier
        by_tier = {}
        for tier in PartnerTier:
            tier_partners = [p for p in partners if p["tier"] == tier.value]
            by_tier[tier.value] = {
                "count": len(tier_partners),
                "revenue": sum(p["total_revenue"] for p in tier_partners),
            }
        
        return {
            "status": "success",
            "dashboard": {
                "generated_at": datetime.utcnow().isoformat(),
                "summary": {
                    "active_partners": active_partners,
                    "total_referrals": total_referrals,
                    "pending_referrals": pending_referrals,
                    "won_referrals": won_referrals,
                    "conversion_rate": round(conversion_rate, 1),
                    "total_revenue": total_revenue,
                    "total_commission": round(total_commission, 2),
                    "commission_owed": round(commission_owed, 2),
                },
                "by_tier": by_tier,
                "top_partners": [
                    {
                        "name": p["name"],
                        "tier": p["tier"],
                        "referrals": p["referral_count"],
                        "revenue": p["total_revenue"],
                    }
                    for p in top_partners
                ],
            },
        }

    async def _calculate_commission(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate commission for a partner."""
        partner_id = context.get("partner_id")
        
        if partner_id not in self._partners:
            return {"status": "error", "error": f"Partner not found: {partner_id}"}
        
        partner = self._partners[partner_id]
        
        # Get partner's won referrals
        won_referrals = [
            r for r in self._referrals.values()
            if r["partner_id"] == partner_id and r["status"] == ReferralStatus.CLOSED_WON.value
        ]
        
        total_commission = sum(r["commission_amount"] for r in won_referrals)
        paid = partner["commission_paid"]
        owed = total_commission - paid
        
        return {
            "status": "success",
            "commission": {
                "partner_id": partner_id,
                "partner_name": partner["name"],
                "tier": partner["tier"],
                "commission_rate": self.COMMISSION_RATES.get(partner["tier"], 0.05),
                "total_earned": round(total_commission, 2),
                "total_paid": round(paid, 2),
                "amount_owed": round(owed, 2),
                "referrals_paid": len(won_referrals),
            },
        }

    async def _log_activity(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Log partner activity."""
        activity = {
            "id": f"act-{datetime.utcnow().timestamp()}",
            "partner_id": context.get("partner_id"),
            "activity_type": context.get("activity_type", "other"),
            "details": context.get("details", ""),
            "logged_at": datetime.utcnow().isoformat(),
        }
        
        self._activities.append(activity)
        
        return {
            "status": "success",
            "activity": activity,
        }

    def _check_tier_upgrade(self, partner: Dict[str, Any]) -> str:
        """Check if partner qualifies for tier upgrade."""
        revenue = partner["total_revenue"]
        referrals = partner["referral_count"]
        
        if revenue >= 500000 or referrals >= 50:
            return PartnerTier.PLATINUM.value
        elif revenue >= 200000 or referrals >= 25:
            return PartnerTier.GOLD.value
        elif revenue >= 100000 or referrals >= 15:
            return PartnerTier.SILVER.value
        elif revenue >= 25000 or referrals >= 5:
            return PartnerTier.BRONZE.value
        else:
            return PartnerTier.REGISTERED.value
