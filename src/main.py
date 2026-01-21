"""FastAPI application entry point."""
import logging
import os

from fastapi import FastAPI
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from src.config import get_settings
from src.logger import configure_logging, get_logger
from src.middleware import TraceIDMiddleware
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
from src.routes import quotes_routes
from src.routes import products_routes
from src.routes import forecasts_routes
from src.routes import territories_routes
from src.routes import competitors_routes
from src.routes import commissions_routes
from src.routes import contracts_routes
from src.routes import approvals_routes
from src.routes import subscriptions_routes
from src.routes import playbooks_routes
from src.routes import learning_routes
from src.routes import integrations_routes
from src.routes import invoices_routes
from src.routes import documents_routes
from src.routes import events_routes
from src.routes import calls_routes
from src.routes import email_tracking_routes
from src.routes import roles_routes
from src.routes import teams_routes
from src.routes import custom_fields_routes
from src.routes import tags_routes
from src.routes import automation_routes
from src.routes import notification_prefs_routes
from src.routes import data_sync_routes
from src.routes import gamification_routes
from src.routes import search_routes
from src.routes import recommendations_routes
from src.routes import webhook_subscriptions_routes
from src.routes import activity_feed_routes
from src.routes import quota_routes
from src.routes import social_selling_routes

# Configure logging
settings = get_settings()
configure_logging(log_level=settings.log_level, log_format=settings.log_format)

logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Sales Agent",
    description="Operator-mode prospecting and nurturing agent",
    version="0.1.0",
)

# Add middleware
app.add_middleware(TraceIDMiddleware)

# Include routers
app.include_router(agents_routes.router)
app.include_router(operator_routes.router)
app.include_router(webhooks_routes.router)
app.include_router(voice_routes.router)
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
app.include_router(quotes_routes.router)
app.include_router(products_routes.router)
app.include_router(forecasts_routes.router)
app.include_router(territories_routes.router)
app.include_router(competitors_routes.router)
app.include_router(commissions_routes.router)
app.include_router(contracts_routes.router)
app.include_router(approvals_routes.router)
app.include_router(subscriptions_routes.router)
app.include_router(playbooks_routes.router)
app.include_router(learning_routes.router)
app.include_router(integrations_routes.router)
app.include_router(invoices_routes.router)
app.include_router(documents_routes.router)
app.include_router(events_routes.router)
app.include_router(calls_routes.router)
app.include_router(email_tracking_routes.router)
app.include_router(roles_routes.router)
app.include_router(teams_routes.router)
app.include_router(custom_fields_routes.router)
app.include_router(tags_routes.router)
app.include_router(automation_routes.router)
app.include_router(notification_prefs_routes.router)
app.include_router(data_sync_routes.router)
app.include_router(gamification_routes.router)
app.include_router(search_routes.router)
app.include_router(recommendations_routes.router)
app.include_router(webhook_subscriptions_routes.router)
app.include_router(activity_feed_routes.router)
app.include_router(quota_routes.router)
app.include_router(social_selling_routes.router)

# Mount static files for dashboard
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


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
            "mode": "DRAFT_ONLY" if settings.mode_draft_only else "SEND_ALLOWED",
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

    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
    )
