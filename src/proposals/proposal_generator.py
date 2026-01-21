"""Proposal generation module.

Generates personalized proposals/one-pagers based on:
- Contact persona and job title
- Company size and industry
- Specific pain points and use cases
- Pesti service offerings

Outputs to Google Docs for easy sharing.
"""
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from src.agents.persona_router import Persona, get_messaging_context
from src.logger import get_logger

logger = get_logger(__name__)


class ProposalSection(BaseModel):
    """A section of the proposal."""
    title: str
    content: str
    bullet_points: List[str] = []


class Proposal(BaseModel):
    """Generated proposal document."""
    id: str
    contact_email: str
    contact_name: str
    company_name: str
    persona: str
    
    # Document content
    title: str
    executive_summary: str
    sections: List[ProposalSection] = []
    pricing_tier: str = ""
    cta: str = ""
    
    # Metadata
    created_at: str = ""
    google_doc_url: Optional[str] = None
    google_doc_id: Optional[str] = None


class ProposalTemplate(BaseModel):
    """Template for a proposal type."""
    id: str
    name: str
    persona: Persona
    sections: List[Dict[str, Any]]
    pricing_tiers: List[Dict[str, Any]]


# Proposal templates by persona
PROPOSAL_TEMPLATES = {
    Persona.EVENTS: ProposalTemplate(
        id="field_marketing",
        name="Field Marketing & Events Partnership",
        persona=Persona.EVENTS,
        sections=[
            {
                "title": "The Challenge",
                "template": "Your field marketing team is stretched thin. Between {company}'s trade shows, roadshows, and regional events, you need reliable execution without growing headcount.",
            },
            {
                "title": "Pesti Field Marketing Solution",
                "template": "We become an extension of your team, handling end-to-end event execution so you can focus on strategy.",
                "bullets": [
                    "Booth staffing and management at trade shows",
                    "Pre-event outreach and meeting scheduling",
                    "On-site lead capture and qualification",
                    "Post-event follow-up and nurturing",
                    "Event ROI tracking and reporting",
                ],
            },
            {
                "title": "How We Work Together",
                "template": "We integrate with your existing tools and processes, not replace them.",
                "bullets": [
                    "Weekly syncs with your field marketing lead",
                    "Direct integration with your CRM (HubSpot, Salesforce)",
                    "Shared Slack channel for real-time coordination",
                    "Monthly performance reviews and optimization",
                ],
            },
        ],
        pricing_tiers=[
            {"name": "Event Support", "description": "Individual event staffing and support", "starting": "$5K/event"},
            {"name": "Program Partner", "description": "Ongoing field marketing support", "starting": "$15K/month"},
            {"name": "Full Outsource", "description": "Complete field marketing function", "starting": "$35K/month"},
        ],
    ),
    Persona.DEMAND_GEN: ProposalTemplate(
        id="demand_generation",
        name="Demand Generation & Pipeline Acceleration",
        persona=Persona.DEMAND_GEN,
        sections=[
            {
                "title": "The Challenge",
                "template": "{company}'s pipeline needs more velocity. You're generating leads, but conversion rates are below target and the sales team needs more qualified meetings.",
            },
            {
                "title": "Pesti Demand Gen Solution",
                "template": "We accelerate your pipeline with targeted outreach, multi-touch nurturing, and qualified meeting generation.",
                "bullets": [
                    "Account-based outreach to your target account list",
                    "Multi-channel nurturing (email, LinkedIn, phone)",
                    "Meeting scheduling directly to sales calendars",
                    "Lead scoring and routing based on engagement",
                    "Pipeline velocity reporting and optimization",
                ],
            },
            {
                "title": "Our Approach",
                "template": "We don't just generate leads - we generate revenue.",
                "bullets": [
                    "Deep integration with your ICP and personas",
                    "Custom messaging aligned with your value props",
                    "A/B testing and continuous optimization",
                    "Transparent reporting on metrics that matter",
                ],
            },
        ],
        pricing_tiers=[
            {"name": "Pilot Program", "description": "3-month proof of concept", "starting": "$10K/month"},
            {"name": "Growth Partner", "description": "Ongoing demand gen support", "starting": "$20K/month"},
            {"name": "Revenue Team", "description": "Full pipeline responsibility", "starting": "$40K/month"},
        ],
    ),
    Persona.SALES: ProposalTemplate(
        id="sales_support",
        name="Sales Enablement & Target Account Penetration",
        persona=Persona.SALES,
        sections=[
            {
                "title": "The Challenge",
                "template": "{company}'s sales team has a target account list but not enough hours in the day to work every account effectively.",
            },
            {
                "title": "Pesti Sales Support Solution",
                "template": "We help your sales team get into more accounts with research, outreach, and meeting scheduling support.",
                "bullets": [
                    "Target account research and contact mapping",
                    "Multi-threaded outreach to key stakeholders",
                    "Meeting scheduling for AEs",
                    "Competitive intelligence and trigger monitoring",
                    "CRM hygiene and data enrichment",
                ],
            },
            {
                "title": "Working With Sales",
                "template": "We operate as an extension of your sales team, not a separate function.",
                "bullets": [
                    "Weekly pipeline reviews with sales leadership",
                    "Direct collaboration with individual AEs",
                    "Real-time Slack communication",
                    "Shared accountability for pipeline metrics",
                ],
            },
        ],
        pricing_tiers=[
            {"name": "AE Support", "description": "Support for 1-3 AEs", "starting": "$8K/month"},
            {"name": "Team Support", "description": "Support for 4-10 AEs", "starting": "$20K/month"},
            {"name": "Enterprise", "description": "Full sales development function", "starting": "$50K/month"},
        ],
    ),
    Persona.EXECUTIVE: ProposalTemplate(
        id="executive_gtm",
        name="GTM Execution Partnership",
        persona=Persona.EXECUTIVE,
        sections=[
            {
                "title": "The Opportunity",
                "template": "{company} has ambitious growth targets. Hitting them requires GTM execution capacity that scales without proportional headcount growth.",
            },
            {
                "title": "Pesti as Your GTM Partner",
                "template": "We provide flexible GTM execution capacity across field marketing, demand generation, and sales development.",
                "bullets": [
                    "Scalable execution without fixed headcount",
                    "Expertise across the full GTM spectrum",
                    "Integrated approach to marketing and sales",
                    "Clear ROI measurement and reporting",
                    "Flexibility to shift priorities as needed",
                ],
            },
            {
                "title": "Partnership Model",
                "template": "We work as an extension of your leadership team, not a vendor.",
                "bullets": [
                    "Executive-level strategic alignment",
                    "Dedicated account team",
                    "Quarterly business reviews",
                    "Transparent pricing and performance metrics",
                ],
            },
        ],
        pricing_tiers=[
            {"name": "Strategic Pilot", "description": "Prove the model", "starting": "$25K/month"},
            {"name": "Growth Partnership", "description": "Scaled execution", "starting": "$50K/month"},
            {"name": "Full GTM Partner", "description": "Comprehensive support", "starting": "$100K+/month"},
        ],
    ),
}

