"""Tests for Sprint 43 - Gemini-Agent Integration.

Tests for:
- Expanded Jarvis tool definitions
- Context passing between agents
- Workflow templates
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.jarvis import JarvisAgent
from src.agents.workflows import (
    get_workflow_template,
    list_workflow_templates,
    get_workflow_categories,
    WORKFLOW_REGISTRY,
)
from src.services.context_service import (
    WorkflowContext,
    ContextService,
    get_context_service,
)


class TestJarvisToolDefinitions:
    """Test expanded Jarvis tool definitions (Task 43.1)."""
    
    def test_has_minimum_tools(self):
        """Should have at least 20 tool definitions."""
        jarvis = JarvisAgent()
        tools = jarvis.get_tool_definitions()
        assert len(tools) >= 20, f"Expected 20+ tools, got {len(tools)}"
    
    def test_tools_have_required_fields(self):
        """All tools should have name, description, and parameters."""
        jarvis = JarvisAgent()
        tools = jarvis.get_tool_definitions()
        
        for tool in tools:
            assert "name" in tool, f"Tool missing 'name': {tool}"
            assert "description" in tool, f"Tool missing 'description': {tool}"
            assert "parameters" in tool, f"Tool missing 'parameters': {tool}"
    
    def test_core_tools_present(self):
        """Should have core sales tools."""
        jarvis = JarvisAgent()
        tools = jarvis.get_tool_definitions()
        tool_names = {t["name"] for t in tools}
        
        required = {
            "search_drive",
            "draft_email",
            "search_hubspot",
            "research_company",
            "check_calendar",
            "schedule_meeting",
        }
        
        for name in required:
            assert name in tool_names, f"Missing core tool: {name}"
    
    def test_expanded_tools_present(self):
        """Should have Sprint 43 expanded tools."""
        jarvis = JarvisAgent()
        tools = jarvis.get_tool_definitions()
        tool_names = {t["name"] for t in tools}
        
        expanded = {
            "analyze_account",
            "score_lead",
            "generate_proposal",
            "handle_objection",
            "repurpose_content",
            "enrich_contact",
        }
        
        for name in expanded:
            assert name in tool_names, f"Missing expanded tool: {name}"


class TestWorkflowContext:
    """Test WorkflowContext class (Task 43.2)."""
    
    def test_create_context(self):
        """Should create context with initial data."""
        ctx = WorkflowContext(initial_context={"company": "Acme"})
        
        assert ctx.workflow_id is not None
        assert ctx.shared_context["company"] == "Acme"
        assert ctx.current_step == 0
        assert ctx.status == "pending"
    
    def test_add_step_result(self):
        """Should record step results and merge context."""
        ctx = WorkflowContext()
        
        ctx.add_step_result(
            agent_name="research_agent",
            input_data={"company_name": "Acme"},
            output_data={"company_info": {"size": "large"}, "insights": ["growing"]},
            success=True,
            duration_ms=100,
        )
        
        assert len(ctx.steps) == 1
        assert ctx.current_step == 1
        assert ctx.shared_context["company_info"]["size"] == "large"
        assert "insights" in ctx.shared_context
    
    def test_context_for_next_step(self):
        """Should include previous step info in next step context."""
        ctx = WorkflowContext(initial_context={"target": "Acme"})
        
        ctx.add_step_result(
            agent_name="step1",
            input_data={},
            output_data={"contacts": [{"email": "test@acme.com"}]},
            success=True,
        )
        
        next_ctx = ctx.get_context_for_next_step()
        
        assert "workflow_id" in next_ctx
        assert next_ctx["step_number"] == 2
        assert len(next_ctx["previous_steps"]) == 1
        assert "contacts" in next_ctx
        assert "target" in next_ctx
    
    def test_expiration(self):
        """Should detect expired contexts."""
        ctx = WorkflowContext(ttl_minutes=0)  # Expires immediately
        ctx.expires_at = datetime.utcnow() - timedelta(minutes=1)
        
        assert ctx.is_expired() is True
    
    def test_serialization(self):
        """Should serialize and deserialize context."""
        original = WorkflowContext(initial_context={"key": "value"})
        original.add_step_result("agent", {"a": 1}, {"b": 2}, True, 50)
        
        data = original.to_dict()
        restored = WorkflowContext.from_dict(data)
        
        assert str(restored.workflow_id) == str(original.workflow_id)
        assert len(restored.steps) == 1
        assert restored.shared_context["key"] == "value"


class TestContextService:
    """Test ContextService (Task 43.2)."""
    
    @pytest.mark.asyncio
    async def test_create_and_get_context(self):
        """Should create and retrieve contexts."""
        service = ContextService()
        
        ctx = await service.create_context(
            initial_data={"company": "TestCo"},
            ttl_minutes=30,
        )
        
        assert ctx.status == "running"
        
        retrieved = await service.get_context(str(ctx.workflow_id))
        assert retrieved is not None
        assert retrieved.shared_context["company"] == "TestCo"
    
    @pytest.mark.asyncio
    async def test_update_context(self):
        """Should update context with step results."""
        service = ContextService()
        ctx = await service.create_context()
        
        updated = await service.update_context(
            workflow_id=str(ctx.workflow_id),
            agent_name="test_agent",
            input_data={"x": 1},
            output_data={"research_data": {"key": "value"}},
            success=True,
            duration_ms=100,
        )
        
        assert updated is not None
        assert len(updated.steps) == 1
        assert "research_data" in updated.shared_context
    
    @pytest.mark.asyncio
    async def test_complete_context(self):
        """Should mark context as completed."""
        service = ContextService()
        ctx = await service.create_context()
        
        completed = await service.complete_context(
            str(ctx.workflow_id),
            status="completed",
        )
        
        assert completed.status == "completed"
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_none(self):
        """Should return None for missing context."""
        service = ContextService()
        
        result = await service.get_context("nonexistent-id")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_cleanup_expired(self):
        """Should clean up expired contexts."""
        service = ContextService()
        
        # Create expired context
        ctx = await service.create_context(ttl_minutes=0)
        ctx.expires_at = datetime.utcnow() - timedelta(minutes=1)
        
        count = await service.cleanup_expired()
        assert count == 1
        
        # Should be gone
        result = await service.get_context(str(ctx.workflow_id))
        assert result is None


class TestWorkflowTemplates:
    """Test workflow templates (Task 43.3)."""
    
    def test_registry_has_templates(self):
        """Should have pre-defined workflow templates."""
        assert len(WORKFLOW_REGISTRY) >= 5
    
    def test_get_workflow_template(self):
        """Should retrieve template by ID."""
        template = get_workflow_template("account_research")
        
        assert template is not None
        assert template.name == "Account Research"
        assert len(template.steps) >= 3
        assert "company_name" in template.required_inputs
    
    def test_get_nonexistent_template(self):
        """Should return None for missing template."""
        template = get_workflow_template("nonexistent")
        assert template is None
    
    def test_list_all_templates(self):
        """Should list all templates."""
        templates = list_workflow_templates()
        
        assert len(templates) >= 5
        assert all(hasattr(t, "name") for t in templates)
    
    def test_list_by_category(self):
        """Should filter templates by category."""
        sales = list_workflow_templates(category="sales")
        research = list_workflow_templates(category="research")
        
        assert all(t.category == "sales" for t in sales)
        assert all(t.category == "research" for t in research)
    
    def test_get_categories(self):
        """Should return category counts."""
        categories = get_workflow_categories()
        
        assert len(categories) >= 3
        assert all("id" in c and "count" in c for c in categories)
    
    def test_template_to_dict(self):
        """Should serialize template to dict."""
        template = get_workflow_template("new_deal")
        data = template.to_dict()
        
        assert data["id"] == "new_deal"
        assert "steps" in data
        assert "required_inputs" in data
        assert len(data["steps"]) == len(template.steps)
    
    def test_templates_have_valid_structure(self):
        """All templates should have valid structure."""
        for template in list_workflow_templates():
            assert template.id, f"Template missing id"
            assert template.name, f"Template missing name"
            assert template.steps, f"Template {template.id} has no steps"
            
            for step in template.steps:
                assert step.agent_name, f"Step missing agent_name in {template.id}"
                assert step.action, f"Step missing action in {template.id}"


class TestGeminiApiWorkflows:
    """Test Gemini API workflow endpoints (Task 43.3)."""
    
    @pytest.mark.asyncio
    async def test_list_workflows_endpoint(self):
        """Should list workflows via API."""
        from src.routes.gemini_api import list_workflows
        
        result = await list_workflows(category=None)
        
        assert "workflows" in result
        assert "categories" in result
        assert "total" in result
        assert result["total"] >= 5
    
    @pytest.mark.asyncio
    async def test_get_workflow_endpoint(self):
        """Should get workflow by ID via API."""
        from src.routes.gemini_api import get_workflow
        
        result = await get_workflow("meeting_prep")
        
        assert result["id"] == "meeting_prep"
        assert "steps" in result
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_workflow_raises(self):
        """Should raise 404 for missing workflow."""
        from src.routes.gemini_api import get_workflow
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            await get_workflow("nonexistent")
        
        assert exc_info.value.status_code == 404
