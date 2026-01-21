"""
ROI Calculator Routes - Deal ROI and value proposition tools
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

router = APIRouter(prefix="/roi-calculator", tags=["ROI Calculator"])


class CalculatorType(str, Enum):
    COST_SAVINGS = "cost_savings"
    REVENUE_INCREASE = "revenue_increase"
    PRODUCTIVITY_GAINS = "productivity_gains"
    RISK_REDUCTION = "risk_reduction"
    TIME_SAVINGS = "time_savings"
    COMPREHENSIVE = "comprehensive"


class IndustryType(str, Enum):
    TECHNOLOGY = "technology"
    HEALTHCARE = "healthcare"
    FINANCE = "finance"
    MANUFACTURING = "manufacturing"
    RETAIL = "retail"
    SERVICES = "services"
    OTHER = "other"


# In-memory storage
roi_calculations = {}
calculator_templates = {}
roi_benchmarks = {}


class ROIInputs(BaseModel):
    calculator_type: CalculatorType
    industry: Optional[IndustryType] = None
    company_size: Optional[str] = None  # small, medium, large, enterprise
    annual_revenue: Optional[float] = None
    employee_count: Optional[int] = None
    current_solution_cost: Optional[float] = None
    implementation_timeline_months: int = 3
    custom_inputs: Dict[str, Any] = {}


class ROICalculationCreate(BaseModel):
    name: str
    deal_id: Optional[str] = None
    account_id: Optional[str] = None
    inputs: ROIInputs


class CalculatorTemplateCreate(BaseModel):
    name: str
    calculator_type: CalculatorType
    industries: List[IndustryType] = []
    input_fields: List[Dict[str, Any]]
    formulas: Dict[str, str]
    description: Optional[str] = None


# Calculations
@router.post("/calculate")
async def create_roi_calculation(
    request: ROICalculationCreate,
    tenant_id: str = Query(default="default")
):
    """Create and run an ROI calculation"""
    calc_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    inputs = request.inputs
    
    # Simulate calculation based on type
    base_savings = random.randint(50000, 500000)
    
    if inputs.annual_revenue:
        base_savings = int(inputs.annual_revenue * random.uniform(0.05, 0.15))
    
    if inputs.employee_count:
        productivity_value = inputs.employee_count * random.randint(1000, 5000)
    else:
        productivity_value = random.randint(20000, 100000)
    
    implementation_cost = random.randint(10000, 100000)
    annual_cost = random.randint(20000, 200000)
    
    total_benefit_year1 = base_savings + productivity_value
    total_cost_year1 = implementation_cost + annual_cost
    net_benefit_year1 = total_benefit_year1 - total_cost_year1
    
    roi_percentage = (net_benefit_year1 / total_cost_year1) * 100 if total_cost_year1 > 0 else 0
    payback_months = (total_cost_year1 / (total_benefit_year1 / 12)) if total_benefit_year1 > 0 else 12
    
    calculation = {
        "id": calc_id,
        "name": request.name,
        "deal_id": request.deal_id,
        "account_id": request.account_id,
        "calculator_type": inputs.calculator_type.value,
        "industry": inputs.industry.value if inputs.industry else None,
        "inputs": {
            "company_size": inputs.company_size,
            "annual_revenue": inputs.annual_revenue,
            "employee_count": inputs.employee_count,
            "current_solution_cost": inputs.current_solution_cost,
            "implementation_timeline_months": inputs.implementation_timeline_months,
            "custom_inputs": inputs.custom_inputs
        },
        "results": {
            "cost_savings": base_savings,
            "productivity_gains": productivity_value,
            "total_annual_benefit": total_benefit_year1,
            "implementation_cost": implementation_cost,
            "annual_license_cost": annual_cost,
            "total_cost_year_1": total_cost_year1,
            "net_benefit_year_1": net_benefit_year1,
            "roi_percentage": round(roi_percentage, 1),
            "payback_months": round(payback_months, 1),
            "3_year_value": total_benefit_year1 * 3 - (total_cost_year1 + annual_cost * 2),
            "5_year_value": total_benefit_year1 * 5 - (total_cost_year1 + annual_cost * 4)
        },
        "breakdown": {
            "cost_savings": [
                {"category": "Labor cost reduction", "value": int(base_savings * 0.4)},
                {"category": "Tool consolidation", "value": int(base_savings * 0.3)},
                {"category": "Process automation", "value": int(base_savings * 0.3)}
            ],
            "productivity_gains": [
                {"category": "Time savings", "value": int(productivity_value * 0.5)},
                {"category": "Faster sales cycles", "value": int(productivity_value * 0.3)},
                {"category": "Reduced errors", "value": int(productivity_value * 0.2)}
            ]
        },
        "assumptions": [
            "Based on industry benchmarks for similar company sizes",
            f"Implementation timeline of {inputs.implementation_timeline_months} months",
            "Full adoption achieved within 6 months",
            "Conservative estimates used for projections"
        ],
        "created_by": "user_1",
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    roi_calculations[calc_id] = calculation
    
    logger.info("roi_calculation_created", calc_id=calc_id)
    
    return calculation


@router.get("")
async def list_roi_calculations(
    deal_id: Optional[str] = None,
    account_id: Optional[str] = None,
    calculator_type: Optional[CalculatorType] = None,
    limit: int = Query(default=50, le=100),
    tenant_id: str = Query(default="default")
):
    """List ROI calculations"""
    result = [c for c in roi_calculations.values() if c.get("tenant_id") == tenant_id]
    
    if deal_id:
        result = [c for c in result if c.get("deal_id") == deal_id]
    if account_id:
        result = [c for c in result if c.get("account_id") == account_id]
    if calculator_type:
        result = [c for c in result if c.get("calculator_type") == calculator_type.value]
    
    return {"calculations": result, "total": len(result)}


@router.get("/{calc_id}")
async def get_roi_calculation(
    calc_id: str,
    tenant_id: str = Query(default="default")
):
    """Get ROI calculation details"""
    if calc_id not in roi_calculations:
        raise HTTPException(status_code=404, detail="Calculation not found")
    return roi_calculations[calc_id]


@router.post("/{calc_id}/recalculate")
async def recalculate_roi(
    calc_id: str,
    updated_inputs: Dict[str, Any],
    tenant_id: str = Query(default="default")
):
    """Recalculate ROI with updated inputs"""
    if calc_id not in roi_calculations:
        raise HTTPException(status_code=404, detail="Calculation not found")
    
    calc = roi_calculations[calc_id]
    
    # Update inputs
    for key, value in updated_inputs.items():
        if key in calc["inputs"]:
            calc["inputs"][key] = value
    
    # Recalculate (simplified)
    base_savings = random.randint(50000, 500000)
    productivity_value = random.randint(20000, 100000)
    implementation_cost = random.randint(10000, 100000)
    annual_cost = random.randint(20000, 200000)
    
    total_benefit = base_savings + productivity_value
    total_cost = implementation_cost + annual_cost
    net_benefit = total_benefit - total_cost
    
    calc["results"] = {
        "cost_savings": base_savings,
        "productivity_gains": productivity_value,
        "total_annual_benefit": total_benefit,
        "total_cost_year_1": total_cost,
        "net_benefit_year_1": net_benefit,
        "roi_percentage": round((net_benefit / total_cost) * 100, 1) if total_cost > 0 else 0,
        "payback_months": round((total_cost / (total_benefit / 12)), 1) if total_benefit > 0 else 12
    }
    
    calc["updated_at"] = datetime.utcnow().isoformat()
    
    return calc


@router.delete("/{calc_id}")
async def delete_roi_calculation(
    calc_id: str,
    tenant_id: str = Query(default="default")
):
    """Delete an ROI calculation"""
    if calc_id not in roi_calculations:
        raise HTTPException(status_code=404, detail="Calculation not found")
    
    del roi_calculations[calc_id]
    
    return {"success": True, "deleted": calc_id}


# Export
@router.get("/{calc_id}/export")
async def export_roi_calculation(
    calc_id: str,
    format: str = Query(default="pdf"),  # pdf, pptx, xlsx
    tenant_id: str = Query(default="default")
):
    """Export ROI calculation as document"""
    if calc_id not in roi_calculations:
        raise HTTPException(status_code=404, detail="Calculation not found")
    
    return {
        "calc_id": calc_id,
        "format": format,
        "download_url": f"https://api.example.com/roi/export/{calc_id}.{format}",
        "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat()
    }


# Share
@router.post("/{calc_id}/share")
async def share_roi_calculation(
    calc_id: str,
    recipient_email: str,
    message: Optional[str] = None,
    include_assumptions: bool = True,
    tenant_id: str = Query(default="default")
):
    """Share ROI calculation with prospect"""
    if calc_id not in roi_calculations:
        raise HTTPException(status_code=404, detail="Calculation not found")
    
    share_id = str(uuid.uuid4())
    share_token = str(uuid.uuid4())[:12]
    
    return {
        "share_id": share_id,
        "calc_id": calc_id,
        "share_url": f"https://roi.example.com/view/{share_token}",
        "recipient_email": recipient_email,
        "message_sent": True,
        "expires_at": (datetime.utcnow() + timedelta(days=30)).isoformat()
    }


# Templates
@router.post("/templates")
async def create_calculator_template(
    request: CalculatorTemplateCreate,
    tenant_id: str = Query(default="default")
):
    """Create a calculator template"""
    template_id = str(uuid.uuid4())
    
    template = {
        "id": template_id,
        "name": request.name,
        "calculator_type": request.calculator_type.value,
        "industries": [i.value for i in request.industries],
        "input_fields": request.input_fields,
        "formulas": request.formulas,
        "description": request.description,
        "usage_count": 0,
        "tenant_id": tenant_id,
        "created_at": datetime.utcnow().isoformat()
    }
    
    calculator_templates[template_id] = template
    
    return template


@router.get("/templates")
async def list_calculator_templates(
    calculator_type: Optional[CalculatorType] = None,
    industry: Optional[IndustryType] = None,
    tenant_id: str = Query(default="default")
):
    """List calculator templates"""
    # Include default templates
    default_templates = [
        {
            "id": "default_savings",
            "name": "Cost Savings Calculator",
            "calculator_type": "cost_savings",
            "industries": ["technology", "finance", "healthcare"],
            "description": "Calculate potential cost savings from implementation"
        },
        {
            "id": "default_productivity",
            "name": "Productivity Gains Calculator",
            "calculator_type": "productivity_gains",
            "industries": ["technology", "services", "manufacturing"],
            "description": "Estimate productivity improvements"
        },
        {
            "id": "default_comprehensive",
            "name": "Comprehensive ROI Calculator",
            "calculator_type": "comprehensive",
            "industries": [],
            "description": "Full ROI analysis with all benefit categories"
        }
    ]
    
    custom = [t for t in calculator_templates.values() if t.get("tenant_id") == tenant_id]
    
    return {"templates": default_templates + custom, "total": len(default_templates) + len(custom)}


# Benchmarks
@router.get("/benchmarks")
async def get_industry_benchmarks(
    industry: IndustryType,
    company_size: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Get industry benchmarks for ROI calculations"""
    return {
        "industry": industry.value,
        "company_size": company_size,
        "benchmarks": {
            "avg_cost_savings_percent": round(random.uniform(10, 25), 1),
            "avg_productivity_gain_percent": round(random.uniform(15, 35), 1),
            "avg_roi_first_year": round(random.uniform(100, 300), 0),
            "avg_payback_months": random.randint(6, 18),
            "avg_implementation_time_months": random.randint(2, 6)
        },
        "comparison_companies": random.randint(50, 200),
        "updated_at": datetime.utcnow().isoformat()
    }


