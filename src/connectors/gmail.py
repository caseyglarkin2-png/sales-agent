"""Gmail connector for reading/syncing messages."""
import base64
import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow, Flow
from google.auth import default
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.logger import get_logger

logger = get_logger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.send",  # Added for email sending
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
    """Connector for Google Gmail API with OAuth token management."""
    
    # Shared circuit breaker for all Gmail connectors
    # Prevents cascading failures when Gmail API is having issues
    _circuit_breaker = None

    def __init__(self, credentials: Optional[Credentials] = None, user_email: Optional[str] = None):
        """Initialize Gmail connector.
        
        Args:
            credentials: Google OAuth2 credentials
            user_email: Email address for token storage (used as DB key)
        """
        self.credentials = credentials
        self.service = None
        self.user_email = user_email
        self._token_storage = None  # Will be set when needed
        
        # Initialize shared circuit breaker
        if GmailConnector._circuit_breaker is None:
            from src.resilience import CircuitBreaker
            GmailConnector._circuit_breaker = CircuitBreaker(
                failure_threshold=5,
                recovery_timeout=60.0,
                name="gmail",
            )

    @classmethod
    def get_circuit_breaker_state(cls) -> dict:
        """Get current circuit breaker state for monitoring."""
        if cls._circuit_breaker:
            return cls._circuit_breaker.get_state()
        return {"state": "uninitialized", "failure_count": 0}

    async def refresh_token_if_needed(self) -> bool:
        """Refresh OAuth token if expired or about to expire.
        
        Returns:
            bool: True if token is valid (refreshed if needed), False if refresh failed
        """
        if not self.credentials:
            logger.warning("No credentials available for refresh")
            return False
        
        # Check if token is expired or will expire in next 5 minutes
        if self.credentials.expired or self._token_expiring_soon():
            logger.info("OAuth token expired or expiring soon, refreshing...")
            
            try:
                self.credentials.refresh(Request())
                logger.info("OAuth token refreshed successfully")
                
                # Persist refreshed token
                await self._save_token()
                return True
            
            except Exception as e:
                logger.error(f"Failed to refresh OAuth token: {e}")
                return False
        
        return True
    
    def _token_expiring_soon(self, threshold_minutes: int = 5) -> bool:
        """Check if token will expire within threshold minutes."""
        if not self.credentials or not self.credentials.expiry:
            return False
        
        time_until_expiry = self.credentials.expiry - datetime.utcnow()
        return time_until_expiry < timedelta(minutes=threshold_minutes)
    
    async def _save_token(self) -> None:
        """Save OAuth token to database for persistence.
        
        Stores token info in oauth_tokens table with user_email as key.
        This ensures tokens survive server restarts.
        """
        if not self.credentials or not self.user_email:
            return
        
        try:
            from src.oauth_manager_legacy import store_oauth_token
            
            token_data = {
                "token": self.credentials.token,
                "refresh_token": self.credentials.refresh_token,
                "token_uri": self.credentials.token_uri,
                "client_id": self.credentials.client_id,
                "client_secret": self.credentials.client_secret,
                "scopes": self.credentials.scopes,
                "expiry": self.credentials.expiry.isoformat() if self.credentials.expiry else None,
            }
            
            await store_oauth_token(
                user_email=self.user_email,
                provider="google",
                token_data=token_data
            )
            
            logger.info(f"Saved OAuth token for {self.user_email}")
        
        except Exception as e:
            logger.error(f"Failed to save OAuth token: {e}")
    
    async def load_token(self, user_email: str) -> bool:
        """Load OAuth token from database.
        
        Args:
            user_email: Email address to load token for
            
        Returns:
            bool: True if token loaded successfully
        """
        try:
            from src.oauth_manager_legacy import retrieve_oauth_token
            
            token_data = await retrieve_oauth_token(user_email, provider="google")
            
            if not token_data:
                logger.warning(f"No stored token found for {user_email}")
                return False
            
            # Reconstruct credentials from stored data
            self.credentials = Credentials(
                token=token_data.get("token"),
                refresh_token=token_data.get("refresh_token"),
                token_uri=token_data.get("token_uri"),
                client_id=token_data.get("client_id"),
                client_secret=token_data.get("client_secret"),
                scopes=token_data.get("scopes"),
            )
            
            # Set expiry if present
            if token_data.get("expiry"):
                from datetime import datetime
                self.credentials.expiry = datetime.fromisoformat(token_data["expiry"])
            
            self.user_email = user_email
            logger.info(f"Loaded OAuth token for {user_email}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to load OAuth token for {user_email}: {e}")
            return False
    
    async def revoke_token(self) -> bool:
        """Revoke OAuth token and remove from database.
        
        Returns:
            bool: True if revocation successful
        """
        if not self.credentials:
            return False
        
        try:
            # Revoke with Google
            import requests
            requests.post(
                'https://oauth2.googleapis.com/revoke',
                params={'token': self.credentials.token},
                headers={'content-type': 'application/x-www-form-urlencoded'}
            )
            
            # Remove from database
            if self.user_email:
                from src.oauth_manager_legacy import revoke_oauth_token
                await revoke_oauth_token(self.user_email, provider="google")
            
            logger.info(f"Revoked OAuth token for {self.user_email}")
            self.credentials = None
            self.service = None
            return True
        
        except Exception as e:
            logger.error(f"Failed to revoke OAuth token: {e}")
            return False

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
            # Refresh token if needed before building service
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If in async context, schedule refresh
                    asyncio.create_task(self.refresh_token_if_needed())
                else:
                    # If not in async context, run synchronously
                    loop.run_until_complete(self.refresh_token_if_needed())
            except Exception as e:
                logger.warning(f"Could not refresh token before building service: {e}")
            
            self.service = build("gmail", "v1", credentials=self.credentials)

    async def health_check(self) -> Dict[str, Any]:
        """Check Gmail API connectivity and return health status.
        
        Uses a lightweight getProfile call to verify API access.
        
        Returns:
            Dict with status, latency_ms, and optional error
        """
        import time
        
        start_time = time.time()
        
        if not self.credentials:
            return {
                "status": "unhealthy",
                "latency_ms": 0,
                "error": "No credentials configured",
            }
        
        try:
            if not self.service:
                self._build_service()
            
            # Lightweight profile check
            profile = self.service.users().getProfile(userId="me").execute()
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            return {
                "status": "healthy",
                "latency_ms": latency_ms,
                "email": profile.get("emailAddress"),
                "messages_total": profile.get("messagesTotal"),
                "error": None,
            }
        
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Gmail health check failed: {e}")
            return {
                "status": "unhealthy",
                "latency_ms": latency_ms,
                "error": str(e),
            }

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

    async def send_email(
        self,
        from_email: str,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        in_reply_to: Optional[str] = None,
        references: Optional[str] = None,
        max_retries: int = 3,
    ) -> Optional[Dict[str, Any]]:
        """Send email via Gmail API with circuit breaker and retry logic.
        
        The circuit breaker protects against cascading failures when Gmail
        API is experiencing issues. After 5 consecutive failures, the circuit
        opens and requests fail fast for 60 seconds before attempting recovery.
        
        Args:
            from_email: Sender email address
            to_email: Recipient email address
            subject: Email subject
            body_text: Plain text email body
            body_html: HTML email body (optional)
            in_reply_to: Message-ID to reply to (for threading)
            references: Space-separated Message-IDs for thread context
            max_retries: Maximum number of retry attempts on failure
            
        Returns:
            dict with 'id' (message_id) and 'threadId', or None on failure
            
        Raises:
            Exception: On unrecoverable errors (after retries exhausted)
            CircuitBreakerOpenError: When circuit breaker is open
        """
        from src.resilience import CircuitBreakerOpenError
        
        # Check circuit breaker before attempting send
        if self._circuit_breaker and self._circuit_breaker.state == "open":
            if not self._circuit_breaker._should_attempt_reset():
                logger.warning(f"Gmail circuit breaker is open, failing fast for email to {to_email}")
                raise CircuitBreakerOpenError("Gmail circuit breaker is open - failing fast")
            else:
                logger.info("Gmail circuit breaker transitioning to half-open, attempting send")
                self._circuit_breaker.state = "half_open"
        
        if not self.service:
            self._build_service()
        
        # Ensure token is valid before sending
        if not await self.refresh_token_if_needed():
            raise Exception("Failed to refresh OAuth token before sending email")
        
        # Build RFC 2822 compliant MIME message
        from src.email_utils.mime_builder import build_mime_message
        
        mime_message = build_mime_message(
            from_email=from_email,
            to_email=to_email,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            in_reply_to=in_reply_to,
            references=references,
        )
        
        # Encode for Gmail API
        encoded_message = base64.urlsafe_b64encode(mime_message.encode()).decode()
        
        # Retry logic with exponential backoff (circuit breaker tracks failures)
        for attempt in range(max_retries):
            try:
                result = self.service.users().messages().send(
                    userId="me",
                    body={"raw": encoded_message}
                ).execute()
                
                message_id = result.get("id")
                thread_id = result.get("threadId")
                
                logger.info(
                    f"Email sent successfully: from={from_email}, to={to_email}, "
                    f"subject='{subject[:50]}...', message_id={message_id}, thread_id={thread_id}"
                )
                
                # Record success for circuit breaker
                if self._circuit_breaker:
                    self._circuit_breaker._on_success()
                
                return {
                    "id": message_id,
                    "threadId": thread_id,
                    "labelIds": result.get("labelIds", []),
                }
            
            except HttpError as e:
                error_reason = self._parse_http_error(e)
                
                # Record failure for circuit breaker
                if self._circuit_breaker:
                    self._circuit_breaker._on_failure()
                
                # Check if error is retryable
                if self._is_retryable_error(e):
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.warning(
                        f"Gmail API error (attempt {attempt + 1}/{max_retries}): {error_reason}. "
                        f"Retrying in {wait_time}s..."
                    )
                    
                    if attempt < max_retries - 1:
                        import asyncio
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"Max retries ({max_retries}) exhausted for email send")
                        raise
                else:
                    # Non-retryable error (e.g., invalid recipient, quota exceeded)
                    logger.error(f"Non-retryable Gmail API error: {error_reason}")
                    raise
            
            except Exception as e:
                logger.error(f"Unexpected error sending email (attempt {attempt + 1}/{max_retries}): {e}")
                
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    import asyncio
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise
        
        return None
    
    def _parse_http_error(self, error: HttpError) -> str:
        """Parse HttpError to extract meaningful error message."""
        try:
            error_details = json.loads(error.content.decode())
            return error_details.get("error", {}).get("message", str(error))
        except Exception:
            return str(error)
    
    def _is_retryable_error(self, error: HttpError) -> bool:
        """Determine if an HttpError is retryable.
        
        Retryable errors:
        - 429: Rate limit exceeded
        - 500, 502, 503, 504: Server errors
        - Network timeouts
        
        Non-retryable errors:
        - 400: Bad request (malformed message)
        - 401: Unauthorized (token invalid)
        - 403: Forbidden (quota exceeded for day)
        - 404: Not found
        """
        retryable_codes = {429, 500, 502, 503, 504}
        return error.resp.status in retryable_codes

    async def delete_draft(self, draft_id: str) -> bool:
        """Delete a draft email from Gmail.
        
        Args:
            draft_id: Gmail draft ID to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        if not self.service:
            self._build_service()
        
        try:
            self.service.users().drafts().delete(
                userId="me",
                id=draft_id
            ).execute()
            logger.info(f"Deleted draft {draft_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting draft {draft_id}: {e}")
            return False

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
