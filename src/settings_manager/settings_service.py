"""
Settings Service - Application Configuration
=============================================
Manage application settings and user preferences.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class SettingCategory(str, Enum):
    """Categories for settings."""
    GENERAL = "general"
    EMAIL = "email"
    NOTIFICATIONS = "notifications"
    INTEGRATIONS = "integrations"
    SECURITY = "security"
    AI = "ai"
    TRACKING = "tracking"
    BRANDING = "branding"
    BILLING = "billing"


class SettingType(str, Enum):
    """Data types for settings."""
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    JSON = "json"
    SECRET = "secret"
    LIST = "list"


@dataclass
class SettingDefinition:
    """Definition of a setting."""
    key: str
    category: SettingCategory
    type: SettingType
    default_value: Any
    label: str
    description: str
    is_required: bool = False
    is_sensitive: bool = False
    validation_pattern: Optional[str] = None
    options: Optional[list[str]] = None  # For select fields
    min_value: Optional[float] = None
    max_value: Optional[float] = None


@dataclass
class Setting:
    """A setting value."""
    key: str
    value: Any
    category: SettingCategory
    type: SettingType
    is_default: bool = True
    updated_at: datetime = field(default_factory=datetime.utcnow)
    updated_by: Optional[str] = None


class SettingsService:
    """Service for managing application settings."""
    
    def __init__(self):
        self.definitions: dict[str, SettingDefinition] = {}
        self.values: dict[str, Setting] = {}
        self.org_values: dict[str, dict[str, Setting]] = {}  # org_id -> settings
        self.user_values: dict[str, dict[str, Setting]] = {}  # user_id -> settings
        self._register_default_settings()
    
    def _register_default_settings(self):
        """Register all default settings."""
        defaults = [
            # General settings
            SettingDefinition(
                key="company_name",
                category=SettingCategory.GENERAL,
                type=SettingType.STRING,
                default_value="My Company",
                label="Company Name",
                description="Your company name displayed in emails and documents"
            ),
            SettingDefinition(
                key="timezone",
                category=SettingCategory.GENERAL,
                type=SettingType.STRING,
                default_value="UTC",
                label="Default Timezone",
                description="Default timezone for scheduling and reports",
                options=["UTC", "America/New_York", "America/Los_Angeles", "Europe/London", "Asia/Tokyo"]
            ),
            SettingDefinition(
                key="date_format",
                category=SettingCategory.GENERAL,
                type=SettingType.STRING,
                default_value="YYYY-MM-DD",
                label="Date Format",
                description="Date format for display",
                options=["YYYY-MM-DD", "MM/DD/YYYY", "DD/MM/YYYY"]
            ),
            SettingDefinition(
                key="currency",
                category=SettingCategory.GENERAL,
                type=SettingType.STRING,
                default_value="USD",
                label="Default Currency",
                description="Default currency for deals and reports",
                options=["USD", "EUR", "GBP", "CAD", "AUD"]
            ),
            
            # Email settings
            SettingDefinition(
                key="email_from_name",
                category=SettingCategory.EMAIL,
                type=SettingType.STRING,
                default_value="Sales Team",
                label="From Name",
                description="Name shown in outgoing emails"
            ),
            SettingDefinition(
                key="email_from_address",
                category=SettingCategory.EMAIL,
                type=SettingType.STRING,
                default_value="sales@example.com",
                label="From Email",
                description="Email address for outgoing emails",
                is_required=True
            ),
            SettingDefinition(
                key="email_reply_to",
                category=SettingCategory.EMAIL,
                type=SettingType.STRING,
                default_value="",
                label="Reply-To Address",
                description="Reply-to email address (optional)"
            ),
            SettingDefinition(
                key="email_signature",
                category=SettingCategory.EMAIL,
                type=SettingType.STRING,
                default_value="Best regards,\nThe Sales Team",
                label="Email Signature",
                description="Default signature for emails"
            ),
            SettingDefinition(
                key="email_daily_limit",
                category=SettingCategory.EMAIL,
                type=SettingType.NUMBER,
                default_value=200,
                label="Daily Email Limit",
                description="Maximum emails per user per day",
                min_value=1,
                max_value=1000
            ),
            SettingDefinition(
                key="email_tracking_enabled",
                category=SettingCategory.EMAIL,
                type=SettingType.BOOLEAN,
                default_value=True,
                label="Email Tracking",
                description="Enable open and click tracking"
            ),
            
            # Notification settings
            SettingDefinition(
                key="notify_email_opens",
                category=SettingCategory.NOTIFICATIONS,
                type=SettingType.BOOLEAN,
                default_value=True,
                label="Email Open Notifications",
                description="Notify when emails are opened"
            ),
            SettingDefinition(
                key="notify_email_replies",
                category=SettingCategory.NOTIFICATIONS,
                type=SettingType.BOOLEAN,
                default_value=True,
                label="Email Reply Notifications",
                description="Notify when replies are received"
            ),
            SettingDefinition(
                key="notify_deal_won",
                category=SettingCategory.NOTIFICATIONS,
                type=SettingType.BOOLEAN,
                default_value=True,
                label="Deal Won Notifications",
                description="Notify when deals are won"
            ),
            SettingDefinition(
                key="notify_task_due",
                category=SettingCategory.NOTIFICATIONS,
                type=SettingType.BOOLEAN,
                default_value=True,
                label="Task Due Notifications",
                description="Notify when tasks are due"
            ),
            SettingDefinition(
                key="notification_channels",
                category=SettingCategory.NOTIFICATIONS,
                type=SettingType.LIST,
                default_value=["email", "in_app"],
                label="Notification Channels",
                description="Channels for notifications",
                options=["email", "in_app", "browser", "slack", "sms"]
            ),
            
            # Integration settings
            SettingDefinition(
                key="hubspot_enabled",
                category=SettingCategory.INTEGRATIONS,
                type=SettingType.BOOLEAN,
                default_value=False,
                label="HubSpot Integration",
                description="Enable HubSpot CRM sync"
            ),
            SettingDefinition(
                key="hubspot_api_key",
                category=SettingCategory.INTEGRATIONS,
                type=SettingType.SECRET,
                default_value="",
                label="HubSpot API Key",
                description="HubSpot private app access token",
                is_sensitive=True
            ),
            SettingDefinition(
                key="hubspot_sync_interval",
                category=SettingCategory.INTEGRATIONS,
                type=SettingType.NUMBER,
                default_value=15,
                label="Sync Interval (minutes)",
                description="How often to sync with HubSpot",
                min_value=5,
                max_value=1440
            ),
            SettingDefinition(
                key="gmail_enabled",
                category=SettingCategory.INTEGRATIONS,
                type=SettingType.BOOLEAN,
                default_value=False,
                label="Gmail Integration",
                description="Enable Gmail for sending emails"
            ),
            SettingDefinition(
                key="calendar_enabled",
                category=SettingCategory.INTEGRATIONS,
                type=SettingType.BOOLEAN,
                default_value=False,
                label="Calendar Integration",
                description="Enable Google Calendar integration"
            ),
            
            # Security settings
            SettingDefinition(
                key="session_timeout",
                category=SettingCategory.SECURITY,
                type=SettingType.NUMBER,
                default_value=30,
                label="Session Timeout (days)",
                description="Days until session expires",
                min_value=1,
                max_value=90
            ),
            SettingDefinition(
                key="require_2fa",
                category=SettingCategory.SECURITY,
                type=SettingType.BOOLEAN,
                default_value=False,
                label="Require 2FA",
                description="Require two-factor authentication"
            ),
            SettingDefinition(
                key="ip_whitelist",
                category=SettingCategory.SECURITY,
                type=SettingType.LIST,
                default_value=[],
                label="IP Whitelist",
                description="Allowed IP addresses (empty = all)"
            ),
            SettingDefinition(
                key="password_min_length",
                category=SettingCategory.SECURITY,
                type=SettingType.NUMBER,
                default_value=8,
                label="Minimum Password Length",
                description="Minimum characters for passwords",
                min_value=6,
                max_value=32
            ),
            
            # AI settings
            SettingDefinition(
                key="ai_enabled",
                category=SettingCategory.AI,
                type=SettingType.BOOLEAN,
                default_value=True,
                label="AI Features",
                description="Enable AI-powered features"
            ),
            SettingDefinition(
                key="ai_model",
                category=SettingCategory.AI,
                type=SettingType.STRING,
                default_value="gpt-4",
                label="AI Model",
                description="AI model for text generation",
                options=["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo", "claude-3-opus", "claude-3-sonnet"]
            ),
            SettingDefinition(
                key="ai_email_suggestions",
                category=SettingCategory.AI,
                type=SettingType.BOOLEAN,
                default_value=True,
                label="Email Suggestions",
                description="AI suggestions for email content"
            ),
            SettingDefinition(
                key="ai_lead_scoring",
                category=SettingCategory.AI,
                type=SettingType.BOOLEAN,
                default_value=True,
                label="AI Lead Scoring",
                description="Use AI for lead scoring"
            ),
            
            # Tracking settings
            SettingDefinition(
                key="track_email_opens",
                category=SettingCategory.TRACKING,
                type=SettingType.BOOLEAN,
                default_value=True,
                label="Track Email Opens",
                description="Track when emails are opened"
            ),
            SettingDefinition(
                key="track_link_clicks",
                category=SettingCategory.TRACKING,
                type=SettingType.BOOLEAN,
                default_value=True,
                label="Track Link Clicks",
                description="Track when links are clicked"
            ),
            SettingDefinition(
                key="tracking_domain",
                category=SettingCategory.TRACKING,
                type=SettingType.STRING,
                default_value="",
                label="Custom Tracking Domain",
                description="Custom domain for tracking links"
            ),
            
            # Branding settings
            SettingDefinition(
                key="logo_url",
                category=SettingCategory.BRANDING,
                type=SettingType.STRING,
                default_value="",
                label="Logo URL",
                description="URL to company logo"
            ),
            SettingDefinition(
                key="primary_color",
                category=SettingCategory.BRANDING,
                type=SettingType.STRING,
                default_value="#3B82F6",
                label="Primary Color",
                description="Primary brand color (hex)"
            ),
            SettingDefinition(
                key="secondary_color",
                category=SettingCategory.BRANDING,
                type=SettingType.STRING,
                default_value="#1E40AF",
                label="Secondary Color",
                description="Secondary brand color (hex)"
            )
        ]
        
        for definition in defaults:
            self.definitions[definition.key] = definition
            # Initialize with default value
            self.values[definition.key] = Setting(
                key=definition.key,
                value=definition.default_value,
                category=definition.category,
                type=definition.type,
                is_default=True
            )
    
    async def get(
        self,
        key: str,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None
    ) -> Any:
        """Get a setting value."""
        # Check user-specific settings first
        if user_id and user_id in self.user_values:
            if key in self.user_values[user_id]:
                return self.user_values[user_id][key].value
        
        # Check org-specific settings
        if org_id and org_id in self.org_values:
            if key in self.org_values[org_id]:
                return self.org_values[org_id][key].value
        
        # Fall back to global settings
        if key in self.values:
            return self.values[key].value
        
        return None
    
    async def set(
        self,
        key: str,
        value: Any,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
        updated_by: Optional[str] = None
    ) -> bool:
        """Set a setting value."""
        if key not in self.definitions:
            logger.warning(f"Unknown setting key: {key}")
            return False
        
        definition = self.definitions[key]
        
        # Validate value
        if not self._validate_value(value, definition):
            logger.warning(f"Invalid value for setting {key}")
            return False
        
        setting = Setting(
            key=key,
            value=value,
            category=definition.category,
            type=definition.type,
            is_default=False,
            updated_at=datetime.utcnow(),
            updated_by=updated_by
        )
        
        # Store in appropriate location
        if user_id:
            if user_id not in self.user_values:
                self.user_values[user_id] = {}
            self.user_values[user_id][key] = setting
        elif org_id:
            if org_id not in self.org_values:
                self.org_values[org_id] = {}
            self.org_values[org_id][key] = setting
        else:
            self.values[key] = setting
        
        logger.info(f"Updated setting: {key}")
        
        return True
    
    def _validate_value(self, value: Any, definition: SettingDefinition) -> bool:
        """Validate a setting value against its definition."""
        if definition.type == SettingType.STRING:
            if not isinstance(value, str):
                return False
            if definition.options and value not in definition.options:
                return False
        
        elif definition.type == SettingType.NUMBER:
            if not isinstance(value, (int, float)):
                return False
            if definition.min_value is not None and value < definition.min_value:
                return False
            if definition.max_value is not None and value > definition.max_value:
                return False
        
        elif definition.type == SettingType.BOOLEAN:
            if not isinstance(value, bool):
                return False
        
        elif definition.type == SettingType.LIST:
            if not isinstance(value, list):
                return False
        
        return True
    
    async def get_all(
        self,
        category: Optional[SettingCategory] = None,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None
    ) -> dict[str, Any]:
        """Get all settings, optionally filtered by category."""
        result = {}
        
        for key, definition in self.definitions.items():
            if category and definition.category != category:
                continue
            
            value = await self.get(key, user_id=user_id, org_id=org_id)
            
            # Mask sensitive values
            if definition.is_sensitive and value:
                value = "********"
            
            result[key] = {
                "value": value,
                "category": definition.category.value,
                "type": definition.type.value,
                "label": definition.label,
                "description": definition.description,
                "is_default": self.values[key].is_default if key in self.values else True
            }
        
        return result
    
    async def get_by_category(
        self,
        category: SettingCategory,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None
    ) -> dict[str, Any]:
        """Get all settings in a category."""
        return await self.get_all(category=category, user_id=user_id, org_id=org_id)
    
    async def reset_to_default(
        self,
        key: str,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None
    ) -> bool:
        """Reset a setting to its default value."""
        if key not in self.definitions:
            return False
        
        if user_id and user_id in self.user_values:
            if key in self.user_values[user_id]:
                del self.user_values[user_id][key]
                return True
        
        if org_id and org_id in self.org_values:
            if key in self.org_values[org_id]:
                del self.org_values[org_id][key]
                return True
        
        if key in self.values:
            definition = self.definitions[key]
            self.values[key] = Setting(
                key=key,
                value=definition.default_value,
                category=definition.category,
                type=definition.type,
                is_default=True
            )
            return True
        
        return False
    
    async def bulk_update(
        self,
        settings: dict[str, Any],
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
        updated_by: Optional[str] = None
    ) -> dict[str, bool]:
        """Update multiple settings at once."""
        results = {}
        
        for key, value in settings.items():
            success = await self.set(
                key=key,
                value=value,
                user_id=user_id,
                org_id=org_id,
                updated_by=updated_by
            )
            results[key] = success
        
        return results
    
    async def get_categories(self) -> list[dict]:
        """Get all setting categories with counts."""
        categories = []
        
        for category in SettingCategory:
            count = len([
                d for d in self.definitions.values()
                if d.category == category
            ])
            
            categories.append({
                "value": category.value,
                "name": category.name,
                "count": count
            })
        
        return categories
    
    async def get_definition(self, key: str) -> Optional[dict]:
        """Get the definition for a setting."""
        definition = self.definitions.get(key)
        if not definition:
            return None
        
        return {
            "key": definition.key,
            "category": definition.category.value,
            "type": definition.type.value,
            "default_value": definition.default_value,
            "label": definition.label,
            "description": definition.description,
            "is_required": definition.is_required,
            "is_sensitive": definition.is_sensitive,
            "options": definition.options,
            "min_value": definition.min_value,
            "max_value": definition.max_value
        }
    
    async def export_settings(
        self,
        org_id: Optional[str] = None
    ) -> dict:
        """Export all settings for backup."""
        all_settings = await self.get_all(org_id=org_id)
        
        return {
            "exported_at": datetime.utcnow().isoformat(),
            "settings": {
                key: data["value"]
                for key, data in all_settings.items()
                if not self.definitions.get(key, SettingDefinition(
                    key="", category=SettingCategory.GENERAL,
                    type=SettingType.STRING, default_value="",
                    label="", description=""
                )).is_sensitive
            }
        }
    
    async def import_settings(
        self,
        settings: dict[str, Any],
        org_id: Optional[str] = None,
        updated_by: Optional[str] = None
    ) -> dict[str, bool]:
        """Import settings from backup."""
        return await self.bulk_update(
            settings=settings,
            org_id=org_id,
            updated_by=updated_by
        )


# Global service instance
_settings_service: Optional[SettingsService] = None


def get_settings_service() -> SettingsService:
    """Get or create the settings service singleton."""
    global _settings_service
    if _settings_service is None:
        _settings_service = SettingsService()
    return _settings_service