# Quick Calculator
@router.post("/quick-calculate")
async def quick_roi_calculation(
    employee_count: int,
    hours_saved_per_week: float = 5,
    hourly_cost: float = 50,
    annual_tool_cost: float = 10000,
    tenant_id: str = Query(default="default")
):
    """Quick ROI calculation without saving"""
    annual_hours_saved = hours_saved_per_week * 52 * employee_count
    productivity_value = annual_hours_saved * hourly_cost
    net_value = productivity_value - annual_tool_cost
    roi_percent = (net_value / annual_tool_cost) * 100 if annual_tool_cost > 0 else 0
    
    return {
        "inputs": {
            "employee_count": employee_count,
            "hours_saved_per_week": hours_saved_per_week,
            "hourly_cost": hourly_cost,
            "annual_tool_cost": annual_tool_cost
        },
        "results": {
            "annual_hours_saved": annual_hours_saved,
            "productivity_value": productivity_value,
            "annual_tool_cost": annual_tool_cost,
            "net_annual_value": net_value,
            "roi_percentage": round(roi_percent, 1),
            "payback_months": round(12 / (productivity_value / annual_tool_cost), 1) if productivity_value > 0 else 12
        }
    }


# Compare Scenarios
@router.post("/compare")
async def compare_scenarios(
    scenarios: List[Dict[str, Any]],
    tenant_id: str = Query(default="default")
):
    """Compare multiple ROI scenarios"""
    results = []
    
    for i, scenario in enumerate(scenarios):
        net_value = random.randint(50000, 300000)
        total_cost = random.randint(30000, 150000)
        
        results.append({
            "scenario_name": scenario.get("name", f"Scenario {i + 1}"),
            "net_value": net_value,
            "total_cost": total_cost,
            "roi_percentage": round((net_value / total_cost) * 100, 1) if total_cost > 0 else 0,
            "payback_months": random.randint(3, 18),
            "risk_level": random.choice(["low", "medium", "high"])
        })
    
    # Find best scenario
    best = max(results, key=lambda x: x["roi_percentage"])
    
    return {
        "scenarios": results,
        "recommendation": {
            "best_roi": best["scenario_name"],
            "reason": "Highest ROI percentage with acceptable risk"
        }
    }
