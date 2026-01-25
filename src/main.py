"""FastAPI application entry point."""
import logging
import os

# Force rebuild: v2.0.1

from fastapi import FastAPI
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from src.config import get_settings
from src.logger import configure_logging, get_logger
from src.middleware import TraceIDMiddleware
from src.security.middleware import CSRFMiddleware, SecurityHeaderMiddleware
from src.sentry_integration import init_sentry
from src.shutdown import register_shutdown_handlers
from src.routes import agents as agents_routes
from src.routes import operator as operator_routes
from src.routes import webhooks as webhooks_routes
from src.routes import voice as voice_routes
from src.routes import metrics as metrics_routes
from src.routes import bulk as bulk_routes
from src.routes import enrichment as enrichment_routes
from src.routes import proposals as proposals_routes
from src.routes import sequences as sequences_routes
from src.routes import docs as docs_routes
from src.routes import accounts as accounts_routes
from src.routes import history as history_routes
from src.routes import analytics as analytics_routes
from src.routes import agenda as agenda_routes
from src.routes import tracking as tracking_routes
from src.routes import linkedin as linkedin_routes
from src.routes import meetings as meetings_routes
from src.routes import dashboard as dashboard_routes
from src.routes import ab_testing as ab_testing_routes
from src.routes import scoring as scoring_routes
from src.routes import notifications as notifications_routes
from src.routes import templates as templates_routes
from src.routes import campaigns as campaigns_routes
from src.routes import insights as insights_routes
from src.routes import reports as reports_routes
from src.routes import imports as imports_routes
from src.routes import workflows as workflows_routes
from src.routes import classification as classification_routes
from src.routes import personalization as personalization_routes
from src.routes import monitoring as monitoring_routes
from src.routes import deliverability as deliverability_routes
from src.routes import deduplication as deduplication_routes
from src.routes import collaboration as collaboration_routes
from src.routes import segmentation as segmentation_routes
from src.routes import timeline as timeline_routes
from src.routes import goals as goals_routes
from src.routes import crm_sync as crm_sync_routes
from src.routes import tasks as tasks_routes
from src.routes import pipeline as pipeline_routes
from src.routes import email_generator as email_generator_routes
from src.routes import notes as notes_routes
from src.routes import companies as companies_routes
from src.routes import audit as audit_routes
from src.routes import outbound_webhooks as outbound_webhooks_routes
from src.routes import exports as exports_routes
from src.routes import api_keys as api_keys_routes
from src.routes import users as users_routes
from src.routes import settings_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import quotes_routes
from src.routes import products_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import forecasts_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import territories_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import competitors_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import commissions_routes
from src.routes import contracts_routes
from src.routes import approvals_routes
from src.routes import subscriptions_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import playbooks_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import learning_routes
from src.routes import integrations_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import invoices_routes
from src.routes import documents_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import events_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import calls_routes
from src.routes import email_tracking_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import roles_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import teams_routes
from src.routes import queue as queue_routes
from src.routes import custom_fields_routes
from src.routes import tags_routes
from src.routes import content_ingest as content_ingest_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import automation_routes
from src.routes import notification_prefs_routes
from src.routes import data_sync_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import gamification_routes
from src.routes import search_routes
from src.routes import recommendations_routes
from src.routes import webhook_subscriptions_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import activity_feed_routes
from src.routes import quota_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import social_selling_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import scheduling_routes
from src.routes import connectors_routes
from src.routes import outreach_routes
from src.routes import queue_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import reporting_routes
from src.routes import auth_routes
from src.routes import commands_routes
from src.routes import gdpr
from src.routes import circuit_breakers
from src.routes import health
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import partner_portal_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import meeting_intelligence_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import revenue_intelligence_routes
from src.routes import admin_flags
from src.routes import dashboard_api
from src.routes import customer_success_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import email_templates_v2_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import cpq_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import sales_enablement_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import lead_scoring_v2_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import abm_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import conversation_intelligence_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import sales_coaching_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import buyer_intent_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import data_quality_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import contact_enrichment_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import competitive_intelligence_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import territories_v2_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import deal_room_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import subscriptions_v2_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import revops_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import gamification_v2_routes
from src.routes import document_generation_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import customer_360_routes
from src.routes import multi_channel_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import workflows_v2_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import activity_capture_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import ai_assistant_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import mobile_sync_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import forecasting_v2_routes
from src.routes import calendar_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import pipeline_analytics_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import deliverability_v2_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import proposals_v2_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import integration_hub_routes
from src.routes import deal_scoring_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import product_analytics_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import revenue_attribution_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import lead_routing_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import account_planning_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import customer_health_v2_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import playbooks_v2_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import team_performance_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import email_analytics_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import sales_metrics_routes
from src.routes import notifications_routes as notifications_v2_routes
from src.routes import webhooks_routes as webhooks_v2_routes
from src.routes import sequences_routes as sequences_v2_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import content_library_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import email_warmup_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import referral_tracking_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import task_automation_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import partner_management_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import meeting_scheduler_v2_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import roi_calculator_routes
from src.routes import contact_queue
from src.routes import forms as forms_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import proposal_templates_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import sales_objections_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import sales_contests_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import commission_calculator_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import territory_mapping_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import lead_enrichment_v2_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import sales_forecasting_ai_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import deal_insights_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import customer_journey_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import engagement_scoring_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import deal_velocity_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import sales_playbook_ai_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import revops_v2_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import win_loss_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import sales_coaching_ai_routes
# REMOVED Sprint 22 Task 5 - Unused route
# from src.routes import quote_management_routes
from src.routes import contract_lifecycle_routes
from src.routes import churn_prediction_routes
from src.routes import sales_compensation_routes
from src.routes import onboarding_workflows_routes
from src.routes import voice_approval_routes
from src.routes import voice_training_api
from src.routes import pii_safety_api
from src.routes import celery_tasks
from src.routes import admin
from src.routes import quota_api
from src.routes import analytics_api
from src.routes import debug_api
from src.routes import integrations_api
from src.routes import ops
from src.routes import command_queue
from src.routes import ui_command_queue
from src.routes import signals as signals_routes
from src.routes import web_auth  # CaseyOS Sprint 1: Web OAuth
from src.routes import hubspot_signals  # CaseyOS Sprint 3: HubSpot Signal Ingestion
from src.routes import hubspot_webhooks  # HubSpot CRM Real-Time Webhooks
from src.routes import actions as actions_routes  # CaseyOS Sprint 9: Action Execution
from src.routes import outcomes as outcomes_routes  # CaseyOS Sprint 10: Closed-Loop Outcomes
from src.routes import caseyos_ui  # CaseyOS Sprint 11: Unified Dashboard
from src.routes import celery_health  # Task 8.18: Celery Beat Health Check
from src.routes import llm_api  # LLM: Multi-provider AI (OpenAI + Gemini)
from src.routes import jarvis_api  # Jarvis: Master AI Orchestrator
from src.routes import memory as memory_routes  # Sprint 15: Jarvis Persistent Memory
from src.routes import twitter_oauth  # Twitter OAuth for personal feed access
from src.routes import grok_routes  # Grok: xAI Market Intelligence (Sprint 13)
from src.routes import mcp_routes  # Sprint 20: MCP Server Integration

