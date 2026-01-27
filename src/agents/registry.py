"""Agent Registry - Centralized discovery and management of all agents.

Sprint 41: Exposes all 38+ built agents for UI discovery and invocation.
"""
import importlib
import inspect
import pkgutil
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Type, Any
from pathlib import Path

from src.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AgentMeta:
    """Metadata for a registered agent."""
    name: str
    description: str
    domain: str  # sales, content, research, fulfillment, contracts, ops, data_hygiene
    module_path: str
    class_name: str
    capabilities: List[str] = field(default_factory=list)
    icon: str = "🤖"
    status: str = "active"  # active, beta, deprecated
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "name": self.name,
            "description": self.description,
            "domain": self.domain,
            "module_path": self.module_path,
            "class_name": self.class_name,
            "capabilities": self.capabilities,
            "icon": self.icon,
            "status": self.status,
        }


# Domain configurations
DOMAIN_CONFIG = {
    "sales": {"icon": "💼", "color": "indigo", "label": "Sales"},
    "content": {"icon": "✍️", "color": "purple", "label": "Content"},
    "research": {"icon": "🔍", "color": "blue", "label": "Research"},
    "fulfillment": {"icon": "📦", "color": "green", "label": "Fulfillment"},
    "contracts": {"icon": "📄", "color": "amber", "label": "Contracts"},
    "ops": {"icon": "⚙️", "color": "gray", "label": "Operations"},
    "data_hygiene": {"icon": "🧹", "color": "emerald", "label": "Data Hygiene"},
}