# Default template for unknown personas
DEFAULT_TEMPLATE = ProposalTemplate(
    id="general",
    name="GTM Partnership Overview",
    persona=Persona.UNKNOWN,
    sections=[
        {
            "title": "About Pesti",
            "template": "Pesti is a GTM execution partner helping B2B companies accelerate growth through field marketing, demand generation, and sales development.",
        },
        {
            "title": "How We Can Help {company}",
            "template": "We provide flexible execution capacity to help you hit your growth targets.",
            "bullets": [
                "Field marketing and event support",
                "Demand generation and lead nurturing",
                "Sales development and meeting scheduling",
                "Account-based marketing execution",
            ],
        },
    ],
    pricing_tiers=[
        {"name": "Starter", "description": "Get started", "starting": "$10K/month"},
        {"name": "Growth", "description": "Scale up", "starting": "$25K/month"},
    ],
)


class ProposalGenerator:
    """Generates personalized proposals for contacts."""
    
    def __init__(self):
        self.google_docs_enabled = bool(os.environ.get("GOOGLE_DOCS_CREDENTIALS"))
    
    async def generate_proposal(
        self,
        contact_email: str,
        contact_name: str,
        company_name: str,
        job_title: str = "",
        custom_context: Dict[str, Any] = None,
    ) -> Proposal:
        """Generate a personalized proposal for a contact.
        
        Args:
            contact_email: Contact's email
            contact_name: Contact's full name
            company_name: Company name
            job_title: Job title for persona detection
            custom_context: Additional context to personalize
            
        Returns:
            Generated Proposal object
        """
        # Detect persona
        persona_context = get_messaging_context(job_title, company_name)
        persona = Persona(persona_context["persona"])
        
        # Get template
        template = PROPOSAL_TEMPLATES.get(persona, DEFAULT_TEMPLATE)
        
        # Generate proposal content
        proposal_id = f"proposal-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        # Build sections from template
        sections = []
        for section_template in template.sections:
            content = section_template.get("template", "").format(
                company=company_name,
                name=contact_name,
            )
            bullets = section_template.get("bullets", [])
            
            sections.append(ProposalSection(
                title=section_template["title"],
                content=content,
                bullet_points=bullets,
            ))
        
        # Add pricing section
        pricing_content = "We offer flexible engagement models:\n\n"
        for tier in template.pricing_tiers:
            pricing_content += f"**{tier['name']}**: {tier['description']} - {tier['starting']}\n"
        
        sections.append(ProposalSection(
            title="Investment",
            content=pricing_content,
        ))
        
        # Generate executive summary
        exec_summary = self._generate_executive_summary(
            company_name=company_name,
            persona=persona,
            template=template,
        )
        
        # Generate CTA
        cta = self._generate_cta(persona, contact_name)
        
        proposal = Proposal(
            id=proposal_id,
            contact_email=contact_email,
            contact_name=contact_name,
            company_name=company_name,
            persona=persona.value,
            title=f"{template.name} - {company_name}",
            executive_summary=exec_summary,
            sections=sections,
            pricing_tier="",
            cta=cta,
            created_at=datetime.utcnow().isoformat(),
        )
        
        # Create Google Doc if enabled
        if self.google_docs_enabled:
            doc_url, doc_id = await self._create_google_doc(proposal)
            proposal.google_doc_url = doc_url
            proposal.google_doc_id = doc_id
        
        logger.info(f"Generated proposal {proposal_id} for {contact_email}")
        return proposal
    
    def _generate_executive_summary(
        self,
        company_name: str,
        persona: Persona,
        template: ProposalTemplate,
    ) -> str:
        """Generate executive summary based on persona."""
        summaries = {
            Persona.EVENTS: f"Pesti is proposing a field marketing partnership with {company_name} to extend your event execution capacity, improve lead capture, and accelerate post-event follow-up.",
            Persona.DEMAND_GEN: f"Pesti is proposing a demand generation partnership with {company_name} to accelerate pipeline velocity, improve lead quality, and increase qualified meeting generation.",
            Persona.SALES: f"Pesti is proposing a sales enablement partnership with {company_name} to help your sales team penetrate more target accounts and generate more qualified meetings.",
            Persona.EXECUTIVE: f"Pesti is proposing a strategic GTM partnership with {company_name} to provide scalable execution capacity across field marketing, demand generation, and sales development.",
            Persona.MARKETING_GENERAL: f"Pesti is proposing a marketing execution partnership with {company_name} to extend your team's capacity and accelerate growth initiatives.",
        }
        
        return summaries.get(persona, f"Pesti is proposing a GTM partnership with {company_name} to help accelerate growth.")
    
    def _generate_cta(self, persona: Persona, contact_name: str) -> str:
        """Generate call-to-action based on persona."""
        first_name = contact_name.split()[0] if contact_name else "there"
        
        ctas = {
            Persona.EVENTS: f"Ready to discuss your upcoming events calendar? Let's schedule a 30-minute call to explore how Pesti can support {first_name}.",
            Persona.DEMAND_GEN: f"Want to see how we've helped similar companies accelerate pipeline? Let's schedule a brief call to discuss your specific goals.",
            Persona.SALES: f"Interested in getting your sales team more at-bats? Let's schedule a call to discuss your target account strategy.",
            Persona.EXECUTIVE: f"I'd love to discuss how Pesti can support your growth objectives. Can we schedule a brief strategic conversation?",
        }
        
        return ctas.get(persona, "Let's schedule a call to discuss how Pesti can help.")
    
    async def _create_google_doc(self, proposal: Proposal) -> tuple[Optional[str], Optional[str]]:
        """Create a Google Doc from the proposal.
        
        Returns:
            Tuple of (doc_url, doc_id) or (None, None) if creation fails
        """
        # TODO: Implement Google Docs API integration
        # This would use the Google Docs API to:
        # 1. Create a new document
        # 2. Add formatted content
        # 3. Set sharing permissions
        # 4. Return the URL
        
        logger.info(f"Google Docs creation not yet implemented for {proposal.id}")
        return None, None
    
    def render_as_markdown(self, proposal: Proposal) -> str:
        """Render proposal as Markdown for preview."""
        lines = [
            f"# {proposal.title}",
            "",
            f"*Prepared for: {proposal.contact_name} at {proposal.company_name}*",
            f"*Date: {proposal.created_at[:10] if proposal.created_at else 'N/A'}*",
            "",
            "---",
            "",
            "## Executive Summary",
            "",
            proposal.executive_summary,
            "",
        ]
        
        for section in proposal.sections:
            lines.append(f"## {section.title}")
            lines.append("")
            lines.append(section.content)
            lines.append("")
            
            if section.bullet_points:
                for bullet in section.bullet_points:
                    lines.append(f"- {bullet}")
                lines.append("")
        
        lines.append("---")
        lines.append("")
        lines.append("## Next Steps")
        lines.append("")
        lines.append(proposal.cta)
        lines.append("")
        
        return "\n".join(lines)


# Global generator instance
_proposal_generator: Optional[ProposalGenerator] = None


def get_proposal_generator() -> ProposalGenerator:
    """Get or create the global proposal generator."""
    global _proposal_generator
    if _proposal_generator is None:
        _proposal_generator = ProposalGenerator()
    return _proposal_generator