# Configure logging
settings = get_settings()
configure_logging(log_level=settings.log_level, log_format=settings.log_format)

logger = get_logger(__name__)

# Initialize Sentry for error tracking (Sprint 6 - Task 6.4)
init_sentry()

# Create FastAPI app
app = FastAPI(
    title="Sales Agent",
    description="Operator-mode prospecting and nurturing agent",
    version="0.1.0",
)

# Register graceful shutdown handlers (Sprint 6 - Task 6.7)
register_shutdown_handlers(app)

# Add middleware
app.add_middleware(SecurityHeaderMiddleware)  # Security headers (X-* headers)
app.add_middleware(CSRFMiddleware)  # CSRF protection on POST/PUT/DELETE
app.add_middleware(TraceIDMiddleware)

# Include routers
app.include_router(web_auth.router)  # CaseyOS Sprint 1: Web OAuth (login, logout, dashboard)
app.include_router(health.router)  # Sprint 6: Health check endpoints
app.include_router(celery_health.router)  # Task 8.18: Celery Beat Health Check
app.include_router(queue_routes.router)  # Morning email queue
app.include_router(agents_routes.router)
app.include_router(operator_routes.router)
app.include_router(webhooks_routes.router)
app.include_router(celery_tasks.router)  # Sprint 2: Async task management
app.include_router(admin.router)  # Sprint 4: Admin controls + emergency kill switch
app.include_router(gdpr.router)  # Sprint 6: GDPR data deletion + retention
app.include_router(circuit_breakers.router)  # Sprint 6: Circuit breaker monitoring
app.include_router(ops.router)  # Ops: Sentry test and admin operations
app.include_router(command_queue.router)  # CaseyOS: Command Queue API v0
app.include_router(ui_command_queue.router)  # CaseyOS: Command Queue UI v0
app.include_router(signals_routes.router)  # CaseyOS: Signals API (Sprint 8)
app.include_router(hubspot_signals.router)  # CaseyOS: HubSpot Signal Ingestion (Sprint 3)
app.include_router(hubspot_webhooks.router)  # HubSpot CRM Real-Time Webhooks
app.include_router(actions_routes.router)  # CaseyOS Sprint 9: Action Execution
app.include_router(outcomes_routes.router)  # CaseyOS Sprint 10: Closed-Loop Outcomes
app.include_router(caseyos_ui.router)  # CaseyOS Sprint 11: Unified Dashboard UI
app.include_router(jarvis_api.router)  # Jarvis: Master AI Orchestrator + Agent Hub
app.include_router(memory_routes.router)  # Sprint 15: Jarvis Persistent Memory API
app.include_router(llm_api.router)  # LLM: Multi-provider AI (OpenAI + Gemini)
app.include_router(twitter_oauth.router)  # Twitter OAuth for personal feed access
app.include_router(grok_routes.router)  # Grok: xAI Market Intelligence (Sprint 13)
app.include_router(mcp_routes.router)  # Sprint 20: MCP Server Integration
app.include_router(voice_routes.router)
app.include_router(contact_queue.router)
app.include_router(forms_routes.router)
app.include_router(metrics_routes.router)
app.include_router(bulk_routes.router)
app.include_router(enrichment_routes.router)
app.include_router(proposals_routes.router)
app.include_router(sequences_routes.router)
app.include_router(docs_routes.router)
app.include_router(accounts_routes.router)
app.include_router(history_routes.router)
app.include_router(analytics_routes.router)
app.include_router(agenda_routes.router)
app.include_router(tracking_routes.router)
app.include_router(linkedin_routes.router)
app.include_router(meetings_routes.router)
app.include_router(dashboard_routes.router)
app.include_router(ab_testing_routes.router)
app.include_router(scoring_routes.router)
app.include_router(notifications_routes.router)
app.include_router(templates_routes.router)
app.include_router(campaigns_routes.router)
app.include_router(insights_routes.router)
app.include_router(reports_routes.router)
app.include_router(imports_routes.router)
app.include_router(workflows_routes.router)
app.include_router(classification_routes.router)
app.include_router(personalization_routes.router)
app.include_router(monitoring_routes.router)
app.include_router(deliverability_routes.router)
app.include_router(deduplication_routes.router)
app.include_router(collaboration_routes.router)
app.include_router(segmentation_routes.router)
app.include_router(timeline_routes.router)
app.include_router(goals_routes.router)
app.include_router(crm_sync_routes.router)
app.include_router(tasks_routes.router)
app.include_router(pipeline_routes.router)
app.include_router(email_generator_routes.router)
app.include_router(notes_routes.router)
app.include_router(companies_routes.router)
app.include_router(audit_routes.router)
app.include_router(outbound_webhooks_routes.router)
app.include_router(exports_routes.router)
app.include_router(api_keys_routes.router)
app.include_router(users_routes.router)
app.include_router(settings_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(quotes_routes.router)
app.include_router(products_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(forecasts_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(territories_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(competitors_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(commissions_routes.router)
app.include_router(contracts_routes.router)
app.include_router(approvals_routes.router)
app.include_router(subscriptions_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(playbooks_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(learning_routes.router)
app.include_router(integrations_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(invoices_routes.router)
app.include_router(documents_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(events_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(calls_routes.router)
app.include_router(email_tracking_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(roles_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(teams_routes.router)
app.include_router(custom_fields_routes.router)
app.include_router(tags_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(automation_routes.router)
app.include_router(notification_prefs_routes.router)
app.include_router(data_sync_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(gamification_routes.router)
app.include_router(search_routes.router)
app.include_router(recommendations_routes.router)
app.include_router(webhook_subscriptions_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(activity_feed_routes.router)
app.include_router(quota_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(social_selling_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(scheduling_routes.router)
app.include_router(connectors_routes.router)
app.include_router(outreach_routes.router)
app.include_router(queue_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(reporting_routes.router)
app.include_router(voice_training_api.router)  # Voice training enhancement
app.include_router(pii_safety_api.router)  # PII detection & safety validation
app.include_router(quota_api.router)  # Rate limiting & quota management
app.include_router(analytics_api.router)  # Analytics & insights engine
app.include_router(debug_api.router)  # Debug database utilities
app.include_router(integrations_api.router)  # Integration marketplace (Ship Ship Ship!)
app.include_router(auth_routes.router)
app.include_router(commands_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(partner_portal_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(meeting_intelligence_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(revenue_intelligence_routes.router)
app.include_router(customer_success_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(email_templates_v2_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(cpq_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(sales_enablement_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(lead_scoring_v2_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(abm_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(conversation_intelligence_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(sales_coaching_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(buyer_intent_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(data_quality_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(contact_enrichment_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(competitive_intelligence_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(territories_v2_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(deal_room_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(subscriptions_v2_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(revops_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(gamification_v2_routes.router)
app.include_router(document_generation_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(customer_360_routes.router)
app.include_router(multi_channel_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(workflows_v2_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(activity_capture_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(ai_assistant_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(mobile_sync_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(forecasting_v2_routes.router)
app.include_router(calendar_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(pipeline_analytics_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(deliverability_v2_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(proposals_v2_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(integration_hub_routes.router)
app.include_router(deal_scoring_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(product_analytics_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(revenue_attribution_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(lead_routing_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(account_planning_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(customer_health_v2_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(playbooks_v2_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(team_performance_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(email_analytics_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(sales_metrics_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(content_library_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(email_warmup_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(referral_tracking_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(task_automation_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(partner_management_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(meeting_scheduler_v2_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(roi_calculator_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(proposal_templates_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(sales_objections_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(sales_contests_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(commission_calculator_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(territory_mapping_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(lead_enrichment_v2_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(sales_forecasting_ai_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(deal_insights_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(customer_journey_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(engagement_scoring_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(deal_velocity_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(sales_playbook_ai_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(revops_v2_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(win_loss_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(sales_coaching_ai_routes.router)
    # REMOVED Sprint 22 Task 5 - Unused route
    # app.include_router(quote_management_routes.router)
app.include_router(voice_approval_routes.router)
app.include_router(content_ingest_routes.router)

# Mount static files for dashboard
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/integrations", include_in_schema=False)
async def integrations_page():
    """Serve integrations marketplace UI"""
    integrations_html = os.path.join(static_dir, "integrations.html")
    if os.path.exists(integrations_html):
        return FileResponse(integrations_html)
    return JSONResponse({"error": "Integrations page not found"}, status_code=404)


@app.get("/integrations.html", include_in_schema=False)
async def integrations_page_html():
    """Serve integrations marketplace UI (with .html extension)"""
    integrations_html = os.path.join(static_dir, "integrations.html")
    if os.path.exists(integrations_html):
        return FileResponse(integrations_html)
    return JSONResponse({"error": "Integrations page not found"}, status_code=404)


@app.on_event("startup")
async def startup_event() -> None:
    """Run on application startup."""
    logger.info("Sales Agent starting up", env=settings.api_env)


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Run on application shutdown."""
    logger.info("Sales Agent shutting down")


@app.get("/health", tags=["Health"])
async def health_check() -> JSONResponse:
    """Health check endpoint."""
    return JSONResponse({"status": "ok"})


@app.get("/", tags=["Root"])
async def root() -> FileResponse:
    """Serve operator dashboard."""
    dashboard_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(dashboard_path):
        return FileResponse(dashboard_path)
    return JSONResponse(
        {
            "service": "sales-agent",
            "version": "0.1.0",
            "status": "running",
            "environment": settings.api_env,
            "dashboard": "/static/index.html",
            "docs": "/docs",
        }
    )


@app.get("/dashboard", tags=["Dashboard"])
async def dashboard():
    """Operator dashboard."""
    dashboard_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(dashboard_path):
        return FileResponse(dashboard_path)
    return JSONResponse({"error": "Dashboard not found"}, status_code=404)


@app.get("/voice-profiles", tags=["Dashboard"])
async def voice_profiles_page():
    """Voice profiles management page."""
    page_path = os.path.join(os.path.dirname(__file__), "static", "voice-profiles.html")
    if os.path.exists(page_path):
        return FileResponse(page_path)
    return JSONResponse({"error": "Page not found"}, status_code=404)


@app.get("/agents", tags=["Dashboard"])
async def agents_page():
    """Agents visibility page."""
    page_path = os.path.join(os.path.dirname(__file__), "static", "agents.html")
    if os.path.exists(page_path):
        return FileResponse(page_path)
    return JSONResponse({"error": "Page not found"}, status_code=404)


@app.get("/jarvis", tags=["Dashboard"])
async def jarvis_page():
    """JARVIS voice approval interface."""
    page_path = os.path.join(os.path.dirname(__file__), "static", "jarvis.html")
    if os.path.exists(page_path):
        return FileResponse(page_path)
    return JSONResponse({"error": "Page not found"}, status_code=404)


@app.get("/admin", tags=["Dashboard"])
async def admin_page():
    """Admin panel page."""
    page_path = os.path.join(os.path.dirname(__file__), "static", "admin.html")
    if os.path.exists(page_path):
        return FileResponse(page_path)
    return JSONResponse({"error": "Page not found"}, status_code=404)


@app.get("/api/status", tags=["Health"])
async def system_status() -> JSONResponse:
    """System status endpoint with dashboard stats."""
    # Get actual stats from database
    pending_count = 0
    workflows_today = 0
    try:
        from src.operator_mode import get_draft_queue
        queue = get_draft_queue()
        pending = await queue.get_pending_approvals()
        pending_count = len(pending)
        
        from src.db.workflow_db import get_workflow_db
        db = await get_workflow_db()
        stats = await db.get_workflow_stats()
        workflows_today = stats.get("today", {}).get("total", 0)
    except Exception as e:
        logger.warning(f"Could not fetch dashboard stats: {e}")
    
    return JSONResponse(
        {
            "status": "operational",
            "operator_mode": settings.operator_mode_enabled,
            "approval_required": settings.operator_approval_required,
            "mode": "DRAFT_ONLY" if settings.MODE_DRAFT_ONLY else "SEND_ALLOWED",
            "rate_limits": {
                "max_emails_per_day": settings.max_emails_per_day,
                "max_emails_per_week": settings.max_emails_per_week,
            },
            "pending_drafts": pending_count,
            "approved_today": 0,
            "sent_today": 0,
            "workflows_today": workflows_today,
        }
    )


@app.get("/api/drafts", tags=["Dashboard"])
async def get_drafts() -> JSONResponse:
    """Get pending drafts for dashboard."""
    try:
        from src.operator_mode import get_draft_queue
        queue = get_draft_queue()
        pending = await queue.get_pending_approvals()
        return JSONResponse({"drafts": pending, "total": len(pending)})
    except Exception as e:
        logger.error(f"Error fetching drafts: {e}")
        return JSONResponse({"drafts": [], "total": 0, "error": str(e)})


@app.get("/api/workflows", tags=["Dashboard"])
async def get_workflows() -> JSONResponse:
    """Get recent workflow runs for dashboard."""
    try:
        from src.db.workflow_db import get_workflow_db
        db = await get_workflow_db()
        recent = await db.get_recent_workflows(limit=50)
        # Convert datetime objects to strings
        for w in recent:
            for k, v in w.items():
                if hasattr(v, 'isoformat'):
                    w[k] = v.isoformat()
        return JSONResponse({"workflows": recent, "total": len(recent)})
    except Exception as e:
        logger.error(f"Error fetching workflows: {e}")
        return JSONResponse({"workflows": [], "total": 0, "error": str(e)})


if __name__ == "__main__":
    import uvicorn

    # Mount static files for dashboard
    app.mount("/static", StaticFiles(directory="src/static"), name="static")
    
    # Dashboard routes
    app.include_router(admin_flags.router)
    app.include_router(dashboard_api.router)
    
    @app.get("/dashboard")
    async def dashboard():
        """Serve operator dashboard."""
        return FileResponse("src/static/operator-dashboard.html")

    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
    )
