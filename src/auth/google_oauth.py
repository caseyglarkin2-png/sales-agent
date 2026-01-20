"""Google OAuth 2.0 manager for Gmail, Drive, and Calendar.

This module handles the OAuth 2.0 flow for Google APIs, including:
- Authorization code flow for local development & Codespaces
- Token storage and refresh
- Scope management (Gmail, Drive, Calendar)
- Multi-scope token aggregation
"""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
from google.auth.oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials as GoogleCredentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials

from src.logger import get_logger

logger = get_logger(__name__)

# Scopes for each service
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

DRIVE_SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
]

CALENDAR_SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
]

ALL_SCOPES = GMAIL_SCOPES + DRIVE_SCOPES + CALENDAR_SCOPES


class GoogleOAuthManager:
    """Manage Google OAuth tokens for multiple services."""

    def __init__(self, credentials_file: str = "client_secret.json", token_cache_dir: str = ".tokens"):
        """Initialize OAuth manager.

        Args:
            credentials_file: Path to Google OAuth credentials (from Google Cloud Console)
            token_cache_dir: Directory to cache tokens (not in git)
        """
        self.credentials_file = credentials_file
        self.token_cache_dir = Path(token_cache_dir)
        self.token_cache_dir.mkdir(exist_ok=True, mode=0o700)  # Secure permissions

        # Ensure token cache is in .gitignore
        self._ensure_gitignore()

        self.credentials: GoogleCredentials | None = None

    def _ensure_gitignore(self) -> None:
        """Ensure token cache directory is in .gitignore."""
        gitignore_path = Path(".gitignore")
        if gitignore_path.exists():
            content = gitignore_path.read_text()
            if ".tokens/" not in content:
                with open(gitignore_path, "a") as f:
                    f.write("\n# Google OAuth tokens (never commit)\n.tokens/\n")
        else:
            gitignore_path.write_text(".tokens/\n")

    def has_valid_token(self) -> bool:
        """Check if we have a valid cached token."""
        token_file = self.token_cache_dir / "google_tokens.json"
        if not token_file.exists():
            return False

        try:
            data = json.loads(token_file.read_text())
            expires_at = data.get("expires_at")
            if expires_at:
                return datetime.fromtimestamp(expires_at) > datetime.utcnow()
        except Exception as e:
            logger.warning(f"Error checking cached token: {e}")

        return False

    def authorize_user(self, scopes: list[str] | None = None) -> GoogleCredentials:
        """Run OAuth 2.0 user authorization flow.

        This opens a browser to Google's login page. User logs in and grants permission.
        Token is saved to disk (not in git).

        Args:
            scopes: List of scopes to request (default: all)

        Returns:
            Credentials object
        """
        if scopes is None:
            scopes = ALL_SCOPES

        if not Path(self.credentials_file).exists():
            raise FileNotFoundError(
                f"Credentials file not found: {self.credentials_file}\n\n"
                "Download from Google Cloud Console:\n"
                "1. Go to https://console.cloud.google.com/\n"
                "2. Select your project\n"
                "3. APIs & Services → Credentials\n"
                "4. Create OAuth 2.0 Desktop Application\n"
                "5. Download JSON to client_secret.json\n"
            )

        try:
            logger.info(f"Starting OAuth flow for {len(scopes)} scopes...")
            flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, scopes=scopes)
            creds = flow.run_local_server(port=8888)

            # Cache token
            self._save_token(creds)
            logger.info("✓ Authorization successful, token cached to .tokens/google_tokens.json")

            self.credentials = creds
            return creds
        except Exception as e:
            logger.error(f"Authorization failed: {e}")
            raise

    def get_credentials(self, scopes: list[str] | None = None, force_refresh: bool = False) -> GoogleCredentials:
        """Get valid credentials, refreshing if needed.

        Args:
            scopes: List of scopes to request
            force_refresh: Force re-authorization even if cached token exists

        Returns:
            Credentials object
        """
        if scopes is None:
            scopes = ALL_SCOPES

        if force_refresh or not self.has_valid_token():
            logger.info("No valid cached token, starting authorization flow...")
            return self.authorize_user(scopes)

        token_file = self.token_cache_dir / "google_tokens.json"
        try:
            self.credentials = GoogleCredentials.from_authorized_user_file(token_file, scopes=scopes)
            logger.info(f"✓ Loaded cached credentials (expires at {self.credentials.expiry})")
            return self.credentials
        except Exception as e:
            logger.warning(f"Failed to load cached token: {e}, re-authorizing...")
            return self.authorize_user(scopes)

    def _save_token(self, creds: GoogleCredentials) -> None:
        """Save token to disk securely."""
        token_file = self.token_cache_dir / "google_tokens.json"
        token_data = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": creds.scopes,
            "expires_at": creds.expiry.timestamp() if creds.expiry else None,
        }
        token_file.write_text(json.dumps(token_data, indent=2))
        token_file.chmod(0o600)  # Secure permissions (owner read/write only)
        logger.debug(f"Token saved to {token_file}")

    def revoke(self) -> None:
        """Revoke credentials and delete cached token."""
        if self.credentials and self.credentials.token:
            try:
                httpx.post(
                    "https://oauth2.googleapis.com/revoke",
                    params={"token": self.credentials.token},
                    timeout=5.0,
                )
                logger.info("✓ Credentials revoked")
            except Exception as e:
                logger.warning(f"Could not revoke token: {e}")

        token_file = self.token_cache_dir / "google_tokens.json"
        if token_file.exists():
            token_file.unlink()
            logger.info("✓ Cached token deleted")

    def get_token_info(self) -> dict[str, Any]:
        """Get info about cached token (without sensitive data)."""
        token_file = self.token_cache_dir / "google_tokens.json"
        if not token_file.exists():
            return {"status": "no_token"}

        try:
            data = json.loads(token_file.read_text())
            expires_at = data.get("expires_at")
            now = datetime.utcnow().timestamp()

            return {
                "status": "valid" if expires_at and expires_at > now else "expired",
                "scopes": data.get("scopes", []),
                "expires_at": datetime.fromtimestamp(expires_at).isoformat() if expires_at else None,
                "time_until_expiry": expires_at - now if expires_at else None,
                "client_id": data.get("client_id", "unknown"),
            }
        except Exception as e:
            logger.error(f"Error reading token info: {e}")
            return {"status": "error", "error": str(e)}

    def refresh_if_needed(self) -> bool:
        """Refresh token if near expiry (within 5 minutes).

        Returns:
            True if token was refreshed or is still valid, False if refresh failed
        """
        if not self.credentials:
            return False

        if not self.credentials.expired:
            # Check if expiry is within 5 minutes
            if self.credentials.expiry and (self.credentials.expiry - datetime.utcnow()) < timedelta(minutes=5):
                logger.info("Token expires soon, refreshing...")
                try:
                    self.credentials.refresh(httpx.Request)
                    self._save_token(self.credentials)
                    logger.info("✓ Token refreshed")
                    return True
                except Exception as e:
                    logger.error(f"Token refresh failed: {e}")
                    return False
            return True

        return False


# Singleton instance
_oauth_manager: GoogleOAuthManager | None = None


def get_oauth_manager() -> GoogleOAuthManager:
    """Get or create singleton OAuth manager."""
    global _oauth_manager
    if _oauth_manager is None:
        creds_file = os.environ.get("GOOGLE_CREDENTIALS_FILE", "client_secret.json")
        token_dir = os.environ.get("GOOGLE_TOKEN_CACHE_DIR", ".tokens")
        _oauth_manager = GoogleOAuthManager(creds_file, token_dir)
    return _oauth_manager


def reset_oauth_manager() -> None:
    """Reset singleton (for testing)."""
    global _oauth_manager
    _oauth_manager = None
