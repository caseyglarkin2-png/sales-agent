"""
Pricing Engine Routes - Dynamic pricing, discounting rules, and price optimization
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

router = APIRouter(prefix="/pricing-engine", tags=["Pricing Engine"])


class PricingModel(str, Enum):
    FLAT_RATE = "flat_rate"
    PER_SEAT = "per_seat"
    USAGE_BASED = "usage_based"
    TIERED = "tiered"
    HYBRID = "hybrid"
    CUSTOM = "custom"


class DiscountType(str, Enum):
    PERCENTAGE = "percentage"
    FIXED = "fixed"
    VOLUME = "volume"
    PROMOTIONAL = "promotional"
    NEGOTIATED = "negotiated"
    BUNDLE = "bundle"


class PriceListStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    EXPIRED = "expired"
    ARCHIVED = "archived"


# In-memory storage
price_lists = {}
pricing_rules = {}
discount_policies = {}
price_calculations = {}


class ProductPricingCreate(BaseModel):
    product_id: str
    product_name: str
    pricing_model: PricingModel
    base_price: float
    currency: str = "USD"
    billing_frequency: str = "monthly"  # monthly, annual, one-time
    tiers: Optional[List[Dict[str, Any]]] = None


class DiscountRuleCreate(BaseModel):
    name: str
    discount_type: DiscountType
    value: float  # percentage or fixed amount
    min_deal_size: Optional[float] = None
    max_deal_size: Optional[float] = None
    min_quantity: Optional[int] = None
    product_ids: Optional[List[str]] = None
    requires_approval: bool = False
    approval_threshold: Optional[float] = None


class PriceCalculationRequest(BaseModel):
    product_id: str
    quantity: int = 1
    billing_frequency: str = "annual"
    customer_segment: Optional[str] = None
    discount_codes: Optional[List[str]] = None


# Price Lists
@router.post("/price-lists")
async def create_price_list(
    name: str,
    effective_date: datetime,
    expiration_date: Optional[datetime] = None,
    products: List[ProductPricingCreate] = [],
    tenant_id: str = Query(default="default")
):
    """Create a price list"""
    list_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    price_list = {
        "id": list_id,
        "name": name,
        "status": PriceListStatus.DRAFT.value,
        "effective_date": effective_date.isoformat(),
        "expiration_date": expiration_date.isoformat() if expiration_date else None,
        "products": [
            {
                "product_id": p.product_id,
                "product_name": p.product_name,
                "pricing_model": p.pricing_model.value,
                "base_price": p.base_price,
                "currency": p.currency,
                "billing_frequency": p.billing_frequency,
                "tiers": p.tiers
            }
            for p in products
        ],
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    price_lists[list_id] = price_list
    
    return price_list


@router.get("/price-lists")
async def list_price_lists(
    status: Optional[PriceListStatus] = None,
    active_only: bool = False,
    tenant_id: str = Query(default="default")
):
    """List price lists"""
    result = [pl for pl in price_lists.values() if pl.get("tenant_id") == tenant_id]
    
    if status:
        result = [pl for pl in result if pl.get("status") == status.value]
    
    if active_only:
        now = datetime.utcnow().isoformat()
        result = [pl for pl in result 
                  if pl.get("status") == PriceListStatus.ACTIVE.value
                  and pl.get("effective_date", "") <= now
                  and (not pl.get("expiration_date") or pl.get("expiration_date", "") > now)]
    
    return {"price_lists": result, "total": len(result)}


@router.post("/price-lists/{list_id}/activate")
async def activate_price_list(
    list_id: str,
    tenant_id: str = Query(default="default")
):
    """Activate a price list"""
    pl = price_lists.get(list_id)
    if not pl:
        raise HTTPException(status_code=404, detail="Price list not found")
    
    pl["status"] = PriceListStatus.ACTIVE.value
    pl["activated_at"] = datetime.utcnow().isoformat()
    
    return {"list_id": list_id, "status": "activated"}


# Price Calculation
@router.post("/calculate")
async def calculate_price(
    request: PriceCalculationRequest,
    tenant_id: str = Query(default="default")
):
    """Calculate price for a product"""
    base_price = random.uniform(50, 500)
    quantity = request.quantity
    
    # Apply quantity-based pricing
    if quantity >= 100:
        unit_price = base_price * 0.70  # 30% volume discount
    elif quantity >= 50:
        unit_price = base_price * 0.80  # 20% volume discount
    elif quantity >= 20:
        unit_price = base_price * 0.90  # 10% volume discount
    elif quantity >= 10:
        unit_price = base_price * 0.95  # 5% volume discount
    else:
        unit_price = base_price
    
    subtotal = unit_price * quantity
    
    # Apply billing frequency adjustment
    if request.billing_frequency == "annual":
        annual_discount = 0.17  # ~2 months free
        discount_amount = subtotal * annual_discount
        final_price = subtotal - discount_amount
        billing_note = "Annual billing (17% discount)"
    else:
        discount_amount = 0
        final_price = subtotal
        billing_note = "Monthly billing"
    
    # Apply segment-based pricing
    segment_adjustment = 0
    if request.customer_segment == "enterprise":
        segment_adjustment = final_price * 0.10  # Enterprise premium
        final_price += segment_adjustment
    elif request.customer_segment == "startup":
        segment_adjustment = -final_price * 0.20  # Startup discount
        final_price += segment_adjustment
    
    return {
        "product_id": request.product_id,
        "quantity": quantity,
        "pricing_breakdown": {
            "base_price_per_unit": base_price,
            "unit_price_after_volume": unit_price,
            "subtotal": subtotal,
            "volume_discount": base_price - unit_price,
            "billing_adjustment": -discount_amount,
            "segment_adjustment": segment_adjustment,
            "final_price": final_price
        },
        "billing": {
            "frequency": request.billing_frequency,
            "note": billing_note,
            "monthly_equivalent": final_price / 12 if request.billing_frequency == "annual" else final_price
        },
        "currency": "USD",
        "calculated_at": datetime.utcnow().isoformat()
    }


@router.post("/bulk-calculate")
async def bulk_calculate_prices(
    items: List[PriceCalculationRequest],
    tenant_id: str = Query(default="default")
):
    """Calculate prices for multiple products"""
    calculations = []
    total = 0
    
    for item in items:
        base_price = random.uniform(50, 500)
        unit_price = base_price * (0.9 if item.quantity >= 10 else 1.0)
        subtotal = unit_price * item.quantity
        
        calculations.append({
            "product_id": item.product_id,
            "quantity": item.quantity,
            "unit_price": unit_price,
            "subtotal": subtotal
        })
        total += subtotal
    
    # Bundle discount
    bundle_discount = total * 0.05 if len(items) >= 3 else 0
    
    return {
        "line_items": calculations,
        "subtotal": total,
        "bundle_discount": bundle_discount,
        "total": total - bundle_discount,
        "currency": "USD"
    }


# Discount Rules
@router.post("/discount-rules")
async def create_discount_rule(
    request: DiscountRuleCreate,
    tenant_id: str = Query(default="default")
):
    """Create a discount rule"""
    rule_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    rule = {
        "id": rule_id,
        "name": request.name,
        "discount_type": request.discount_type.value,
        "value": request.value,
        "min_deal_size": request.min_deal_size,
        "max_deal_size": request.max_deal_size,
        "min_quantity": request.min_quantity,
        "product_ids": request.product_ids,
        "requires_approval": request.requires_approval,
        "approval_threshold": request.approval_threshold,
        "is_active": True,
        "usage_count": 0,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    pricing_rules[rule_id] = rule
    
    return rule


@router.get("/discount-rules")
async def list_discount_rules(
    active_only: bool = True,
    discount_type: Optional[DiscountType] = None,
    tenant_id: str = Query(default="default")
):
    """List discount rules"""
    result = [r for r in pricing_rules.values() if r.get("tenant_id") == tenant_id]
    
    if active_only:
        result = [r for r in result if r.get("is_active", True)]
    if discount_type:
        result = [r for r in result if r.get("discount_type") == discount_type.value]
    
    return {"rules": result, "total": len(result)}


@router.post("/validate-discount")
async def validate_discount(
    discount_code: str,
    deal_value: float,
    product_ids: List[str] = [],
    tenant_id: str = Query(default="default")
):
    """Validate if a discount can be applied"""
    # Mock validation
    is_valid = random.choice([True, True, True, False])
    
    if is_valid:
        discount_value = random.uniform(5, 25)
        return {
            "valid": True,
            "discount_code": discount_code,
            "discount_type": "percentage",
            "discount_value": discount_value,
            "discount_amount": deal_value * (discount_value / 100),
            "requires_approval": discount_value > 20,
            "message": f"Discount of {discount_value}% applied"
        }
    else:
        return {
            "valid": False,
            "discount_code": discount_code,
            "reason": random.choice([
                "Discount code expired",
                "Minimum deal size not met",
                "Product not eligible for this discount"
            ])
        }


# Price Optimization
@router.get("/optimization/recommendations")
async def get_pricing_recommendations(
    product_id: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Get AI-powered pricing recommendations"""
    return {
        "generated_at": datetime.utcnow().isoformat(),
        "recommendations": [
            {
                "type": "price_increase",
                "product_id": product_id or "prod_001",
                "current_price": random.randint(100, 300),
                "recommended_price": random.randint(150, 350),
                "rationale": "Competitor analysis shows market can bear 15% higher price",
                "expected_impact": {
                    "revenue_change": "+12%",
                    "volume_change": "-3%",
                    "margin_improvement": "+18%"
                },
                "confidence": round(random.uniform(0.75, 0.92), 2)
            },
            {
                "type": "volume_tier",
                "product_id": product_id or "prod_001",
                "recommendation": "Add 100+ seat tier with 35% discount",
                "rationale": "Missing competitive tier for enterprise deals",
                "expected_impact": {
                    "enterprise_win_rate": "+8%",
                    "avg_deal_size": "+25%"
                },
                "confidence": round(random.uniform(0.70, 0.88), 2)
            },
            {
                "type": "bundle_opportunity",
                "products": ["prod_001", "prod_002", "prod_003"],
                "recommendation": "Create growth bundle with 20% combined discount",
                "rationale": "These products are frequently purchased together",
                "expected_impact": {
                    "attach_rate": "+35%",
                    "avg_order_value": "+40%"
                },
                "confidence": round(random.uniform(0.80, 0.95), 2)
            }
        ],
        "market_insights": {
            "competitor_avg_price": random.randint(150, 250),
            "your_position": random.choice(["below_market", "at_market", "above_market"]),
            "price_sensitivity": random.choice(["low", "medium", "high"])
        }
    }


