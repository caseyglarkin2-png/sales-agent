"""Jarvis - The Master Orchestrator Agent for CaseyOS.

Jarvis is the single source of truth that coordinates all specialized agents.
It routes requests to the appropriate agent, aggregates responses, and maintains
context across the entire GTM operation.

Think of Jarvis as Casey's Chief of Staff who delegates to specialists.

Henry-style Evolution (Sprint 15):
- Persistent memory across sessions via MemoryService
- Semantic search for relevant context
- Automatic summarization of old conversations
"""
from datetime import datetime
from typing import Any, Dict, List, Optional, Type
from enum import Enum

from src.agents.base import BaseAgent
from src.logger import get_logger
from src.db import get_session
from src.services.memory_service import MemoryService

logger = get_logger(__name__)


class AgentDomain(str, Enum):
    """Domains that Jarvis can route to."""
    SALES = "sales"
    CONTENT = "content"
    FULFILLMENT = "fulfillment"
    CONTRACTS = "contracts"
    OPS = "ops"
    RESEARCH = "research"


class JarvisAgent(BaseAgent):
    """Master orchestrator that coordinates all CaseyOS agents.
    
    Jarvis is the single entry point for all agent operations. It:
    - Routes requests to specialized agents based on intent
    - Maintains conversation context across interactions
    - Aggregates responses from multiple agents when needed
    - Provides a unified API for the Command Queue
    
    Usage:
        jarvis = JarvisAgent()
        await jarvis.initialize()  # Load all agents
        
        # Ask Jarvis anything
        result = await jarvis.ask(
            "Draft a follow-up email for the TechCorp deal",
            context={"deal_id": "123", "contact_email": "john@techcorp.com"}
        )
    """

    def __init__(self):
        """Initialize Jarvis."""
        super().__init__(
            name="Jarvis",
            description="Master orchestrator coordinating all CaseyOS agents"
        )
        self._agents: Dict[str, BaseAgent] = {}
        self._agent_registry: Dict[str, Dict[str, Any]] = {}
        self._conversation_context: Dict[str, Any] = {}
        self._initialized = False
        
        # Henry-style persistent memory
        self._memory_enabled = True
        self._default_user_id = "casey"  # Default user for sessions

    async def initialize(
        self,
        gmail_connector=None,
        hubspot_connector=None,
        calendar_connector=None,
        drive_connector=None,
        llm_connector=None,
    ) -> None:
        """Initialize all agents with their connectors.
        
        Args:
            gmail_connector: Gmail API connector
            hubspot_connector: HubSpot API connector
            calendar_connector: Google Calendar connector
            drive_connector: Google Drive connector
            llm_connector: OpenAI/LLM connector
        """
        logger.info("Jarvis initializing agent network...")
        
        # Store connectors for agent initialization
        self._connectors = {
            "gmail": gmail_connector,
            "hubspot": hubspot_connector,
            "calendar": calendar_connector,
            "drive": drive_connector,
            "llm": llm_connector,
        }
        
        # Initialize Sales agents
        await self._init_sales_agents()
        
        # Initialize Content agents
        await self._init_content_agents()
        
        # Initialize Fulfillment agents
        await self._init_fulfillment_agents()
        
        # Initialize Contract agents
        await self._init_contract_agents()
        
        # Initialize Ops agents
        await self._init_ops_agents()
        
        # Initialize Research agents
        await self._init_research_agents()
        
        self._initialized = True
        logger.info(f"Jarvis initialized with {len(self._agents)} agents")

    async def _init_sales_agents(self) -> None:
        """Initialize sales domain agents."""
        from src.agents.prospecting import ProspectingAgent
        from src.agents.nurturing import NurturingAgent
        from src.agents.research import ResearchAgent
        from src.agents.specialized import (
            ThreadReaderAgent,
            LongMemoryAgent,
            AssetHunterAgent,
            MeetingSlotAgent,
            NextStepPlannerAgent,
            DraftWriterAgent,
        )
        from src.agents.validation import ValidationAgent
        
        # Register sales agents
        self._register_agent(
            "prospecting",
            ProspectingAgent(self._connectors.get("llm")),
            domain=AgentDomain.SALES,
            capabilities=["analyze_intent", "score_relevance", "generate_response"]
        )
        
        self._register_agent(
            "nurturing",
            NurturingAgent(self._connectors.get("hubspot")),
            domain=AgentDomain.SALES,
            capabilities=["follow_up_sequence", "create_tasks", "engagement_tracking"]
        )
        
        self._register_agent(
            "research",
            ResearchAgent(
                hubspot_connector=self._connectors.get("hubspot"),
                gmail_connector=self._connectors.get("gmail"),
            ),
            domain=AgentDomain.RESEARCH,
            capabilities=["enrich_prospect", "company_intel", "talking_points"]
        )
        
        self._register_agent(
            "thread_reader",
            ThreadReaderAgent(),
            domain=AgentDomain.SALES,
            capabilities=["summarize_thread", "extract_context"]
        )
        
        self._register_agent(
            "long_memory",
            LongMemoryAgent(gmail_connector=self._connectors.get("gmail")),
            domain=AgentDomain.SALES,
            capabilities=["find_patterns", "similar_situations"]
        )
        
        self._register_agent(
            "asset_hunter",
            AssetHunterAgent(drive_connector=self._connectors.get("drive")),
            domain=AgentDomain.SALES,
            capabilities=["find_assets", "proposal_search", "case_study_search"]
        )
        
        self._register_agent(
            "meeting_slot",
            MeetingSlotAgent(calendar_connector=self._connectors.get("calendar")),
            domain=AgentDomain.SALES,
            capabilities=["propose_slots", "check_availability"]
        )
        
        self._register_agent(
            "next_step",
            NextStepPlannerAgent(),
            domain=AgentDomain.SALES,
            capabilities=["select_cta", "plan_action"]
        )
        
        self._register_agent(
            "draft_writer",
            DraftWriterAgent(),
            domain=AgentDomain.SALES,
            capabilities=["write_email", "apply_voice_profile"]
        )
        
        self._register_agent(
            "validation",
            ValidationAgent(),
            domain=AgentDomain.SALES,
            capabilities=["compliance_check", "tone_analysis", "pii_detection"]
        )

    async def _init_content_agents(self) -> None:
        """Initialize content domain agents."""
        from src.agents.content.repurpose import ContentRepurposeAgent
        from src.agents.content.repurpose_v2 import ContentRepurposeAgentV2
        from src.agents.content.social_scheduler import SocialSchedulerAgent
        from src.agents.content.graphics_request import GraphicsRequestAgent
        
        self._register_agent(
            "content_repurpose",
            ContentRepurposeAgent(
                drive_connector=self._connectors.get("drive"),
                llm_connector=self._connectors.get("llm"),
            ),
            domain=AgentDomain.CONTENT,
            capabilities=["repurpose_content", "generate_posts", "create_threads"]
        )
        
        self._register_agent(
            "content_repurpose_v2",
            ContentRepurposeAgentV2(
                llm_connector=self._connectors.get("llm"),
            ),
            domain=AgentDomain.CONTENT,
            capabilities=["repurpose_transcript", "generate_linkedin_viral", "generate_newsletter_deep"]
        )
        
        self._register_agent(
            "social_scheduler",
            SocialSchedulerAgent(),
            domain=AgentDomain.CONTENT,
            capabilities=["schedule_post", "track_engagement", "optimize_timing"]
        )
        
        self._register_agent(
            "graphics_request",
            GraphicsRequestAgent(),
            domain=AgentDomain.CONTENT,
            capabilities=["create_brief", "queue_design", "brand_guidelines"]
        )

    async def _init_fulfillment_agents(self) -> None:
        """Initialize fulfillment domain agents."""
        from src.agents.fulfillment.deliverable_tracker import DeliverableTrackerAgent
        from src.agents.fulfillment.approval_gateway import ApprovalGatewayAgent
        from src.agents.fulfillment.client_health import ClientHealthAgent
        
        self._register_agent(
            "deliverable_tracker",
            DeliverableTrackerAgent(
                hubspot_connector=self._connectors.get("hubspot"),
            ),
            domain=AgentDomain.FULFILLMENT,
            capabilities=["track_deliverables", "flag_overdue", "send_reminders"]
        )
        
        self._register_agent(
            "approval_gateway",
            ApprovalGatewayAgent(
                hubspot_connector=self._connectors.get("hubspot"),
            ),
            domain=AgentDomain.FULFILLMENT,
            capabilities=["route_approval", "track_signoffs", "escalate"]
        )
        
        self._register_agent(
            "client_health",
            ClientHealthAgent(
                hubspot_connector=self._connectors.get("hubspot"),
                gmail_connector=self._connectors.get("gmail"),
            ),
            domain=AgentDomain.FULFILLMENT,
            capabilities=["monitor_engagement", "flag_risk", "renewal_alerts"]
        )

    async def _init_contract_agents(self) -> None:
        """Initialize contracts domain agents."""
        from src.agents.contracts.proposal_generator import ProposalGeneratorAgent
        from src.agents.contracts.contract_review import ContractReviewAgent
        from src.agents.contracts.pricing_calculator import PricingCalculatorAgent
        
        self._register_agent(
            "proposal_generator",
            ProposalGeneratorAgent(
                drive_connector=self._connectors.get("drive"),
                llm_connector=self._connectors.get("llm"),
            ),
            domain=AgentDomain.CONTRACTS,
            capabilities=["generate_proposal", "customize_template", "add_pricing"]
        )
        
        self._register_agent(
            "contract_review",
            ContractReviewAgent(
                llm_connector=self._connectors.get("llm"),
                drive_connector=self._connectors.get("drive"),
            ),
            domain=AgentDomain.CONTRACTS,
            capabilities=["review_contract", "flag_risks", "suggest_edits"]
        )
        
        self._register_agent(
            "pricing_calculator",
            PricingCalculatorAgent(),
            domain=AgentDomain.CONTRACTS,
            capabilities=["calculate_quote", "apply_discounts", "validate_pricing"]
        )

    async def _init_ops_agents(self) -> None:
        """Initialize ops domain agents."""
        from src.agents.ops.competitor_watch import CompetitorWatchAgent
        from src.agents.ops.revenue_ops import RevenueOpsAgent
        from src.agents.ops.partner_coordinator import PartnerCoordinatorAgent
        
        self._register_agent(
            "competitor_watch",
            CompetitorWatchAgent(
                llm_connector=self._connectors.get("llm"),
            ),
            domain=AgentDomain.OPS,
            capabilities=["track_competitors", "news_alerts", "market_intel"]
        )
        
        self._register_agent(
            "revenue_ops",
            RevenueOpsAgent(
                hubspot_connector=self._connectors.get("hubspot"),
            ),
            domain=AgentDomain.OPS,
            capabilities=["forecast_pipeline", "flag_stuck_deals", "commission_tracking"]
        )
        
        self._register_agent(
            "partner_coordinator",
            PartnerCoordinatorAgent(
                hubspot_connector=self._connectors.get("hubspot"),
                gmail_connector=self._connectors.get("gmail"),
            ),
            domain=AgentDomain.OPS,
            capabilities=["track_referrals", "cosell_opportunities", "partner_comms"]
        )

    async def _init_research_agents(self) -> None:
        """Initialize research domain agents."""
        from src.agents.research.research_deep import DeepResearchAgent
        
        self._register_agent(
            "deep_research",
            DeepResearchAgent(),
            domain=AgentDomain.RESEARCH,
            capabilities=["deep_dive_drive", "analyze_large_docs", "treasure_trove_search"]
        )

    def _register_agent(
        self,
        name: str,
        agent: BaseAgent,
        domain: AgentDomain,
        capabilities: List[str],
    ) -> None:
        """Register an agent with Jarvis."""
        self._agents[name] = agent
        self._agent_registry[name] = {
            "agent": agent,
            "domain": domain,
            "capabilities": capabilities,
            "registered_at": datetime.utcnow().isoformat(),
        }
        logger.debug(f"Registered agent: {name} ({domain.value})")

    async def validate_input(self, context: Dict[str, Any]) -> bool:
        """Validate input has required fields."""
        return "query" in context or "action" in context

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a request by routing to appropriate agents."""
        if not self._initialized:
            await self.initialize()
        
        query = context.get("query", "")
        action = context.get("action")
        
        # Route to specific agent if action specified
        if action:
            return await self._execute_action(action, context)
        
        # Otherwise, interpret the query and route
        return await self.ask(query, context)

    async def ask(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        session_name: str = "default",
    ) -> Dict[str, Any]:
        """Ask Jarvis a question or request an action.
        
        Jarvis will:
        1. Load relevant memory from persistent storage
        2. Interpret the intent
        3. Route to appropriate agent(s)
        4. Save the interaction to memory
        5. Aggregate and return results
        
        Args:
            query: Natural language query or command
            context: Additional context (deal_id, contact_email, etc.)
            user_id: User identifier for persistent memory (default: "casey")
            session_name: Named session for conversation grouping
            
        Returns:
            Aggregated response from relevant agents
        """
        if not self._initialized:
            await self.initialize()
        
        context = context or {}
        user_id = user_id or self._default_user_id
        logger.info(f"Jarvis received query: {query[:100]}...")
        
        # ========================================
        # Henry-style: Load persistent memory
        # ========================================
        memory_context = {}
        if self._memory_enabled:
            try:
                async with get_session() as db:
                    memory = MemoryService(db)
                    
                    # Get or create session
                    session = await memory.get_or_create_session(user_id, session_name)
                    
                    # Recall recent conversation
                    recent_messages = await memory.recall(str(session.id), limit=10)
                    
                    # Search for relevant context from past conversations
                    relevant_context = await memory.search_similar(
                        str(session.id), 
                        query, 
                        limit=3
                    )
                    
                    # Remember the user's query
                    await memory.remember(
                        session_id=str(session.id),
                        role="user",
                        content=query,
                        metadata={"context": context}
                    )
                    
                    memory_context = {
                        "session_id": str(session.id),
                        "recent_messages": recent_messages,
                        "relevant_context": relevant_context,
                        "session_topic": session.last_topic,
                    }
                    logger.debug(f"Loaded {len(recent_messages)} recent messages, {len(relevant_context)} relevant")
            except Exception as e:
                logger.warning(f"Memory service unavailable: {e}")
                memory_context = {"error": str(e)}
        
        # Update conversation context
        self._conversation_context.update(context)
        self._conversation_context.update(memory_context)
        self._conversation_context["last_query"] = query
        self._conversation_context["timestamp"] = datetime.utcnow().isoformat()
        
        # Determine which agents to invoke
        agents_to_invoke = await self._route_query(query, context)
        
        if not agents_to_invoke:
            return {
                "status": "no_match",
                "message": "I couldn't determine which agent should handle this request.",
                "suggestion": "Try being more specific about what you need.",
            }
        
        # Execute agents and aggregate results
        results = {}
        for agent_name in agents_to_invoke:
            agent_info = self._agent_registry.get(agent_name)
            if agent_info:
                try:
                    agent = agent_info["agent"]
                    agent_context = {
                        **context,
                        "query": query,
                        "conversation_context": self._conversation_context,
                    }
                    result = await agent.execute(agent_context)
                    results[agent_name] = {
                        "status": "success",
                        "domain": agent_info["domain"].value,
                        "result": result,
                    }
                except Exception as e:
                    logger.error(f"Agent {agent_name} failed: {e}")
                    results[agent_name] = {
                        "status": "error",
                        "error": str(e),
                    }
        
        response = {
            "status": "success",
            "query": query,
            "agents_invoked": list(results.keys()),
            "results": results,
            "timestamp": datetime.utcnow().isoformat(),
            "memory": {"session_id": memory_context.get("session_id")} if memory_context else None,
        }
        
        # ========================================
        # Henry-style: Save response to memory
        # ========================================
        if self._memory_enabled and memory_context.get("session_id"):
            try:
                async with get_session() as db:
                    memory = MemoryService(db)
                    
                    # Create a summary of the response for memory
                    response_summary = f"Invoked agents: {', '.join(results.keys())}. "
                    for agent_name, result in results.items():
                        if result.get("status") == "success":
                            agent_result = result.get("result", {})
                            if isinstance(agent_result, dict):
                                response_summary += f"{agent_name}: {agent_result.get('message', 'completed')}. "
                    
                    await memory.remember(
                        session_id=memory_context["session_id"],
                        role="assistant",
                        content=response_summary[:1000],  # Limit to 1000 chars
                        metadata={
                            "agents_invoked": list(results.keys()),
                            "status": "success",
                        }
                    )
            except Exception as e:
                logger.warning(f"Failed to save response to memory: {e}")
        
        return response

    async def _route_query(
        self,
        query: str,
        context: Dict[str, Any],
    ) -> List[str]:
        """Determine which agents should handle this query.
        
        Uses keyword matching for now; can be upgraded to LLM-based routing.
        """
        query_lower = query.lower()
        agents = []
        
        # Sales routing
        if any(word in query_lower for word in ["email", "draft", "outreach", "follow up", "prospect"]):
            agents.extend(["draft_writer", "research"])
        if any(word in query_lower for word in ["meeting", "schedule", "calendar", "slot"]):
            agents.append("meeting_slot")
        if any(word in query_lower for word in ["nurture", "sequence", "engagement"]):
            agents.append("nurturing")
        
        # Content routing
        if any(word in query_lower for word in ["content", "repurpose", "linkedin", "twitter", "post"]):
            agents.append("content_repurpose")
        if any(word in query_lower for word in ["social", "schedule post", "engagement"]):
            agents.append("social_scheduler")
        if any(word in query_lower for word in ["graphic", "design", "image", "visual"]):
            agents.append("graphics_request")
        
        # Fulfillment routing
        if any(word in query_lower for word in ["deliverable", "deadline", "overdue", "project"]):
            agents.append("deliverable_tracker")
        if any(word in query_lower for word in ["approval", "sign off", "approve"]):
            agents.append("approval_gateway")
        if any(word in query_lower for word in ["client health", "churn", "renewal", "risk"]):
            agents.append("client_health")
        
        # Contract routing
        if any(word in query_lower for word in ["proposal", "generate proposal"]):
            agents.append("proposal_generator")
        if any(word in query_lower for word in ["contract", "review", "clause", "terms"]):
            agents.append("contract_review")
        if any(word in query_lower for word in ["price", "quote", "pricing", "discount"]):
            agents.append("pricing_calculator")
        
        # Ops routing
        if any(word in query_lower for word in ["competitor", "competition", "market"]):
            agents.append("competitor_watch")
        if any(word in query_lower for word in ["pipeline", "forecast", "revenue", "commission"]):
            agents.append("revenue_ops")
        if any(word in query_lower for word in ["partner", "referral", "cosell"]):
            agents.append("partner_coordinator")
        
        # Research is often needed as context
        if any(word in query_lower for word in ["research", "intel", "background", "info about"]):
            agents.append("research")

        # Deep Research
        if any(word in query_lower for word in ["drive", "deep dive", "treasure trove", "contract", "files", "pesti", "yardflow"]):
            agents.append("deep_research") 
        
        return list(set(agents))  # Dedupe

    async def _execute_action(
        self,
        action: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a specific action on a specific agent."""
        agent_name = context.get("agent")
        if not agent_name or agent_name not in self._agents:
            return {"status": "error", "error": f"Unknown agent: {agent_name}"}
        
        agent = self._agents[agent_name]
        return await agent.execute(context)

    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """Get a specific agent by name."""
        return self._agents.get(name)

    def list_agents(self) -> Dict[str, Dict[str, Any]]:
        """List all registered agents with their capabilities."""
        result = {}
        for name, info in self._agent_registry.items():
            agent = info["agent"]
            # Handle agents that may not extend BaseAgent properly
            description = getattr(agent, 'description', None)
            if description is None:
                # Try to get from docstring
                description = agent.__class__.__doc__ or f"{name} agent"
                # Clean up multiline docstrings
                description = description.strip().split('\n')[0]
            result[name] = {
                "domain": info["domain"].value,
                "capabilities": info["capabilities"],
                "description": description,
            }
        return result

    def get_agents_by_domain(self, domain: AgentDomain) -> List[str]:
        """Get all agents in a specific domain."""
        return [
            name for name, info in self._agent_registry.items()
            if info["domain"] == domain
        ]

    # =========================================================================
    # Sprint 36: Gemini Tool Integration
    # =========================================================================
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """
        Get Gemini-compatible tool definitions for agent capabilities.
        
        Returns tool definitions that Gemini can use to call Jarvis actions.
        """
        return [
            {
                "name": "search_drive",
                "description": "Search Google Drive for files and documents",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query (company name, topic, etc.)"
                        },
                        "file_types": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "File types to search: document, spreadsheet, presentation, pdf"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "draft_email",
                "description": "Draft an email to a contact",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "to_email": {
                            "type": "string",
                            "description": "Recipient email address"
                        },
                        "subject": {
                            "type": "string",
                            "description": "Email subject line"
                        },
                        "context": {
                            "type": "string",
                            "description": "Context for the email (what it should be about)"
                        },
                        "tone": {
                            "type": "string",
                            "description": "Tone: professional, friendly, urgent, casual"
                        }
                    },
                    "required": ["to_email", "context"]
                }
            },
            {
                "name": "search_hubspot",
                "description": "Search HubSpot CRM for contacts, companies, or deals",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query (name, email, company)"
                        },
                        "object_type": {
                            "type": "string",
                            "description": "Object to search: contact, company, deal"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "get_contact_info",
                "description": "Get detailed information about a contact",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "email": {
                            "type": "string",
                            "description": "Contact email address"
                        }
                    },
                    "required": ["email"]
                }
            },
            {
                "name": "check_calendar",
                "description": "Check calendar availability",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "start_date": {
                            "type": "string",
                            "description": "Start date (YYYY-MM-DD)"
                        },
                        "end_date": {
                            "type": "string",
                            "description": "End date (YYYY-MM-DD)"
                        }
                    },
                    "required": ["start_date"]
                }
            },
            {
                "name": "schedule_meeting",
                "description": "Schedule a meeting on the calendar",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Meeting title"
                        },
                        "attendees": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Attendee email addresses"
                        },
                        "datetime": {
                            "type": "string",
                            "description": "Meeting datetime (ISO format)"
                        },
                        "duration_minutes": {
                            "type": "integer",
                            "description": "Meeting duration in minutes"
                        }
                    },
                    "required": ["title", "attendees", "datetime"]
                }
            },
            {
                "name": "research_company",
                "description": "Research a company for sales context",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "company_name": {
                            "type": "string",
                            "description": "Company name to research"
                        },
                        "depth": {
                            "type": "string",
                            "description": "Research depth: quick, standard, deep"
                        }
                    },
                    "required": ["company_name"]
                }
            }
        ]
    
    async def handle_tool_call(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Handle a tool call from Gemini.
        
        Routes the tool call to the appropriate agent and returns results.
        
        Args:
            tool_name: Name of the tool being called
            tool_args: Arguments passed to the tool
            
        Returns:
            Result dict from the agent execution
        """
        logger.info(f"Jarvis handling tool call: {tool_name} with args: {tool_args}")
        
        try:
            if tool_name == "search_drive":
                agent = self._agents.get("asset_hunter")
                if agent:
                    return await agent.execute({
                        "action": "search",
                        "query": tool_args.get("query"),
                        "file_types": tool_args.get("file_types"),
                    })
                return {"status": "error", "error": "Asset hunter agent not available"}
            
            elif tool_name == "draft_email":
                agent = self._agents.get("draft_writer")
                if agent:
                    return await agent.execute({
                        "action": "draft",
                        "to_email": tool_args.get("to_email"),
                        "subject": tool_args.get("subject"),
                        "context": tool_args.get("context"),
                        "tone": tool_args.get("tone", "professional"),
                    })
                return {"status": "error", "error": "Draft writer agent not available"}
            
            elif tool_name == "search_hubspot":
                agent = self._agents.get("research")
                if agent:
                    return await agent.execute({
                        "action": "search_crm",
                        "query": tool_args.get("query"),
                        "object_type": tool_args.get("object_type", "contact"),
                    })
                return {"status": "error", "error": "Research agent not available"}
            
            elif tool_name == "get_contact_info":
                agent = self._agents.get("research")
                if agent:
                    return await agent.execute({
                        "action": "get_contact",
                        "email": tool_args.get("email"),
                    })
                return {"status": "error", "error": "Research agent not available"}
            
            elif tool_name == "check_calendar":
                agent = self._agents.get("meeting_slot")
                if agent:
                    return await agent.execute({
                        "action": "check_availability",
                        "start_date": tool_args.get("start_date"),
                        "end_date": tool_args.get("end_date"),
                    })
                return {"status": "error", "error": "Meeting slot agent not available"}
            
            elif tool_name == "schedule_meeting":
                agent = self._agents.get("meeting_slot")
                if agent:
                    return await agent.execute({
                        "action": "schedule",
                        "title": tool_args.get("title"),
                        "attendees": tool_args.get("attendees"),
                        "datetime": tool_args.get("datetime"),
                        "duration_minutes": tool_args.get("duration_minutes", 30),
                    })
                return {"status": "error", "error": "Meeting slot agent not available"}
            
            elif tool_name == "research_company":
                agent = self._agents.get("research")
                if agent:
                    return await agent.execute({
                        "action": "company_intel",
                        "company_name": tool_args.get("company_name"),
                        "depth": tool_args.get("depth", "standard"),
                    })
                return {"status": "error", "error": "Research agent not available"}
            
            else:
                return {"status": "error", "error": f"Unknown tool: {tool_name}"}
                
        except Exception as e:
            logger.error(f"Tool call error for {tool_name}: {e}")
            return {"status": "error", "error": str(e)}
    
    async def ask_with_tools(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        max_tool_calls: int = 5,
    ) -> Dict[str, Any]:
        """
        Ask Jarvis with automatic tool calling support.
        
        Uses Gemini to decide when to call tools and orchestrates
        the multi-step conversation.
        
        Args:
            query: User query
            context: Additional context
            max_tool_calls: Maximum tool calls per request
            
        Returns:
            Final response with all tool results incorporated
        """
        from src.connectors.gemini import get_gemini
        
        gemini = get_gemini()
        tools = self.get_tool_definitions()
        
        system_instruction = """You are Jarvis, the AI orchestrator for CaseyOS - a B2B GTM command center.
You have access to tools for:
- Searching Google Drive for documents and proposals
- Drafting emails to contacts
- Searching HubSpot CRM for contacts, companies, and deals
- Checking and scheduling calendar events
- Researching companies

When a user asks a question, decide if you need to use any tools to answer it.
If the question can be answered directly, respond without tools.
If you need information from Drive, CRM, or calendar, use the appropriate tool.

Be concise and action-oriented in your responses."""

        tool_results = []
        current_prompt = query
        
        for i in range(max_tool_calls):
            result = await gemini.generate_with_tools(
                prompt=current_prompt,
                tools=tools,
                system_instruction=system_instruction,
            )
            
            if result["type"] == "text":
                # Final text response
                return {
                    "status": "success",
                    "response": result["content"],
                    "tool_calls": tool_results,
                }
            
            elif result["type"] == "tool_call":
                # Execute the tool
                tool_name = result["name"]
                tool_args = result["args"]
                
                tool_result = await self.handle_tool_call(tool_name, tool_args)
                tool_results.append({
                    "tool": tool_name,
                    "args": tool_args,
                    "result": tool_result,
                })
                
                # Continue conversation with tool result
                result = await gemini.continue_with_tool_result(
                    original_prompt=query,
                    tool_name=tool_name,
                    tool_result=tool_result,
                    tools=tools,
                    system_instruction=system_instruction,
                )
                
                if result["type"] == "text":
                    return {
                        "status": "success",
                        "response": result["content"],
                        "tool_calls": tool_results,
                    }
                    
            elif result["type"] == "error":
                return {
                    "status": "error",
                    "error": result["message"],
                    "tool_calls": tool_results,
                }
        
        return {
            "status": "error",
            "error": f"Max tool calls ({max_tool_calls}) exceeded",
            "tool_calls": tool_results,
        }


# Singleton instance
_jarvis_instance: Optional[JarvisAgent] = None


def get_jarvis() -> JarvisAgent:
    """Get the singleton Jarvis instance."""
    global _jarvis_instance
    if _jarvis_instance is None:
        _jarvis_instance = JarvisAgent()
    return _jarvis_instance


async def reset_jarvis() -> None:
    """Reset Jarvis (for testing)."""
    global _jarvis_instance
    _jarvis_instance = None
