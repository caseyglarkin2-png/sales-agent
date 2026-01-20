"""FastAPI application entry point."""
import logging

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from src.config import get_settings
from src.logger import configure_logging, get_logger
from src.middleware import TraceIDMiddleware
from src.routes import agents as agents_routes
from src.routes import operator as operator_routes
from src.routes import webhooks as webhooks_routes

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
async def root() -> JSONResponse:
    """Root endpoint."""
    return JSONResponse(
        {
            "service": "sales-agent",
            "version": "0.1.0",
            "status": "running",
            "environment": settings.api_env,
            "operator_mode_enabled": settings.operator_mode_enabled,
            "features": {
                "cold_start_demo": settings.feature_cold_start_demo,
                "validation_agent": settings.feature_validation_agent,
                "outcome_reporter": settings.feature_outcome_reporter,
            },
        }
    )


@app.get("/api/status", tags=["Health"])
async def system_status() -> JSONResponse:
    """System status endpoint."""
    return JSONResponse(
        {
            "status": "operational",
            "operator_mode": settings.operator_mode_enabled,
            "approval_required": settings.operator_approval_required,
            "rate_limits": {
                "max_emails_per_day": settings.max_emails_per_day,
                "max_emails_per_week": settings.max_emails_per_week,
            },
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
    )