@router.get("/analytics")
async def get_pricing_analytics(
    period: str = Query(default="quarter"),
    tenant_id: str = Query(default="default")
):
    """Get pricing analytics"""
    return {
        "period": period,
        "generated_at": datetime.utcnow().isoformat(),
        "summary": {
            "avg_selling_price": random.randint(40000, 80000),
            "avg_list_price": random.randint(50000, 100000),
            "avg_discount_pct": round(random.uniform(12, 25), 1),
            "deals_with_discount": round(random.uniform(0.60, 0.85), 2),
            "total_discount_given": random.randint(200000, 800000)
        },
        "discount_analysis": {
            "by_type": [
                {"type": DiscountType.VOLUME.value, "count": random.randint(30, 80), "avg_pct": round(random.uniform(10, 20), 1)},
                {"type": DiscountType.NEGOTIATED.value, "count": random.randint(20, 50), "avg_pct": round(random.uniform(15, 25), 1)},
                {"type": DiscountType.PROMOTIONAL.value, "count": random.randint(10, 30), "avg_pct": round(random.uniform(5, 15), 1)}
            ],
            "excessive_discounts": random.randint(5, 15),
            "approval_rate": round(random.uniform(0.85, 0.98), 2)
        },
        "win_rate_by_discount": [
            {"discount_range": "0-10%", "win_rate": round(random.uniform(0.25, 0.35), 2)},
            {"discount_range": "10-20%", "win_rate": round(random.uniform(0.35, 0.50), 2)},
            {"discount_range": "20-30%", "win_rate": round(random.uniform(0.45, 0.60), 2)},
            {"discount_range": "30%+", "win_rate": round(random.uniform(0.50, 0.65), 2)}
        ],
        "trends": {
            "discount_trend": random.choice(["increasing", "stable", "decreasing"]),
            "asp_trend": random.choice(["increasing", "stable", "decreasing"])
        }
    }


# Competitive Pricing
@router.get("/competitive-analysis")
async def get_competitive_pricing(
    product_id: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Get competitive pricing analysis"""
    competitors = ["Competitor A", "Competitor B", "Competitor C"]
    
    return {
        "product_id": product_id,
        "your_price": random.randint(80, 150),
        "market_position": random.choice(["premium", "competitive", "value"]),
        "competitors": [
            {
                "name": comp,
                "price": random.randint(70, 180),
                "pricing_model": random.choice([pm.value for pm in PricingModel]),
                "includes": random.sample(["Support", "Training", "API Access", "Custom Reports", "SSO"], 3),
                "last_updated": (datetime.utcnow() - timedelta(days=random.randint(1, 60))).isoformat()
            }
            for comp in competitors
        ],
        "recommendation": random.choice([
            "Consider raising prices - you're 15% below market",
            "Pricing is competitive - focus on value messaging",
            "Add feature differentiators to justify premium"
        ])
    }