# Manual agent registry for agents without AGENT_META
# This ensures all agents are discoverable even without code changes
MANUAL_REGISTRY: List[AgentMeta] = [
    # Sales Domain
    AgentMeta(
        name="Prospecting Agent",
        description="Analyzes incoming messages to identify sales opportunities and generate personalized outreach",
        domain="sales",
        module_path="src.agents.prospecting",
        class_name="ProspectingAgent",
        capabilities=["lead_scoring", "intent_analysis", "response_generation"],
        icon="🎯",
    ),
    AgentMeta(
        name="Nurturing Agent",
        description="Manages lead nurturing sequences with personalized touch-points",
        domain="sales",
        module_path="src.agents.nurturing",
        class_name="NurturingAgent",
        capabilities=["sequence_management", "engagement_tracking", "follow_ups"],
        icon="🌱",
    ),
    AgentMeta(
        name="Account Analyzer",
        description="Deep analysis of accounts for strategic planning and opportunity identification",
        domain="sales",
        module_path="src.agents.account_analyzer",
        class_name="AccountAnalyzer",
        capabilities=["account_research", "stakeholder_mapping", "opportunity_analysis"],
        icon="🏢",
    ),
    AgentMeta(
        name="Persona Router",
        description="Routes messages to appropriate handlers based on detected persona",
        domain="sales",
        module_path="src.agents.persona_router",
        class_name="PersonaRouter",
        capabilities=["persona_detection", "routing", "context_switching"],
        icon="🎭",
    ),
    AgentMeta(
        name="Agenda Generator",
        description="Creates meeting agendas based on context and participants",
        domain="sales",
        module_path="src.agents.agenda_generator",
        class_name="AgendaGeneratorAgent",
        capabilities=["agenda_creation", "meeting_prep", "context_gathering"],
        icon="📋",
    ),
    AgentMeta(
        name="Outcome Reporter",
        description="Tracks and reports on sales outcomes and metrics",
        domain="sales",
        module_path="src.agents.outcome_reporter",
        class_name="OutcomeReporterAgent",
        capabilities=["outcome_tracking", "reporting", "analytics"],
        icon="📊",
    ),
    AgentMeta(
        name="Market Trend Monitor",
        description="Monitors market trends and competitive landscape",
        domain="sales",
        module_path="src.agents.market_trend_monitor",
        class_name="MarketTrendMonitor",
        capabilities=["trend_analysis", "competitive_intel", "market_research"],
        icon="📈",
    ),
    AgentMeta(
        name="Draft Writer",
        description="Generates email drafts with voice profile matching",
        domain="sales",
        module_path="src.agents.specialized",
        class_name="DraftWriterAgent",
        capabilities=["email_drafting", "voice_matching", "personalization"],
        icon="✉️",
    ),
    AgentMeta(
        name="Thread Reader",
        description="Analyzes email threads for context and action items",
        domain="sales",
        module_path="src.agents.specialized",
        class_name="ThreadReaderAgent",
        capabilities=["thread_analysis", "context_extraction", "action_items"],
        icon="📧",
    ),
    AgentMeta(
        name="Long Memory Agent",
        description="Maintains persistent memory of conversations and context",
        domain="sales",
        module_path="src.agents.specialized",
        class_name="LongMemoryAgent",
        capabilities=["memory_persistence", "context_recall", "relationship_tracking"],
        icon="🧠",
    ),
    AgentMeta(
        name="Objection Handler",
        description="Helps overcome sales objections with proven responses",
        domain="sales",
        module_path="src.agents.specialized",
        class_name="ObjectionHandlerAgent",
        capabilities=["objection_handling", "response_suggestions", "rebuttals"],
        icon="🛡️",
    ),
    AgentMeta(
        name="Validation Agent",
        description="Validates data and ensures quality across workflows",
        domain="sales",
        module_path="src.agents.validation",
        class_name="ValidationAgent",
        capabilities=["data_validation", "quality_checks", "error_detection"],
        icon="✅",
    ),
    
    # Content Domain
    AgentMeta(
        name="Content Repurpose",
        description="Repurposes content across different formats and channels",
        domain="content",
        module_path="src.agents.content.repurpose",
        class_name="ContentRepurposeAgent",
        capabilities=["content_transformation", "format_conversion", "channel_adaptation"],
        icon="♻️",
    ),
    AgentMeta(
        name="Social Scheduler",
        description="Schedules and optimizes social media content",
        domain="content",
        module_path="src.agents.content.social_scheduler",
        class_name="SocialSchedulerAgent",
        capabilities=["scheduling", "timing_optimization", "platform_targeting"],
        icon="📱",
    ),
    AgentMeta(
        name="Graphics Request",
        description="Generates graphics requests and creative briefs",
        domain="content",
        module_path="src.agents.content.graphics_request",
        class_name="GraphicsRequestAgent",
        capabilities=["brief_generation", "asset_requests", "design_specs"],
        icon="🎨",
    ),
    AgentMeta(
        name="Content Repurpose V2",
        description="Advanced content repurposing with AI enhancement",
        domain="content",
        module_path="src.agents.content.repurpose_v2",
        class_name="ContentRepurposeAgentV2",
        capabilities=["ai_enhancement", "multi_format", "seo_optimization"],
        icon="🔄",
        status="beta",
    ),
    
    # Research Domain
    AgentMeta(
        name="Research Deep",
        description="Deep research agent for comprehensive analysis",
        domain="research",
        module_path="src.agents.research.research_deep",
        class_name="ResearchDeepAgent",
        capabilities=["deep_research", "source_aggregation", "insight_synthesis"],
        icon="🔬",
    ),
    AgentMeta(
        name="Research Standard",
        description="Standard research for quick insights",
        domain="research",
        module_path="src.agents.research.standard",
        class_name="ResearchStandardAgent",
        capabilities=["quick_research", "fact_checking", "summary_generation"],
        icon="📚",
    ),
    
    # Fulfillment Domain
    AgentMeta(
        name="Approval Gateway",
        description="Manages approval workflows and routing",
        domain="fulfillment",
        module_path="src.agents.fulfillment.approval_gateway",
        class_name="ApprovalGatewayAgent",
        capabilities=["approval_routing", "escalation", "status_tracking"],
        icon="✔️",
    ),
    AgentMeta(
        name="Client Health",
        description="Monitors client health scores and engagement",
        domain="fulfillment",
        module_path="src.agents.fulfillment.client_health",
        class_name="ClientHealthAgent",
        capabilities=["health_scoring", "churn_prediction", "engagement_tracking"],
        icon="💚",
    ),
    AgentMeta(
        name="Deliverable Tracker",
        description="Tracks deliverables and project milestones",
        domain="fulfillment",
        module_path="src.agents.fulfillment.deliverable_tracker",
        class_name="DeliverableTrackerAgent",
        capabilities=["milestone_tracking", "deadline_management", "status_updates"],
        icon="📍",
    ),
    
    # Contracts Domain
    AgentMeta(
        name="Proposal Generator",
        description="Generates sales proposals and quotes",
        domain="contracts",
        module_path="src.agents.contracts.proposal_generator",
        class_name="ProposalGeneratorAgent",
        capabilities=["proposal_creation", "pricing", "customization"],
        icon="📝",
    ),
    AgentMeta(
        name="Contract Review",
        description="Reviews contracts for risks and issues",
        domain="contracts",
        module_path="src.agents.contracts.contract_review",
        class_name="ContractReviewAgent",
        capabilities=["risk_analysis", "clause_review", "compliance_check"],
        icon="🔏",
    ),
    AgentMeta(
        name="Pricing Calculator",
        description="Calculates pricing and generates quotes",
        domain="contracts",
        module_path="src.agents.contracts.pricing_calculator",
        class_name="PricingCalculatorAgent",
        capabilities=["pricing_models", "discount_rules", "quote_generation"],
        icon="💰",
    ),
    
    # Operations Domain
    AgentMeta(
        name="Revenue Ops",
        description="Revenue operations and forecasting",
        domain="ops",
        module_path="src.agents.ops.revenue_ops",
        class_name="RevenueOpsAgent",
        capabilities=["forecasting", "pipeline_analysis", "revenue_tracking"],
        icon="💵",
    ),
    AgentMeta(
        name="Competitor Watch",
        description="Monitors competitor activities and updates",
        domain="ops",
        module_path="src.agents.ops.competitor_watch",
        class_name="CompetitorWatchAgent",
        capabilities=["competitor_tracking", "market_intel", "alert_generation"],
        icon="👁️",
    ),
    AgentMeta(
        name="Partner Coordinator",
        description="Manages partner relationships and referrals",
        domain="ops",
        module_path="src.agents.ops.partner_coordinator",
        class_name="PartnerCoordinatorAgent",
        capabilities=["partner_management", "referral_tracking", "commission_calculation"],
        icon="🤝",
    ),
    
    # Data Hygiene Domain
    AgentMeta(
        name="Duplicate Watcher",
        description="Detects and manages duplicate records",
        domain="data_hygiene",
        module_path="src.agents.data_hygiene.duplicate_watcher",
        class_name="DuplicateWatcherAgent",
        capabilities=["duplicate_detection", "merge_suggestions", "deduplication"],
        icon="👯",
    ),
    AgentMeta(
        name="Contact Validation",
        description="Validates contact information accuracy",
        domain="data_hygiene",
        module_path="src.agents.data_hygiene.contact_validation",
        class_name="ContactValidationAgent",
        capabilities=["email_validation", "phone_validation", "address_verification"],
        icon="📇",
    ),
    AgentMeta(
        name="Data Decay Monitor",
        description="Monitors data freshness and decay",
        domain="data_hygiene",
        module_path="src.agents.data_hygiene.data_decay",
        class_name="DataDecayAgent",
        capabilities=["freshness_tracking", "decay_alerts", "refresh_suggestions"],
        icon="⏰",
    ),
    AgentMeta(
        name="Enrichment Orchestrator",
        description="Orchestrates data enrichment from multiple sources",
        domain="data_hygiene",
        module_path="src.agents.data_hygiene.enrichment_orchestrator",
        class_name="EnrichmentOrchestratorAgent",
        capabilities=["data_enrichment", "source_aggregation", "field_mapping"],
        icon="✨",
    ),
    AgentMeta(
        name="Sync Health Monitor",
        description="Monitors CRM sync health and data flow",
        domain="data_hygiene",
        module_path="src.agents.data_hygiene.sync_health",
        class_name="SyncHealthAgent",
        capabilities=["sync_monitoring", "error_detection", "reconciliation"],
        icon="🔄",
    ),
    
    # Master Agent
    AgentMeta(
        name="Jarvis",
        description="Master orchestrator that routes intents to specialized agents",
        domain="sales",
        module_path="src.agents.jarvis",
        class_name="Jarvis",
        capabilities=["intent_routing", "agent_orchestration", "tool_calling"],
        icon="🧙",
        status="active",
    ),
]


