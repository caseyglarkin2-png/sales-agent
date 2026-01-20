"""Pydantic settings configuration loader."""
import os
from typing import Literal

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Configuration
    api_host: str = Field(default="0.0.0.0", description="API host to bind to")
    api_port: int = Field(default=8000, description="API port")
    api_env: Literal["development", "staging", "production"] = Field(
        default="development", description="Environment name"
    )
    api_log_level: str = Field(default="INFO", description="Log level")

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/sales_agent",
        description="Database connection URL",
    )
    database_pool_size: int = Field(default=20, description="Database pool size")
    database_max_overflow: int = Field(default=10, description="Database max overflow")

    @property
    def async_database_url(self) -> str:
        """Get async database URL (postgresql+asyncpg://)."""
        url = self.database_url
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0", description="Redis connection URL"
    )

    # Celery
    celery_broker_url: str = Field(
        default="redis://localhost:6379/1", description="Celery broker URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/2", description="Celery result backend URL"
    )

    # Google OAuth
    google_client_id: str = Field(default="", description="Google OAuth Client ID")
    google_client_secret: str = Field(default="", description="Google OAuth Client Secret")
    google_redirect_uri: str = Field(
        default="http://localhost:8000/auth/google/callback",
        description="Google OAuth Redirect URI",
    )

    # HubSpot
    hubspot_api_key: str = Field(default="", description="HubSpot API Key")
    hubspot_app_id: str = Field(default="", description="HubSpot App ID")

    # OpenAI
    openai_api_key: str = Field(default="", description="OpenAI API Key")
    openai_model: str = Field(default="gpt-4-turbo-preview", description="OpenAI Model")

    # Feature Flags
    feature_cold_start_demo: bool = Field(default=True, description="Enable cold-start demo")
    feature_validation_agent: bool = Field(default=False, description="Enable validation agent")
    feature_outcome_reporter: bool = Field(default=False, description="Enable outcome reporter")

    # Operator Mode
    operator_mode_enabled: bool = Field(default=True, description="Enable operator mode")
    operator_approval_required: bool = Field(
        default=True, description="Require operator approval for sends"
    )
    max_emails_per_day: int = Field(default=20, description="Max emails per day")
    max_emails_per_week: int = Field(default=2, description="Max emails per week")

    # DRAFT_ONLY Mode (Safety First)
    mode_draft_only: bool = Field(default=True, description="Enable DRAFT_ONLY mode (emails saved as drafts, not sent)")
    allow_auto_send: bool = Field(default=False, description="Allow auto-send (overrides DRAFT_ONLY if True)")
    require_approval: bool = Field(default=True, description="Require operator approval for any send")
    approval_timeout_hours: int = Field(default=24, description="Hours to keep draft for approval")

    # Logging
    log_format: str = Field(default="json", description="Log format (json or text)")
    log_level: str = Field(default="INFO", description="Log level")
    audit_trail_enabled: bool = Field(default=True, description="Enable audit trail logging")
    audit_trail_retention_days: int = Field(default=90, description="Days to retain audit logs")

    # Security
    secret_key: str = Field(default="dev-secret-key-change-in-production", description="Secret key for sessions")
    allowed_origins: list = Field(default=["http://localhost:3000"], description="CORS allowed origins")
    
    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_requests: int = Field(default=100, description="Requests per period")
    rate_limit_period_seconds: int = Field(default=60, description="Rate limit period in seconds")

    class Config:
        env_file = ".env"
        case_sensitive = False

    def validate_required_fields(self) -> None:
        """Validate that required fields are set."""
        if self.api_env == "production":
            required = [
                "google_client_id",
                "google_client_secret",
                "hubspot_api_key",
                "openai_api_key",
            ]
            missing = [f for f in required if not getattr(self, f, None)]
            if missing:
                raise ValidationError(f"Missing required fields for production: {missing}")
            
            # Production safety checks
            if self.secret_key == "dev-secret-key-change-in-production":
                raise ValidationError("SECRET_KEY must be changed from default in production")
            if self.mode_draft_only and not self.allow_auto_send:
                # This is safe - DRAFT_ONLY enforced
                pass
            elif not self.mode_draft_only and self.allow_auto_send and not self.require_approval:
                # Dangerous - auto-send without approval in production
                raise ValidationError(
                    "Production safety: Cannot enable AUTO_SEND without DRAFT_ONLY and REQUIRE_APPROVAL"
                )

    def is_draft_only_enforced(self) -> bool:
        """Check if DRAFT_ONLY mode is enforced (no auto-send possible)."""
        return self.mode_draft_only and not self.allow_auto_send

    def is_auto_send_allowed(self) -> bool:
        """Check if auto-send is allowed and safe."""
        return (
            self.allow_auto_send
            and not self.mode_draft_only
            and self.require_approval
        )


def get_settings() -> Settings:
    """Get application settings, validating on import."""
    settings = Settings()
    try:
        settings.validate_required_fields()
    except ValidationError as e:
        raise RuntimeError(f"Configuration error: {e}") from e
    return settings
