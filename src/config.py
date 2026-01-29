"""Pydantic settings configuration loader."""
import os
from typing import Literal

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Configuration
    api_host: str = Field(default="0.0.0.0", alias="API_HOST", description="API host to bind to")
    api_port: int = Field(default=8000, alias="API_PORT", description="API port")
    api_env: Literal["development", "staging", "production"] = Field(
        default="development", alias="API_ENV", description="Environment name"
    )
    api_log_level: str = Field(default="INFO", alias="API_LOG_LEVEL", description="Log level")

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/sales_agent",
        alias="DATABASE_URL",
        description="Database connection URL",
    )
    database_pool_size: int = Field(default=20, alias="DATABASE_POOL_SIZE", description="Database pool size")
    database_max_overflow: int = Field(default=10, alias="DATABASE_MAX_OVERFLOW", description="Database max overflow")

    @property
    def async_database_url(self) -> str:
        """Get async database URL (postgresql+asyncpg://)."""
        url = self.database_url
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0", alias="REDIS_URL", description="Redis connection URL"
    )

    # Celery
    celery_broker_url: str = Field(
        default="redis://localhost:6379/1", alias="CELERY_BROKER_URL", description="Celery broker URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/2", alias="CELERY_RESULT_BACKEND", description="Celery result backend URL"
    )

    # Text-to-Speech (TTS) Configuration
    tts_enabled: bool = Field(default=True, alias="TTS_ENABLED", description="Enable text-to-speech features")
    tts_voice_name: str = Field(
        default="Google UK English Female", alias="TTS_VOICE_NAME", description="Preferred TTS voice name"
    )
    tts_rate: float = Field(
        default=1.0, 
        ge=0.5, 
        le=2.0, 
        alias="TTS_RATE", 
        description="TTS speech rate (0.5-2.0, 1.0 = normal)"
    )
    tts_pitch: float = Field(
        default=1.0, 
        ge=0.0, 
        le=2.0, 
        alias="TTS_PITCH", 
        description="TTS speech pitch (0.0-2.0, 1.0 = normal)"
    )
    tts_volume: float = Field(
        default=1.0, 
        ge=0.0, 
        le=1.0, 
        alias="TTS_VOLUME", 
        description="TTS speech volume (0.0-1.0, 1.0 = max)"
    )

    # Google OAuth
    google_client_id: str = Field(default="", alias="GOOGLE_CLIENT_ID", description="Google OAuth Client ID")
    google_client_secret: str = Field(default="", alias="GOOGLE_CLIENT_SECRET", description="Google OAuth Client Secret")
    google_redirect_uri: str = Field(
        default="http://localhost:8000/auth/callback",
        alias="GOOGLE_REDIRECT_URI",
        description="Google OAuth Redirect URI - must match /auth/callback route in web_auth.py",
    )

    # HubSpot
    hubspot_api_key: str = Field(default="", alias="HUBSPOT_API_KEY", description="HubSpot API Key")
    hubspot_app_id: str = Field(default="", alias="HUBSPOT_APP_ID", description="HubSpot App ID")
    hubspot_webhook_secret: str = Field(default="", alias="HUBSPOT_WEBHOOK_SECRET", description="HubSpot Webhook Secret for signature validation")

    # OpenAI
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY", description="OpenAI API Key")
    openai_model: str = Field(default="gpt-4-turbo-preview", alias="OPENAI_MODEL", description="OpenAI Model")

    # Google Gemini AI
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY", description="Google Gemini API Key")
    gemini_model: str = Field(default="gemini-2.0-flash-exp", alias="GEMINI_MODEL", description="Default Gemini Model")
    llm_provider: str = Field(default="openai", alias="LLM_PROVIDER", description="LLM provider: openai or gemini")

    # xAI Grok (for real-time market intelligence)
    xai_api_key: str = Field(default="", alias="XAI_API_KEY", description="xAI Grok API Key from console.x.ai")

    # Twitter/X API (for social monitoring)
    twitter_bearer_token: str = Field(default="", alias="TWITTER_BEARER_TOKEN", description="Twitter/X API Bearer Token for social monitoring")
    twitter_consumer_key: str = Field(default="", alias="TWITTER_CONSUMER_KEY", description="Twitter/X Consumer Key (API Key) for OAuth 1.0a")
    twitter_consumer_secret: str = Field(default="", alias="TWITTER_CONSUMER_SECRET", description="Twitter/X Consumer Secret (API Secret) for OAuth 1.0a")

    # Slack (The Comms Trove)
    slack_bot_token: str = Field(default="", alias="SLACK_BOT_TOKEN", description="Slack Bot Token (xoxb-...)")
    slack_signing_secret: str = Field(default="", alias="SLACK_SIGNING_SECRET", description="Slack Signing Secret")

    # SendGrid (Sprint 64 - High Volume Email)
    sendgrid_api_key: str = Field(default="", alias="SENDGRID_API_KEY", description="SendGrid API Key")
    sendgrid_sender_email: str = Field(default="", alias="SENDGRID_SENDER_EMAIL", description="SendGrid verified sender email")
    sendgrid_sender_name: str = Field(default="CaseyOS", alias="SENDGRID_SENDER_NAME", description="SendGrid sender display name")
    email_provider: str = Field(default="gmail", alias="EMAIL_PROVIDER", description="Email provider: gmail, sendgrid, or auto")

    # Feature Flags
    feature_cold_start_demo: bool = Field(default=True, alias="FEATURE_COLD_START_DEMO", description="Enable cold-start demo")
    feature_validation_agent: bool = Field(default=False, alias="FEATURE_VALIDATION_AGENT", description="Enable validation agent")
    feature_outcome_reporter: bool = Field(default=False, alias="FEATURE_OUTCOME_REPORTER", description="Enable outcome reporter")

    # Operator Mode
    operator_mode_enabled: bool = Field(default=True, alias="OPERATOR_MODE_ENABLED", description="Enable operator mode")
    operator_approval_required: bool = Field(
        default=True, alias="OPERATOR_APPROVAL_REQUIRED", description="Require operator approval for sends"
    )
    max_emails_per_day: int = Field(default=20, alias="MAX_EMAILS_PER_DAY", description="Max emails per day")
    max_emails_per_week: int = Field(default=2, alias="MAX_EMAILS_PER_WEEK", description="Max emails per week")

    # DRAFT_ONLY Mode (Safety First)
    MODE_DRAFT_ONLY: bool = Field(default=True, alias="MODE_DRAFT_ONLY", description="Enable DRAFT_ONLY mode (emails saved as drafts, not sent)")
    ALLOW_AUTO_SEND: bool = Field(default=False, alias="ALLOW_AUTO_SEND", description="Allow auto-send (overrides DRAFT_ONLY if True)")
    REQUIRE_APPROVAL: bool = Field(default=True, alias="REQUIRE_APPROVAL", description="Require operator approval for any send")
    ALLOW_REAL_SENDS: bool = Field(default=False, alias="ALLOW_REAL_SENDS", description="Feature flag to allow real email sends (overrides draft-only)")
    approval_timeout_hours: int = Field(default=24, alias="APPROVAL_TIMEOUT_HOURS", description="Hours to keep draft for approval")
    
    # Auto-Approval (Sprint 4)
    auto_approve_enabled: bool = Field(default=True, alias="AUTO_APPROVE_ENABLED", description="Enable auto-approval rules engine")
    
    # Security (Sprint 6)
    admin_password: str = Field(default="", alias="ADMIN_PASSWORD", description="Admin password for sensitive operations")
    
    # Sentry (Sprint 6 - Task 6.4)
    sentry_dsn: str = Field(default="", alias="SENTRY_DSN", description="Sentry DSN for error tracking")
    sentry_environment: str = Field(default="development", alias="SENTRY_ENVIRONMENT", description="Sentry environment")
    sentry_traces_sample_rate: float = Field(default=0.1, alias="SENTRY_TRACES_SAMPLE_RATE", description="Sentry tracing rate")
    
    # Expose uppercase versions for feature flag manager
    @property
    def API_ENV(self) -> str:
        return self.api_env

    # Logging
    log_format: str = Field(default="json", alias="LOG_FORMAT", description="Log format (json or text)")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL", description="Log level")
    audit_trail_enabled: bool = Field(default=True, alias="AUDIT_TRAIL_ENABLED", description="Enable audit trail logging")
    audit_trail_retention_days: int = Field(default=90, alias="AUDIT_TRAIL_RETENTION_DAYS", description="Days to retain audit logs")

    # Security
    secret_key: str = Field(default="dev-secret-key-change-in-production", alias="SECRET_KEY", description="Secret key for sessions")
    allowed_origins: list = Field(default=["http://localhost:3000"], alias="ALLOWED_ORIGINS", description="CORS allowed origins")
    
    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED", description="Enable rate limiting")
    rate_limit_requests: int = Field(default=100, alias="RATE_LIMIT_REQUESTS", description="Requests per period")
    rate_limit_period_seconds: int = Field(default=60, alias="RATE_LIMIT_PERIOD_SECONDS", description="Rate limit period in seconds")

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Allow extra environment variables
        populate_by_name = True  # Allow both alias and field name

    def validate_required_fields(self) -> None:
        """Validate that required fields are set (Sprint 70: Enhanced)."""
        import warnings
        
        if self.api_env == "production":
            # Critical required fields - app won't start without these
            required = [
                "database_url",
                "secret_key",
                "google_client_id",
                "google_client_secret",
            ]
            missing = [f for f in required if not getattr(self, f, None)]
            if missing:
                raise ValueError(f"Missing required fields for production: {missing}")
            
            # Check for placeholder DATABASE_URL
            if "localhost" in self.database_url or "127.0.0.1" in self.database_url:
                raise ValueError(
                    "Production DATABASE_URL cannot point to localhost. "
                    "Set DATABASE_URL to your production PostgreSQL instance."
                )
            
            # Production safety checks
            if self.secret_key == "dev-secret-key-change-in-production":
                raise ValueError("SECRET_KEY must be changed from default in production")
            if self.MODE_DRAFT_ONLY and not self.ALLOW_AUTO_SEND:
                # This is safe - DRAFT_ONLY enforced
                pass
            elif not self.MODE_DRAFT_ONLY and self.ALLOW_AUTO_SEND and not self.REQUIRE_APPROVAL:
                # Dangerous - auto-send without approval in production
                raise ValueError(
                    "Production safety: Cannot enable AUTO_SEND without DRAFT_ONLY and REQUIRE_APPROVAL"
                )
            
            # Warn on missing optional but recommended fields
            optional_recommended = {
                "openai_api_key": "AI draft generation won't work",
                "hubspot_api_key": "CRM integration won't work",
                "sendgrid_api_key": "Email sending fallback won't work",
                "slack_bot_token": "Slack notifications won't work",
            }
            for field, impact in optional_recommended.items():
                if not getattr(self, field, None):
                    warnings.warn(
                        f"Production warning: {field.upper()} not set. Impact: {impact}",
                        UserWarning
                    )

    def is_draft_only_enforced(self) -> bool:
        """Check if DRAFT_ONLY mode is enforced (no auto-send possible)."""
        return self.MODE_DRAFT_ONLY and not self.ALLOW_AUTO_SEND

    def is_auto_send_allowed(self) -> bool:
        """Check if auto-send is allowed and safe."""
        return (
            self.ALLOW_AUTO_SEND
            and not self.MODE_DRAFT_ONLY
            and self.REQUIRE_APPROVAL
        )


def get_settings() -> Settings:
    """Get application settings, validating on import."""
    settings = Settings()
    try:
        settings.validate_required_fields()
    except ValueError as e:
        raise RuntimeError(f"Configuration error: {e}") from e
    return settings
