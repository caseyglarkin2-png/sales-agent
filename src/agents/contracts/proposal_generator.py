"""ProposalGeneratorAgent - Generate proposal documents from templates.

Creates professional proposals by combining service templates, pricing,
and client-specific context.
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from enum import Enum

from src.agents.base import BaseAgent
from src.logger import get_logger

logger = get_logger(__name__)


class ProposalType(str, Enum):
    """Types of proposals."""
    STRATEGY = "strategy"
    IMPLEMENTATION = "implementation"
    RETAINER = "retainer"
    PROJECT = "project"
    AUDIT = "audit"
    TRAINING = "training"


class ProposalStatus(str, Enum):
    """Proposal lifecycle status."""
    DRAFT = "draft"
    REVIEW = "review"
    SENT = "sent"
    VIEWED = "viewed"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"


class ProposalGeneratorAgent(BaseAgent):
    """Generates professional proposals from templates and context.
    
    Features:
    - Template-based proposal generation
    - Dynamic pricing insertion
    - Client-specific customization
    - Multiple output formats (PDF, Google Docs, Notion)
    - Proposal tracking and analytics
    
    Example:
        agent = ProposalGeneratorAgent(drive_connector, llm_connector)
        result = await agent.execute({
            "action": "generate",
            "client_name": "Acme Corp",
            "proposal_type": "strategy",
            "services": ["brand_strategy", "content_strategy"],
            "budget_range": {"min": 15000, "max": 25000},
        })
    """

    # Service catalog with base pricing
    SERVICE_CATALOG = {
        "brand_strategy": {
            "name": "Brand Strategy",
            "description": "Comprehensive brand positioning and messaging framework",
            "base_price": 8000,
            "duration_weeks": 4,
            "deliverables": [
                "Brand positioning statement",
                "Messaging framework",
                "Competitive analysis",
                "Brand guidelines",
            ],
        },
        "content_strategy": {
            "name": "Content Strategy",
            "description": "Content planning and editorial calendar development",
            "base_price": 6000,
            "duration_weeks": 3,
            "deliverables": [
                "Content audit",
                "Editorial calendar (3 months)",
                "Content pillars and themes",
                "Distribution strategy",
            ],
        },
        "go_to_market": {
            "name": "Go-to-Market Strategy",
            "description": "Launch planning and execution strategy",
            "base_price": 12000,
            "duration_weeks": 6,
            "deliverables": [
                "Market analysis",
                "Launch timeline",
                "Channel strategy",
                "Launch playbook",
            ],
        },
        "monthly_retainer": {
            "name": "Monthly Retainer",
            "description": "Ongoing strategic support and execution",
            "base_price": 5000,
            "duration_weeks": 4,
            "deliverables": [
                "Weekly strategy sessions",
                "Content creation support",
                "Performance reporting",
                "Ad-hoc consulting",
            ],
            "recurring": True,
        },
    }

    def __init__(self, drive_connector=None, llm_connector=None):
        """Initialize with connectors."""
        super().__init__(
            name="Proposal Generator Agent",
            description="Generates professional proposals from templates"
        )
        self.drive_connector = drive_connector
        self.llm_connector = llm_connector
        
        # In-memory storage (would be DB in production)
        self._proposals: Dict[str, Dict[str, Any]] = {}

    async def validate_input(self, context: Dict[str, Any]) -> bool:
        """Validate input."""
        action = context.get("action", "generate")
        if action == "generate":
            return "client_name" in context
        return True

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute proposal generation action."""
        action = context.get("action", "generate")
        
        if action == "generate":
            return await self._generate_proposal(context)
        elif action == "list":
            return await self._list_proposals(context)
        elif action == "get":
            return await self._get_proposal(context)
        elif action == "update_status":
            return await self._update_status(context)
        elif action == "get_services":
            return await self._get_services(context)
        else:
            return {"status": "error", "error": f"Unknown action: {action}"}

    async def _generate_proposal(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a new proposal."""
        proposal_id = f"prop-{datetime.utcnow().timestamp()}"
        
        # Get services
        service_ids = context.get("services", ["brand_strategy"])
        services = []
        total_price = 0
        total_weeks = 0
        
        for service_id in service_ids:
            if service_id in self.SERVICE_CATALOG:
                service = self.SERVICE_CATALOG[service_id].copy()
                service["id"] = service_id
                services.append(service)
                total_price += service["base_price"]
                if not service.get("recurring"):
                    total_weeks = max(total_weeks, service["duration_weeks"])
        
        # Apply discount if multiple services
        discount = 0
        if len(services) >= 3:
            discount = 0.10  # 10% discount
        elif len(services) >= 2:
            discount = 0.05  # 5% discount
        
        final_price = total_price * (1 - discount)
        
        # Calculate timeline
        start_date = datetime.utcnow() + timedelta(days=7)  # Start in 1 week
        end_date = start_date + timedelta(weeks=total_weeks)
        
        # Generate executive summary with LLM if available
        executive_summary = await self._generate_summary(context, services)
        
        proposal = {
            "id": proposal_id,
            "client_name": context["client_name"],
            "client_email": context.get("client_email"),
            "client_company": context.get("client_company"),
            "proposal_type": context.get("proposal_type", ProposalType.PROJECT.value),
            "title": context.get("title", f"Proposal for {context['client_name']}"),
            "status": ProposalStatus.DRAFT.value,
            "services": services,
            "pricing": {
                "subtotal": total_price,
                "discount_percent": discount * 100,
                "discount_amount": total_price * discount,
                "total": round(final_price, 2),
                "payment_terms": context.get("payment_terms", "50% upfront, 50% on completion"),
            },
            "timeline": {
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "duration_weeks": total_weeks,
            },
            "executive_summary": executive_summary,
            "validity_days": context.get("validity_days", 30),
            "expires_at": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            "created_by": context.get("created_by", "system"),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        # Generate full content
        proposal["content"] = self._generate_proposal_content(proposal)
        
        self._proposals[proposal_id] = proposal
        
        logger.info(f"Generated proposal: {proposal_id} for {context['client_name']}")
        
        return {
            "status": "success",
            "proposal": proposal,
            "message": f"Proposal generated: ${final_price:,.0f} for {total_weeks} weeks",
        }

    async def _generate_summary(
        self, 
        context: Dict[str, Any], 
        services: List[Dict[str, Any]]
    ) -> str:
        """Generate executive summary using LLM."""
        if not self.llm_connector:
            # Default summary template
            service_names = [s["name"] for s in services]
            return f"""We're excited to propose a comprehensive engagement with {context['client_name']} 
covering {', '.join(service_names)}. This proposal outlines our approach, deliverables, 
timeline, and investment for achieving your goals."""
        
        service_list = "\n".join([f"- {s['name']}: {s['description']}" for s in services])
        
        prompt = f"""Write a compelling 2-3 sentence executive summary for a proposal to {context['client_name']}.

Services included:
{service_list}

Additional context: {context.get('notes', 'None')}

The summary should be professional, confident, and focused on the value we'll deliver.
Do not include pricing or specific dates. Keep it concise and impactful.
"""
        
        try:
            response = await self.llm_connector.generate_text(
                prompt=prompt,
                temperature=0.7,
                max_tokens=200,
            )
            return response.strip()
        except Exception as e:
            logger.warning(f"Could not generate summary: {e}")
            return f"We're excited to partner with {context['client_name']} on this engagement."

    def _generate_proposal_content(self, proposal: Dict[str, Any]) -> Dict[str, Any]:
        """Generate full proposal content sections."""
        return {
            "cover": {
                "title": proposal["title"],
                "prepared_for": proposal["client_name"],
                "date": datetime.utcnow().strftime("%B %d, %Y"),
                "valid_until": proposal["expires_at"][:10],
            },
            "executive_summary": proposal["executive_summary"],
            "scope_of_work": [
                {
                    "service": s["name"],
                    "description": s["description"],
                    "deliverables": s["deliverables"],
                    "duration": f"{s['duration_weeks']} weeks" if not s.get("recurring") else "Monthly",
                }
                for s in proposal["services"]
            ],
            "timeline": {
                "overview": f"The engagement will run from {proposal['timeline']['start_date']} to {proposal['timeline']['end_date']}.",
                "phases": self._generate_phases(proposal["services"]),
            },
            "investment": {
                "summary": f"Total Investment: ${proposal['pricing']['total']:,.0f}",
                "breakdown": [
                    {"item": s["name"], "amount": s["base_price"]}
                    for s in proposal["services"]
                ],
                "discount": proposal["pricing"]["discount_amount"] if proposal["pricing"]["discount_percent"] > 0 else None,
                "payment_terms": proposal["pricing"]["payment_terms"],
            },
            "about_us": {
                "company": "Dude, What's The Bid??! LLC",
                "description": "We help companies build and execute go-to-market strategies that drive measurable results.",
            },
            "next_steps": [
                "Review this proposal and let us know if you have any questions",
                "Sign the agreement to confirm your engagement",
                "Complete onboarding questionnaire",
                "Schedule kickoff call",
            ],
        }

    def _generate_phases(self, services: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate project phases from services."""
        phases = []
        current_week = 1
        
        for service in services:
            if service.get("recurring"):
                phases.append({
                    "name": service["name"],
                    "timing": "Ongoing (Monthly)",
                    "activities": service["deliverables"],
                })
            else:
                phases.append({
                    "name": service["name"],
                    "timing": f"Weeks {current_week}-{current_week + service['duration_weeks'] - 1}",
                    "activities": service["deliverables"],
                })
                current_week += service["duration_weeks"]
        
        return phases

    async def _list_proposals(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """List proposals with optional filters."""
        status = context.get("status")
        client = context.get("client_name")
        
        proposals = list(self._proposals.values())
        
        if status:
            proposals = [p for p in proposals if p["status"] == status]
        if client:
            proposals = [p for p in proposals if client.lower() in p["client_name"].lower()]
        
        # Sort by created date descending
        proposals = sorted(proposals, key=lambda x: x["created_at"], reverse=True)
        
        return {
            "status": "success",
            "count": len(proposals),
            "proposals": proposals,
        }

    async def _get_proposal(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get a specific proposal."""
        proposal_id = context.get("proposal_id")
        
        if proposal_id not in self._proposals:
            return {"status": "error", "error": f"Proposal not found: {proposal_id}"}
        
        return {
            "status": "success",
            "proposal": self._proposals[proposal_id],
        }

    async def _update_status(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Update proposal status."""
        proposal_id = context.get("proposal_id")
        new_status = context.get("new_status")
        
        if proposal_id not in self._proposals:
            return {"status": "error", "error": f"Proposal not found: {proposal_id}"}
        
        proposal = self._proposals[proposal_id]
        proposal["status"] = new_status
        proposal["updated_at"] = datetime.utcnow().isoformat()
        
        if new_status == ProposalStatus.VIEWED.value:
            proposal["viewed_at"] = datetime.utcnow().isoformat()
        elif new_status == ProposalStatus.ACCEPTED.value:
            proposal["accepted_at"] = datetime.utcnow().isoformat()
        elif new_status == ProposalStatus.DECLINED.value:
            proposal["declined_at"] = datetime.utcnow().isoformat()
            proposal["decline_reason"] = context.get("reason")
        
        logger.info(f"Proposal {proposal_id} status updated to {new_status}")
        
        return {
            "status": "success",
            "proposal": proposal,
        }

    async def _get_services(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get available services."""
        return {
            "status": "success",
            "services": self.SERVICE_CATALOG,
        }