class AgentRegistry:
    """Singleton registry for all agents in CaseyOS."""
    
    _instance: Optional["AgentRegistry"] = None
    _agents: Dict[str, AgentMeta] = {}
    
    def __new__(cls) -> "AgentRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self) -> None:
        """Initialize registry with all known agents."""
        self._agents = {}
        
        # Load from manual registry
        for agent_meta in MANUAL_REGISTRY:
            key = f"{agent_meta.domain}:{agent_meta.name}"
            self._agents[key] = agent_meta
        
        logger.info(f"Agent registry initialized with {len(self._agents)} agents")
    
    def list_all(self) -> List[AgentMeta]:
        """Get all registered agents."""
        return list(self._agents.values())
    
    def get_by_domain(self, domain: str) -> List[AgentMeta]:
        """Get agents filtered by domain."""
        return [a for a in self._agents.values() if a.domain == domain]
    
    def get_by_name(self, name: str) -> Optional[AgentMeta]:
        """Get a specific agent by name."""
        for agent in self._agents.values():
            if agent.name.lower() == name.lower():
                return agent
        return None
    
    def get_by_class(self, class_name: str) -> Optional[AgentMeta]:
        """Get a specific agent by class name."""
        for agent in self._agents.values():
            if agent.class_name == class_name:
                return agent
        return None
    
    def list_domains(self) -> List[Dict[str, Any]]:
        """Get all domains with agent counts."""
        domains = {}
        for agent in self._agents.values():
            if agent.domain not in domains:
                config = DOMAIN_CONFIG.get(agent.domain, {})
                domains[agent.domain] = {
                    "id": agent.domain,
                    "label": config.get("label", agent.domain.title()),
                    "icon": config.get("icon", "📦"),
                    "color": config.get("color", "gray"),
                    "count": 0,
                }
            domains[agent.domain]["count"] += 1
        return list(domains.values())
    
    def get_agent_count(self) -> int:
        """Get total number of agents."""
        return len(self._agents)
    
    def search(self, query: str) -> List[AgentMeta]:
        """Search agents by name or description."""
        query = query.lower()
        return [
            a for a in self._agents.values()
            if query in a.name.lower() or query in a.description.lower()
        ]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert registry to dictionary for API."""
        return {
            "total": len(self._agents),
            "domains": self.list_domains(),
            "agents": [a.to_dict() for a in self._agents.values()],
        }


# Singleton getter
def get_agent_registry() -> AgentRegistry:
    """Get the singleton agent registry."""
    return AgentRegistry()
