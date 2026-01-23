"""Gmail connector for reading/syncing messages."""
import base64
import json
import os
from typing import Any, Dict, List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow, Flow
from google.auth import default
from googleapiclient.discovery import build

from src.logger import get_logger

logger = get_logger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.compose",
]


def create_gmail_connector() -> "GmailConnector":
    """Create a GmailConnector with credentials from environment.
    
    Looks for:
    1. GOOGLE_CREDENTIALS_FILE - path to service account JSON
    2. GOOGLE_CREDENTIALS_JSON - JSON content directly (or base64 encoded)
    3. Application Default Credentials
    """
    import base64
    creds_file = os.environ.get("GOOGLE_CREDENTIALS_FILE")
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    delegated_user = os.environ.get("GMAIL_DELEGATED_USER")  # For service account impersonation
    
    credentials = None
    
    if creds_file and os.path.exists(creds_file):
        logger.info(f"Loading Google credentials from file: {creds_file}")
        credentials = service_account.Credentials.from_service_account_file(
            creds_file, scopes=SCOPES
        )
        if delegated_user:
            credentials = credentials.with_subject(delegated_user)
    elif creds_json:
        logger.info("Loading Google credentials from JSON env var")
        # Try to decode base64 first, fall back to raw JSON
        try:
            decoded = base64.b64decode(creds_json).decode('utf-8')
            creds_data = json.loads(decoded)
        except Exception:
            # Not base64, try raw JSON
            creds_data = json.loads(creds_json)
        credentials = service_account.Credentials.from_service_account_info(
            creds_data, scopes=SCOPES
        )
        if delegated_user:
            credentials = credentials.with_subject(delegated_user)
    else:
        logger.warning("No Google credentials found, Gmail connector will be in mock mode")
    
    connector = GmailConnector(credentials=credentials)
    return connector


class GmailConnector:
    """Connector for Google Gmail API."""

    def __init__(self, credentials: Optional[Credentials] = None):
        """Initialize Gmail connector."""
        self.credentials = credentials
        self.service = None

    async def authenticate(self, client_id: str, client_secret: str, redirect_uri: str) -> None:
        """Authenticate with Google using OAuth2."""
        flow = Flow.from_client_config(
            {
                "installed": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [redirect_uri],
                }
            },
            scopes=SCOPES,
        )
        self.credentials = flow.run_local_server(port=0)

    def _build_service(self) -> None:
        """Build Gmail service from credentials."""
        if self.credentials:
            self.service = build("gmail", "v1", credentials=self.credentials)

    async def search_threads(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search for email threads matching query (e.g., from:email@example.com)."""
        if not self.service:
            self._build_service()

        try:
            results = self.service.users().threads().list(
                userId="me", q=query, maxResults=max_results
            ).execute()

            threads = results.get("threads", [])
            logger.info(f"Found {len(threads)} threads matching query", query=query)
            return threads
        except Exception as e:
            logger.error(f"Error searching threads: {e}")
            return []

    async def get_thread(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """Get full thread details including all messages."""
        if not self.service:
            self._build_service()

        try:
            thread = self.service.users().threads().get(
                userId="me", id=thread_id, format="full"
            ).execute()
            logger.info(f"Retrieved thread {thread_id}")
            return thread
        except Exception as e:
            logger.error(f"Error retrieving thread {thread_id}: {e}")
            return None

    async def get_messages(self, query: str = "", max_results: int = 10) -> List[Dict[str, Any]]:
        """Get messages from Gmail."""
        if not self.service:
            self._build_service()

        try:
            results = self.service.users().messages().list(
                userId="me", q=query, maxResults=max_results
            ).execute()

            messages = results.get("messages", [])
            logger.info(f"Retrieved {len(messages)} messages", query=query)
            return messages
        except Exception as e:
            logger.error(f"Error retrieving messages: {e}")
            return []

    async def get_message_detail(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get full message details."""
        if not self.service:
            self._build_service()

        try:
            message = self.service.users().messages().get(
                userId="me", id=message_id, format="full"
            ).execute()
            return message
        except Exception as e:
            logger.error(f"Error retrieving message {message_id}: {e}")
            return None

    async def create_draft(self, to: str, subject: str, body: str, from_email: Optional[str] = None) -> Optional[str]:
        """Create a draft email (DRAFT_ONLY mode - NOT SENT).
        
        Args:
            to: Recipient email
            subject: Email subject
            body: Email body
            from_email: Sender email (defaults to GMAIL_DELEGATED_USER env var - casey.l@pesti.io)
        """
        if not self.service:
            self._build_service()

        try:
            message = {
                "raw": self._create_message(to, subject, body, from_email=from_email)
            }
            result = self.service.users().drafts().create(
                userId="me", body={"message": message}
            ).execute()
            draft_id = result["id"]
            sender = from_email or os.environ.get("GMAIL_DELEGATED_USER", "me")
            logger.info(f"Created draft {draft_id} from {sender} to {to} (DRAFT_ONLY - not sent)", subject=subject)
            return draft_id
        except Exception as e:
            logger.error(f"Error creating draft to {to}: {e}")
            return None

    async def send_message(self, to: str, subject: str, body: str) -> Optional[str]:
        """Send an email message."""
        if not self.service:
            self._build_service()

        try:
            message = {
                "raw": self._create_message(to, subject, body)
            }
            result = self.service.users().messages().send(
                userId="me", body=message
            ).execute()
            logger.info(f"Message sent to {to}", message_id=result["id"])
            return result["id"]
        except Exception as e:
            logger.error(f"Error sending message to {to}: {e}")
            return None

    def _create_message(self, to: str, subject: str, body: str, from_email: Optional[str] = None) -> str:
        """Create a message in base64 format."""
        import base64
        from email.mime.text import MIMEText

        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        
        # Set From header - defaults to delegated user (casey.l@pesti.io)
        if from_email:
            message["from"] = from_email
        elif os.environ.get("GMAIL_DELEGATED_USER"):
            message["from"] = os.environ.get("GMAIL_DELEGATED_USER")
        
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        return raw
