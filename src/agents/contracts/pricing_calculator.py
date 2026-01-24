"""PricingCalculatorAgent - Calculate service pricing and generate quotes.

Handles dynamic pricing, discounts, package bundling, and quote generation.
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from enum import Enum

from src.agents.base import BaseAgent
from src.logger import get_logger

logger = get_logger(__name__)


class PricingModel(str, Enum):
    """Pricing models."""
    FIXED = "fixed"
    HOURLY = "hourly"
    VALUE_BASED = "value_based"
    RETAINER = "retainer"
    SUCCESS_FEE = "success_fee"
    HYBRID = "hybrid"


class DiscountType(str, Enum):
    """Types of discounts."""
    VOLUME = "volume"          # Multiple services
    LOYALTY = "loyalty"        # Returning client
    REFERRAL = "referral"      # Referred by partner
    EARLY_BIRD = "early_bird"  # Quick commitment
    STRATEGIC = "strategic"    # Strategic account


class PricingCalculatorAgent(BaseAgent):
    """Calculates pricing and generates quotes.
    
    Features:
    - Dynamic pricing based on scope
    - Automatic discount application
    - Package bundling optimization
    - Competitive pricing analysis
    - Quote generation with options
    
    Example:
        agent = PricingCalculatorAgent()
        result = await agent.execute({
            "action": "calculate",
            "services": ["strategy", "implementation"],
            "scope": {"complexity": "medium", "duration_weeks": 8},
            "discounts": ["volume"],
        })
    """

    # Base service pricing
    SERVICE_PRICING = {
        "strategy": {
            "name": "Strategy Engagement",
            "base_rate": 8000,
            "hourly_rate": 250,
            "min_hours": 30,
            "complexity_multipliers": {
                "low": 0.8,
                "medium": 1.0,
                "high": 1.3,
                "enterprise": 1.6,
            },
        },
        "implementation": {
            "name": "Implementation Services",
            "base_rate": 15000,
            "hourly_rate": 175,
            "min_hours": 80,
            "complexity_multipliers": {
                "low": 0.8,
                "medium": 1.0,
                "high": 1.25,
                "enterprise": 1.5,
            },
        },
        "retainer": {
            "name": "Monthly Retainer",
            "base_rate": 5000,
            "hourly_rate": 200,
            "min_hours": 20,
            "tiers": {
                "basic": {"hours": 20, "rate": 5000},
                "standard": {"hours": 40, "rate": 8500},
                "premium": {"hours": 60, "rate": 12000},
            },
        },
        "audit": {
            "name": "Audit & Assessment",
            "base_rate": 4000,
            "hourly_rate": 225,
            "min_hours": 16,
        },
        "training": {
            "name": "Training & Workshops",
            "base_rate": 2500,
            "daily_rate": 2500,
            "half_day_rate": 1500,
        },
    }

    # Discount rules
    DISCOUNT_RULES = {
        DiscountType.VOLUME: {
            "2_services": 0.05,    # 5% for 2 services
            "3_services": 0.10,   # 10% for 3+
            "5_services": 0.15,   # 15% for 5+
        },
        DiscountType.LOYALTY: {
            "returning": 0.05,
            "2_years": 0.10,
            "5_years": 0.15,
        },
        DiscountType.REFERRAL: {
            "standard": 0.05,
            "partner": 0.10,
        },
        DiscountType.EARLY_BIRD: {
            "7_days": 0.10,       # Sign within 7 days
            "14_days": 0.05,      # Sign within 14 days
        },
        DiscountType.STRATEGIC: {
            "logo_value": 0.10,   # High-profile logo
            "case_study": 0.05,   # Agrees to case study
        },
    }

    def __init__(self):
        """Initialize pricing calculator."""
        super().__init__(
            name="Pricing Calculator Agent",
            description="Calculates service pricing and generates quotes"
        )
        
        # Quote history
        self._quotes: Dict[str, Dict[str, Any]] = {}

    async def validate_input(self, context: Dict[str, Any]) -> bool:
        """Validate input."""
        action = context.get("action", "calculate")
        if action == "calculate":
            return "services" in context or "service" in context
        return True

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute pricing calculation."""
        action = context.get("action", "calculate")
        
        if action == "calculate":
            return await self._calculate_pricing(context)
        elif action == "generate_quote":
            return await self._generate_quote(context)
        elif action == "compare_options":
            return await self._compare_options(context)
        elif action == "get_services":
            return await self._get_services()
        elif action == "apply_discount":
            return await self._apply_discount(context)
        else:
            return {"status": "error", "error": f"Unknown action: {action}"}

    async def _calculate_pricing(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate pricing for services."""
        # Get services list
        services = context.get("services", [context.get("service")])
        if not services or services == [None]:
            return {"status": "error", "error": "No services specified"}
        
        scope = context.get("scope", {})
        complexity = scope.get("complexity", "medium")
        duration_weeks = scope.get("duration_weeks", 4)
        
        # Calculate each service
        line_items = []
        subtotal = 0
        
        for service_id in services:
            if service_id not in self.SERVICE_PRICING:
                continue
            
            service = self.SERVICE_PRICING[service_id]
            
            # Base calculation
            base_price = service["base_rate"]
            
            # Apply complexity multiplier
            multiplier = service.get("complexity_multipliers", {}).get(complexity, 1.0)
            adjusted_price = base_price * multiplier
            
            # Duration adjustment for longer projects
            if duration_weeks > 4:
                duration_factor = 1 + ((duration_weeks - 4) * 0.05)  # 5% per extra week
                adjusted_price *= duration_factor
            
            line_items.append({
                "service_id": service_id,
                "name": service["name"],
                "base_price": base_price,
                "complexity": complexity,
                "multiplier": multiplier,
                "calculated_price": round(adjusted_price, 2),
            })
            
            subtotal += adjusted_price
        
        # Calculate discounts
        discounts_requested = context.get("discounts", [])
        total_discount = 0
        applied_discounts = []
        
        # Volume discount
        if len(services) >= 2:
            volume_discount = self._get_volume_discount(len(services))
            if volume_discount > 0:
                total_discount += volume_discount
                applied_discounts.append({
                    "type": DiscountType.VOLUME.value,
                    "rate": volume_discount,
                    "reason": f"{len(services)} services bundled",
                })
        
        # Other discounts
        for discount_type in discounts_requested:
            if discount_type == "volume":
                continue  # Already handled
            discount_rate = self._get_discount_rate(discount_type, context)
            if discount_rate > 0:
                total_discount += discount_rate
                applied_discounts.append({
                    "type": discount_type,
                    "rate": discount_rate,
                })
        
        # Cap total discount at 25%
        total_discount = min(0.25, total_discount)
        discount_amount = subtotal * total_discount
        total = subtotal - discount_amount
        
        return {
            "status": "success",
            "pricing": {
                "line_items": line_items,
                "subtotal": round(subtotal, 2),
                "discounts": applied_discounts,
                "total_discount_rate": round(total_discount * 100, 1),
                "discount_amount": round(discount_amount, 2),
                "total": round(total, 2),
                "scope": {
                    "complexity": complexity,
                    "duration_weeks": duration_weeks,
                },
            },
        }

    async def _generate_quote(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a formal quote document."""
        # First calculate pricing
        pricing_result = await self._calculate_pricing(context)
        if pricing_result["status"] != "success":
            return pricing_result
        
        quote_id = f"quote-{datetime.utcnow().timestamp()}"
        pricing = pricing_result["pricing"]
        
        quote = {
            "id": quote_id,
            "client_name": context.get("client_name", "Prospective Client"),
            "client_email": context.get("client_email"),
            "prepared_by": context.get("prepared_by", "Casey"),
            "created_at": datetime.utcnow().isoformat(),
            "valid_until": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            "pricing": pricing,
            "payment_options": self._get_payment_options(pricing["total"]),
            "terms": {
                "payment_terms": "50% upon signing, 50% upon completion",
                "cancellation": "30 days written notice",
                "validity": "30 days from issue date",
            },
            "notes": context.get("notes", ""),
        }
        
        self._quotes[quote_id] = quote
        
        logger.info(f"Generated quote {quote_id}: ${pricing['total']:,.2f}")
        
        return {
            "status": "success",
            "quote": quote,
        }

    async def _compare_options(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate multiple pricing options for comparison."""
        base_services = context.get("services", ["strategy"])
        
        options = []
        
        # Option 1: Essential (base services only)
        essential = await self._calculate_pricing({
            "services": base_services[:1],
            "scope": context.get("scope", {}),
        })
        if essential["status"] == "success":
            options.append({
                "name": "Essential",
                "description": "Core engagement focused on key deliverables",
                **essential["pricing"],
            })
        
        # Option 2: Recommended (all requested services)
        recommended = await self._calculate_pricing({
            "services": base_services,
            "scope": context.get("scope", {}),
            "discounts": ["volume"],
        })
        if recommended["status"] == "success":
            options.append({
                "name": "Recommended",
                "description": "Comprehensive engagement for maximum impact",
                "recommended": True,
                **recommended["pricing"],
            })
        
        # Option 3: Premium (add retainer)
        premium_services = base_services + ["retainer"]
        premium = await self._calculate_pricing({
            "services": premium_services,
            "scope": context.get("scope", {}),
            "discounts": ["volume"],
        })
        if premium["status"] == "success":
            options.append({
                "name": "Premium Partnership",
                "description": "Full engagement plus ongoing strategic support",
                **premium["pricing"],
            })
        
        return {
            "status": "success",
            "options": options,
        }

    async def _get_services(self) -> Dict[str, Any]:
        """Get available services and pricing."""
        return {
            "status": "success",
            "services": self.SERVICE_PRICING,
        }

    async def _apply_discount(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Apply a discount to an existing quote."""
        quote_id = context.get("quote_id")
        discount_type = context.get("discount_type")
        discount_rate = context.get("discount_rate")
        
        if quote_id not in self._quotes:
            return {"status": "error", "error": f"Quote not found: {quote_id}"}
        
        quote = self._quotes[quote_id]
        
        # Apply additional discount
        additional_discount = discount_rate or self._get_discount_rate(discount_type, context)
        
        current_total = quote["pricing"]["total"]
        new_discount_amount = current_total * additional_discount
        new_total = current_total - new_discount_amount
        
        quote["pricing"]["applied_discounts"] = quote["pricing"].get("discounts", []) + [{
            "type": discount_type,
            "rate": additional_discount,
            "amount": new_discount_amount,
        }]
        quote["pricing"]["total"] = round(new_total, 2)
        quote["updated_at"] = datetime.utcnow().isoformat()
        
        return {
            "status": "success",
            "quote": quote,
            "discount_applied": {
                "type": discount_type,
                "rate": additional_discount,
                "savings": round(new_discount_amount, 2),
            },
        }

    def _get_volume_discount(self, service_count: int) -> float:
        """Get volume discount based on service count."""
        volume_rules = self.DISCOUNT_RULES[DiscountType.VOLUME]
        
        if service_count >= 5:
            return volume_rules["5_services"]
        elif service_count >= 3:
            return volume_rules["3_services"]
        elif service_count >= 2:
            return volume_rules["2_services"]
        return 0.0

    def _get_discount_rate(self, discount_type: str, context: Dict[str, Any]) -> float:
        """Get discount rate for a specific type."""
        try:
            dtype = DiscountType(discount_type)
        except ValueError:
            return 0.0
        
        rules = self.DISCOUNT_RULES.get(dtype, {})
        
        if dtype == DiscountType.LOYALTY:
            tenure = context.get("client_tenure_years", 0)
            if tenure >= 5:
                return rules.get("5_years", 0.15)
            elif tenure >= 2:
                return rules.get("2_years", 0.10)
            elif tenure >= 1:
                return rules.get("returning", 0.05)
        
        elif dtype == DiscountType.REFERRAL:
            referrer = context.get("referrer_type", "standard")
            return rules.get(referrer, 0.05)
        
        elif dtype == DiscountType.EARLY_BIRD:
            commitment_days = context.get("commitment_days", 30)
            if commitment_days <= 7:
                return rules.get("7_days", 0.10)
            elif commitment_days <= 14:
                return rules.get("14_days", 0.05)
        
        elif dtype == DiscountType.STRATEGIC:
            if context.get("logo_value"):
                return rules.get("logo_value", 0.10)
            elif context.get("case_study"):
                return rules.get("case_study", 0.05)
        
        return 0.0

    def _get_payment_options(self, total: float) -> List[Dict[str, Any]]:
        """Generate payment options for a total."""
        return [
            {
                "name": "Standard",
                "description": "50% upfront, 50% on completion",
                "upfront": round(total * 0.50, 2),
                "on_completion": round(total * 0.50, 2),
            },
            {
                "name": "Milestone-Based",
                "description": "Split across 3 milestones",
                "milestone_1": round(total * 0.33, 2),
                "milestone_2": round(total * 0.33, 2),
                "milestone_3": round(total * 0.34, 2),
            },
            {
                "name": "Monthly",
                "description": "Equal monthly payments over 3 months",
                "monthly_amount": round(total / 3, 2),
                "total_months": 3,
            },
        ]
