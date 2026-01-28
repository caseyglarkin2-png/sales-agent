"""Workflow Templates - Pre-defined multi-agent workflows.

Sprint 43.3: Provides templates for common multi-step sales workflows
that chain multiple agents together.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from src.logger import get_logger

logger = get_logger(__name__)


@dataclass
class WorkflowStep:
    """A single step in a workflow template."""
    agent_name: str
    action: str
    description: str
    input_mapping: Dict[str, str] = field(default_factory=dict)
    # Maps context keys to agent input params
    # e.g., {"company_name": "target_company"} means
    # pass context["target_company"] as company_name param
    optional: bool = False
    condition: Optional[str] = None  # e.g., "has_email" - skip if not met


@dataclass
class WorkflowTemplate:
    """A pre-defined multi-agent workflow."""
    id: str
    name: str
    description: str
    icon: str
    category: str  # sales, content, research, fulfillment
    steps: List[WorkflowStep]
    required_inputs: List[str] = field(default_factory=list)
    estimated_duration: str = "2-3 minutes"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "category": self.category,
            "steps": [
                {
                    "agent": s.agent_name,
                    "action": s.action,
                    "description": s.description,
                    "optional": s.optional,
                }
                for s in self.steps
            ],
            "required_inputs": self.required_inputs,
            "estimated_duration": self.estimated_duration,
        }


# =========================================================================
# Pre-defined Workflow Templates
# =========================================================================

ACCOUNT_RESEARCH_WORKFLOW = WorkflowTemplate(
    id="account_research",
    name="Account Research",
    description="Deep dive into a target account: research company, find stakeholders, identify opportunities",
    icon="🔍",
    category="research",
    required_inputs=["company_name"],
    estimated_duration="2-3 minutes",
    steps=[
        WorkflowStep(
            agent_name="research_agent",
            action="research_company",
            description="Research company background, size, industry",
            input_mapping={"company_name": "company_name"},
        ),
        WorkflowStep(
            agent_name="account_analyzer",
            action="analyze_account",
            description="Analyze account for opportunities",
            input_mapping={"company_name": "company_name"},
        ),
        WorkflowStep(
            agent_name="hubspot_connector",
            action="search_contacts",
            description="Find contacts at the company",
            input_mapping={"query": "company_name"},
        ),
        WorkflowStep(
            agent_name="enrichment_agent",
            action="enrich_contacts",
            description="Enrich found contacts with additional data",
            input_mapping={},
            optional=True,
            condition="has_contacts",
        ),
    ],
)

NEW_DEAL_WORKFLOW = WorkflowTemplate(
    id="new_deal",
    name="New Deal Setup",
    description="Set up a new deal: create in CRM, research account, draft intro email",
    icon="🎯",
    category="sales",
    required_inputs=["company_name", "contact_email"],
    estimated_duration="3-4 minutes",
    steps=[
        WorkflowStep(
            agent_name="research_agent",
            action="research_company",
            description="Quick research on the target company",
            input_mapping={"company_name": "company_name", "depth": "'quick'"},
        ),
        WorkflowStep(
            agent_name="hubspot_connector",
            action="create_deal",
            description="Create deal in HubSpot CRM",
            input_mapping={
                "company_name": "company_name",
                "contact_email": "contact_email",
            },
        ),
        WorkflowStep(
            agent_name="prospecting_agent",
            action="score_lead",
            description="Score the lead based on fit signals",
            input_mapping={"email": "contact_email"},
        ),
        WorkflowStep(
            agent_name="draft_writer",
            action="draft_email",
            description="Draft personalized intro email",
            input_mapping={
                "to_email": "contact_email",
                "context": "_research_summary",
            },
        ),
    ],
)

MEETING_PREP_WORKFLOW = WorkflowTemplate(
    id="meeting_prep",
    name="Meeting Preparation",
    description="Prepare for a sales meeting: research, create agenda, find talking points",
    icon="📅",
    category="sales",
    required_inputs=["company_name", "meeting_type"],
    estimated_duration="2-3 minutes",
    steps=[
        WorkflowStep(
            agent_name="research_agent",
            action="research_company",
            description="Research company for meeting context",
            input_mapping={"company_name": "company_name"},
        ),
        WorkflowStep(
            agent_name="hubspot_connector",
            action="get_deal_history",
            description="Get deal history and past interactions",
            input_mapping={"company_name": "company_name"},
            optional=True,
        ),
        WorkflowStep(
            agent_name="agenda_generator",
            action="create_agenda",
            description="Generate meeting agenda",
            input_mapping={
                "meeting_type": "meeting_type",
                "company_name": "company_name",
            },
        ),
        WorkflowStep(
            agent_name="objection_handler",
            action="prepare_objections",
            description="Prepare for likely objections",
            input_mapping={"context": "_company_info"},
            optional=True,
        ),
    ],
)

CONTENT_CAMPAIGN_WORKFLOW = WorkflowTemplate(
    id="content_campaign",
    name="Content Campaign",
    description="Create a content campaign: repurpose content, schedule social posts, draft email",
    icon="✍️",
    category="content",
    required_inputs=["source_content", "campaign_goal"],
    estimated_duration="3-5 minutes",
    steps=[
        WorkflowStep(
            agent_name="content_repurpose",
            action="analyze_content",
            description="Analyze source content for repurposing",
            input_mapping={"content": "source_content"},
        ),
        WorkflowStep(
            agent_name="content_repurpose",
            action="generate_linkedin",
            description="Create LinkedIn post from content",
            input_mapping={"content": "source_content"},
        ),
        WorkflowStep(
            agent_name="content_repurpose",
            action="generate_twitter",
            description="Create Twitter thread from content",
            input_mapping={"content": "source_content"},
        ),
        WorkflowStep(
            agent_name="social_scheduler",
            action="schedule_posts",
            description="Schedule the social posts",
            input_mapping={},
            optional=True,
        ),
        WorkflowStep(
            agent_name="draft_writer",
            action="draft_email",
            description="Draft email promoting the content",
            input_mapping={"context": "campaign_goal"},
            optional=True,
        ),
    ],
)

PROPOSAL_CREATION_WORKFLOW = WorkflowTemplate(
    id="proposal_creation",
    name="Proposal Creation",
    description="Create a sales proposal: research, generate document, add to CRM",
    icon="📄",
    category="fulfillment",
    required_inputs=["company_name", "deal_value"],
    estimated_duration="4-5 minutes",
    steps=[
        WorkflowStep(
            agent_name="research_agent",
            action="research_company",
            description="Research company for proposal context",
            input_mapping={"company_name": "company_name", "depth": "'deep'"},
        ),
        WorkflowStep(
            agent_name="account_analyzer",
            action="identify_needs",
            description="Identify key needs and pain points",
            input_mapping={"company_name": "company_name"},
        ),
        WorkflowStep(
            agent_name="proposal_generator",
            action="generate_proposal",
            description="Generate proposal document",
            input_mapping={
                "company_name": "company_name",
                "deal_value": "deal_value",
            },
        ),
        WorkflowStep(
            agent_name="deliverable_tracker",
            action="track_deliverable",
            description="Track proposal as deliverable",
            input_mapping={"deliverable_type": "'proposal'"},
        ),
    ],
)

COMPETITOR_ANALYSIS_WORKFLOW = WorkflowTemplate(
    id="competitor_analysis",
    name="Competitor Analysis",
    description="Analyze a competitor: gather intel, compare features, find differentiators",
    icon="⚔️",
    category="research",
    required_inputs=["competitor_name"],
    estimated_duration="3-4 minutes",
    steps=[
        WorkflowStep(
            agent_name="research_agent",
            action="research_company",
            description="Research competitor company",
            input_mapping={"company_name": "competitor_name", "depth": "'deep'"},
        ),
        WorkflowStep(
            agent_name="competitor_watch",
            action="analyze_competitor",
            description="Deep competitor analysis",
            input_mapping={"competitor_name": "competitor_name"},
        ),
        WorkflowStep(
            agent_name="competitor_watch",
            action="find_differentiators",
            description="Identify key differentiators",
            input_mapping={},
        ),
        WorkflowStep(
            agent_name="objection_handler",
            action="prepare_battlecard",
            description="Generate competitive battlecard",
            input_mapping={"competitor": "competitor_name"},
            optional=True,
        ),
    ],
)


# =========================================================================
# Workflow Registry
# =========================================================================

WORKFLOW_REGISTRY: Dict[str, WorkflowTemplate] = {
    "account_research": ACCOUNT_RESEARCH_WORKFLOW,
    "new_deal": NEW_DEAL_WORKFLOW,
    "meeting_prep": MEETING_PREP_WORKFLOW,
    "content_campaign": CONTENT_CAMPAIGN_WORKFLOW,
    "proposal_creation": PROPOSAL_CREATION_WORKFLOW,
    "competitor_analysis": COMPETITOR_ANALYSIS_WORKFLOW,
}


def get_workflow_template(workflow_id: str) -> Optional[WorkflowTemplate]:
    """Get a workflow template by ID."""
    return WORKFLOW_REGISTRY.get(workflow_id)


def list_workflow_templates(category: Optional[str] = None) -> List[WorkflowTemplate]:
    """List all workflow templates, optionally filtered by category."""
    workflows = list(WORKFLOW_REGISTRY.values())
    if category:
        workflows = [w for w in workflows if w.category == category]
    return workflows


def get_workflow_categories() -> List[Dict[str, Any]]:
    """Get list of workflow categories with counts."""
    categories: Dict[str, int] = {}
    for w in WORKFLOW_REGISTRY.values():
        categories[w.category] = categories.get(w.category, 0) + 1
    
    return [
        {"id": cat, "count": count}
        for cat, count in sorted(categories.items())
    ]
