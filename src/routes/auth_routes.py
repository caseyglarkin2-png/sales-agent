"""
Auth Routes - Authentication and authorization management
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Header, Depends, Request
from pydantic import BaseModel, Field, EmailStr
from enum import Enum
import structlog
import secrets
import hashlib
from src.rate_limiter import rate_limit

logger = structlog.get_logger()

router = APIRouter(prefix="/auth", tags=["Authentication"])


class AuthProvider(str, Enum):
    LOCAL = "local"
    GOOGLE = "google"
    MICROSOFT = "microsoft"
    SAML = "saml"
    OIDC = "oidc"
    LDAP = "ldap"


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"
    API_KEY = "api_key"
    RESET_PASSWORD = "reset_password"
    EMAIL_VERIFICATION = "email_verification"
    INVITE = "invite"


class MFAMethod(str, Enum):
    TOTP = "totp"
    SMS = "sms"
    EMAIL = "email"
    PUSH = "push"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False
    mfa_code: Optional[str] = None


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    company: Optional[str] = None
    phone: Optional[str] = None
    invite_code: Optional[str] = None


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class MFASetup(BaseModel):
    method: MFAMethod
    phone_number: Optional[str] = None  # For SMS


class MFAVerify(BaseModel):
    code: str
    method: MFAMethod


class OAuthInitiate(BaseModel):
    provider: AuthProvider
    redirect_uri: str
    state: Optional[str] = None


class OAuthCallback(BaseModel):
    provider: AuthProvider
    code: str
    state: Optional[str] = None


class SessionInfo(BaseModel):
    include_history: bool = False


class TokenRefresh(BaseModel):
    refresh_token: str


# In-memory storage
users = {}
sessions = {}
tokens = {}
mfa_secrets = {}
password_reset_tokens = {}
oauth_states = {}


def hash_password(password: str) -> str:
    """Hash password with salt"""
    salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return f"{salt}:{hashed.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify password against stored hash"""
    try:
        salt, hashed = stored_hash.split(":")
        check_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return check_hash.hex() == hashed
    except:
        return False


def generate_token(length: int = 32) -> str:
    """Generate secure random token"""
    return secrets.token_urlsafe(length)


@router.post("/register")
@rate_limit(max_requests=5, window_seconds=60)
async def register(
    request: RegisterRequest,
    tenant_id: str = Query(default="default"),
    http_request: Request = None
):
    """Register a new user"""
    import uuid
    
    # Check if email exists
    for user in users.values():
        if user.get("email") == request.email and user.get("tenant_id") == tenant_id:
            raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    user = {
        "id": user_id,
        "email": request.email,
        "password_hash": hash_password(request.password),
        "first_name": request.first_name,
        "last_name": request.last_name,
        "company": request.company,
        "phone": request.phone,
        "provider": AuthProvider.LOCAL.value,
        "email_verified": False,
        "mfa_enabled": False,
        "status": "active",
        "roles": ["user"],
        "tenant_id": tenant_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    users[user_id] = user
    
    # Generate email verification token
    verify_token = generate_token()
    tokens[verify_token] = {
        "type": TokenType.EMAIL_VERIFICATION.value,
        "user_id": user_id,
        "expires_at": (now + timedelta(hours=24)).isoformat()
    }
    
    logger.info("user_registered", user_id=user_id, email=request.email)
    
    return {
        "user_id": user_id,
        "email": request.email,
        "message": "Registration successful. Please verify your email.",
        "verification_required": True
    }


@router.post("/login")
@rate_limit(max_requests=10, window_seconds=60)
async def login(
    request: LoginRequest,
    user_agent: Optional[str] = Header(None),
    tenant_id: str = Query(default="default"),
    http_request: Request = None
):
    """Authenticate user and create session"""
    import uuid
    
    # Find user
    user = None
    for u in users.values():
        if u.get("email") == request.email and u.get("tenant_id") == tenant_id:
            user = u
            break
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not verify_password(request.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if user.get("status") != "active":
        raise HTTPException(status_code=403, detail="Account is not active")
    
    # Check MFA if enabled
    if user.get("mfa_enabled") and not request.mfa_code:
        return {
            "mfa_required": True,
            "mfa_method": user.get("mfa_method", "totp"),
            "message": "MFA verification required"
        }
    
    if user.get("mfa_enabled") and request.mfa_code:
        if not _verify_mfa_code(user["id"], request.mfa_code):
            raise HTTPException(status_code=401, detail="Invalid MFA code")
    
    now = datetime.utcnow()
    session_id = str(uuid.uuid4())
    
    # Generate tokens
    access_token = generate_token()
    refresh_token = generate_token() if request.remember_me else None
    
    token_expiry = timedelta(hours=24) if request.remember_me else timedelta(hours=1)
    
    session = {
        "id": session_id,
        "user_id": user["id"],
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user_agent": user_agent,
        "ip_address": "127.0.0.1",  # Would get from request
        "expires_at": (now + token_expiry).isoformat(),
        "created_at": now.isoformat(),
        "last_activity": now.isoformat()
    }
    
    sessions[session_id] = session
    tokens[access_token] = {
        "type": TokenType.ACCESS.value,
        "session_id": session_id,
        "user_id": user["id"],
        "expires_at": session["expires_at"]
    }
    
    if refresh_token:
        tokens[refresh_token] = {
            "type": TokenType.REFRESH.value,
            "session_id": session_id,
            "user_id": user["id"],
            "expires_at": (now + timedelta(days=30)).isoformat()
        }
    
    # Update last login
    user["last_login"] = now.isoformat()
    user["login_count"] = user.get("login_count", 0) + 1
    
    logger.info("user_logged_in", user_id=user["id"], session_id=session_id)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": int(token_expiry.total_seconds()),
        "user": {
            "id": user["id"],
            "email": user["email"],
            "first_name": user["first_name"],
            "last_name": user["last_name"],
            "roles": user.get("roles", [])
        }
    }


def _verify_mfa_code(user_id: str, code: str) -> bool:
    """Verify MFA code (mock implementation)"""
    # In production, would verify TOTP, SMS code, etc.
    return code == "123456"  # Mock verification


@router.post("/logout")
async def logout(
    authorization: Optional[str] = Header(None)
):
    """Logout and invalidate session"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.replace("Bearer ", "")
    token_data = tokens.get(token)
    
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    session_id = token_data.get("session_id")
    
    # Remove session and tokens
    if session_id and session_id in sessions:
        session = sessions[session_id]
        
        # Remove associated tokens
        for t, data in list(tokens.items()):
            if data.get("session_id") == session_id:
                del tokens[t]
        
        del sessions[session_id]
    
    logger.info("user_logged_out", session_id=session_id)
    return {"message": "Logged out successfully"}


@router.post("/refresh")
async def refresh_token(request: TokenRefresh):
    """Refresh access token"""
    import uuid
    
    token_data = tokens.get(request.refresh_token)
    
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    if token_data.get("type") != TokenType.REFRESH.value:
        raise HTTPException(status_code=401, detail="Invalid token type")
    
    # Check expiry
    expires_at = datetime.fromisoformat(token_data["expires_at"].replace("Z", "+00:00"))
    if expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Refresh token expired")
    
    now = datetime.utcnow()
    session_id = token_data.get("session_id")
    user_id = token_data.get("user_id")
    
    # Generate new access token
    new_access_token = generate_token()
    
    tokens[new_access_token] = {
        "type": TokenType.ACCESS.value,
        "session_id": session_id,
        "user_id": user_id,
        "expires_at": (now + timedelta(hours=1)).isoformat()
    }
    
    # Update session
    if session_id in sessions:
        sessions[session_id]["access_token"] = new_access_token
        sessions[session_id]["last_activity"] = now.isoformat()
    
    logger.info("token_refreshed", user_id=user_id)
    
    return {
        "access_token": new_access_token,
        "token_type": "Bearer",
        "expires_in": 3600
    }


@router.post("/password/reset-request")
@rate_limit(max_requests=5, window_seconds=300)
async def request_password_reset(
    request: PasswordResetRequest,
    tenant_id: str = Query(default="default"),
    http_request: Request = None
):
    """Request password reset"""
    # Find user
    user = None
    for u in users.values():
        if u.get("email") == request.email and u.get("tenant_id") == tenant_id:
            user = u
            break
    
    # Always return success (don't reveal if email exists)
    if user:
        reset_token = generate_token()
        now = datetime.utcnow()
        
        password_reset_tokens[reset_token] = {
            "user_id": user["id"],
            "email": request.email,
            "expires_at": (now + timedelta(hours=1)).isoformat(),
            "used": False
        }
        
        logger.info("password_reset_requested", email=request.email)
    
    return {
        "message": "If the email exists, a password reset link has been sent."
    }


@router.post("/password/reset-confirm")
async def confirm_password_reset(request: PasswordResetConfirm):
    """Confirm password reset with token"""
    token_data = password_reset_tokens.get(request.token)
    
    if not token_data:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    
    if token_data.get("used"):
        raise HTTPException(status_code=400, detail="Token already used")
    
    expires_at = datetime.fromisoformat(token_data["expires_at"].replace("Z", "+00:00"))
    if expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Token expired")
    
    user_id = token_data["user_id"]
    if user_id not in users:
        raise HTTPException(status_code=400, detail="User not found")
    
    # Update password
    users[user_id]["password_hash"] = hash_password(request.new_password)
    users[user_id]["updated_at"] = datetime.utcnow().isoformat()
    
    # Invalidate token
    token_data["used"] = True
    
    # Invalidate all sessions
    for session_id, session in list(sessions.items()):
        if session.get("user_id") == user_id:
            del sessions[session_id]
    
    logger.info("password_reset_completed", user_id=user_id)
    
    return {"message": "Password reset successful"}


@router.post("/password/change")
async def change_password(
    request: PasswordChange,
    authorization: Optional[str] = Header(None)
):
    """Change password for authenticated user"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.replace("Bearer ", "")
    token_data = tokens.get(token)
    
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = token_data.get("user_id")
    user = users.get(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not verify_password(request.current_password, user.get("password_hash", "")):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    user["password_hash"] = hash_password(request.new_password)
    user["updated_at"] = datetime.utcnow().isoformat()
    
    logger.info("password_changed", user_id=user_id)
    
    return {"message": "Password changed successfully"}


@router.post("/mfa/setup")
async def setup_mfa(
    request: MFASetup,
    authorization: Optional[str] = Header(None)
):
    """Set up MFA for user"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.replace("Bearer ", "")
    token_data = tokens.get(token)
    
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = token_data.get("user_id")
    
    # Generate MFA secret
    mfa_secret = generate_token(20)
    
    mfa_secrets[user_id] = {
        "secret": mfa_secret,
        "method": request.method.value,
        "phone": request.phone_number,
        "verified": False,
        "created_at": datetime.utcnow().isoformat()
    }
    
    if request.method == MFAMethod.TOTP:
        # Would generate QR code for authenticator app
        return {
            "method": request.method.value,
            "secret": mfa_secret,
            "qr_code_url": f"otpauth://totp/SalesAgent:{user_id}?secret={mfa_secret}",
            "message": "Scan the QR code with your authenticator app"
        }
    elif request.method == MFAMethod.SMS:
        return {
            "method": request.method.value,
            "phone": request.phone_number,
            "message": "SMS verification code sent"
        }
    else:
        return {
            "method": request.method.value,
            "message": f"Verification code sent via {request.method.value}"
        }


@router.post("/mfa/verify")
async def verify_mfa(
    request: MFAVerify,
    authorization: Optional[str] = Header(None)
):
    """Verify MFA setup"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.replace("Bearer ", "")
    token_data = tokens.get(token)
    
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = token_data.get("user_id")
    mfa_data = mfa_secrets.get(user_id)
    
    if not mfa_data:
        raise HTTPException(status_code=400, detail="MFA not configured")
    
    # Verify code (mock - would use actual TOTP verification)
    if request.code == "123456":  # Mock verification
        mfa_data["verified"] = True
        
        user = users.get(user_id)
        if user:
            user["mfa_enabled"] = True
            user["mfa_method"] = request.method.value
        
        logger.info("mfa_enabled", user_id=user_id, method=request.method.value)
        
        return {"message": "MFA enabled successfully", "backup_codes": [generate_token(8) for _ in range(10)]}
    else:
        raise HTTPException(status_code=400, detail="Invalid verification code")


@router.delete("/mfa")
async def disable_mfa(
    authorization: Optional[str] = Header(None)
):
    """Disable MFA for user"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.replace("Bearer ", "")
    token_data = tokens.get(token)
    
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = token_data.get("user_id")
    
    if user_id in mfa_secrets:
        del mfa_secrets[user_id]
    
    user = users.get(user_id)
    if user:
        user["mfa_enabled"] = False
        user["mfa_method"] = None
    
    logger.info("mfa_disabled", user_id=user_id)
    
    return {"message": "MFA disabled"}


@router.get("/sessions")
async def list_sessions(
    authorization: Optional[str] = Header(None)
):
    """List active sessions for user"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.replace("Bearer ", "")
    token_data = tokens.get(token)
    
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = token_data.get("user_id")
    current_session_id = token_data.get("session_id")
    
    user_sessions = [
        {
            "id": s["id"],
            "user_agent": s.get("user_agent"),
            "ip_address": s.get("ip_address"),
            "created_at": s.get("created_at"),
            "last_activity": s.get("last_activity"),
            "is_current": s["id"] == current_session_id
        }
        for s in sessions.values()
        if s.get("user_id") == user_id
    ]
    
    return {"sessions": user_sessions, "total": len(user_sessions)}


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: str,
    authorization: Optional[str] = Header(None)
):
    """Revoke a specific session"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.replace("Bearer ", "")
    token_data = tokens.get(token)
    
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = token_data.get("user_id")
    
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    if session.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Remove associated tokens
    for t, data in list(tokens.items()):
        if data.get("session_id") == session_id:
            del tokens[t]
    
    del sessions[session_id]
    
    logger.info("session_revoked", session_id=session_id, user_id=user_id)
    
    return {"message": "Session revoked"}


@router.post("/oauth/initiate")
async def initiate_oauth(
    request: OAuthInitiate,
    tenant_id: str = Query(default="default")
):
    """Initiate OAuth flow"""
    import uuid
    import os
    
    state = request.state or str(uuid.uuid4())
    
    oauth_urls = {
        AuthProvider.GOOGLE: "https://accounts.google.com/o/oauth2/v2/auth",
        AuthProvider.MICROSOFT: "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
    }
    
    base_url = oauth_urls.get(request.provider)
    if not base_url:
        raise HTTPException(status_code=400, detail=f"Unsupported OAuth provider: {request.provider}")
    
    oauth_states[state] = {
        "provider": request.provider.value,
        "redirect_uri": request.redirect_uri,
        "tenant_id": tenant_id,
        "expires_at": (datetime.utcnow() + timedelta(minutes=10)).isoformat()
    }
    
    # Use real credentials from environment
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "YOUR_CLIENT_ID")
    redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI", request.redirect_uri)
    scopes = "email profile https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/drive.readonly"
    
    oauth_url = f"{base_url}?client_id={client_id}&redirect_uri={redirect_uri}&state={state}&response_type=code&scope={scopes}&access_type=offline&prompt=consent"
    
    return {
        "oauth_url": oauth_url,
        "state": state,
        "provider": request.provider.value
    }


@router.get("/me")
async def get_current_user(authorization: Optional[str] = Header(None)):
    """Get current authenticated user"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.replace("Bearer ", "")
    token_data = tokens.get(token)
    
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Check expiry
    expires_at = datetime.fromisoformat(token_data["expires_at"].replace("Z", "+00:00"))
    if expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Token expired")
    
    user_id = token_data.get("user_id")
    user = users.get(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": user["id"],
        "email": user["email"],
        "first_name": user["first_name"],
        "last_name": user["last_name"],
        "company": user.get("company"),
        "phone": user.get("phone"),
        "roles": user.get("roles", []),
        "mfa_enabled": user.get("mfa_enabled", False),
        "email_verified": user.get("email_verified", False),
        "created_at": user.get("created_at"),
        "last_login": user.get("last_login")
    }


# Token storage for OAuth
google_tokens = {}


@router.get("/google/callback")
async def google_oauth_callback(
    code: str = Query(...),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None)
):
    """Handle Google OAuth callback - exchange code for tokens
    
    DEPRECATED (Sprint 33): This route is deprecated. 
    Use /auth/callback via web_auth.py instead.
    This route will be removed in Sprint 35.
    """
    import os
    import httpx
    from fastapi.responses import HTMLResponse
    
    # Log deprecation warning
    logger.warning(
        "DEPRECATED: /auth/google/callback is deprecated. "
        "Use /auth/callback instead. This route will be removed in Sprint 35."
    )
    
    if error:
        return HTMLResponse(f"""
        <html><body>
        <h1>Authentication Failed</h1>
        <p>Error: {error}</p>
        <p><a href="/">Return to Dashboard</a></p>
        </body></html>
        """, status_code=400)
    
    # Exchange code for tokens
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI")
    
    if not all([client_id, client_secret, redirect_uri]):
        return HTMLResponse("""
        <html><body>
        <h1>Configuration Error</h1>
        <p>Google OAuth credentials not configured.</p>
        </body></html>
        """, status_code=500)
    
    try:
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                }
            )
            
            if token_response.status_code != 200:
                logger.error(f"Token exchange failed: {token_response.text}")
                return HTMLResponse(f"""
                <html><body>
                <h1>Authentication Failed</h1>
                <p>Could not exchange code for tokens.</p>
                <p><a href="/">Return to Dashboard</a></p>
                </body></html>
                """, status_code=400)
            
            tokens_data = token_response.json()
            
            # Get user info
            user_response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {tokens_data['access_token']}"}
            )
            user_info = user_response.json()
            
            # Store tokens (in production, use proper secure storage)
            email = user_info.get("email", "unknown")
            google_tokens[email] = {
                "access_token": tokens_data.get("access_token"),
                "refresh_token": tokens_data.get("refresh_token"),
                "expires_in": tokens_data.get("expires_in"),
                "token_type": tokens_data.get("token_type"),
                "scope": tokens_data.get("scope"),
                "created_at": datetime.utcnow().isoformat(),
                "user_info": user_info,
            }
            
            logger.info(f"Google OAuth successful for {email}")
            
            return HTMLResponse(f"""
            <html>
            <head>
                <title>Connected!</title>
                <style>
                    body {{ font-family: system-ui; max-width: 600px; margin: 100px auto; text-align: center; }}
                    .success {{ color: #22c55e; font-size: 48px; }}
                    h1 {{ color: #1f2937; }}
                    p {{ color: #6b7280; }}
                    a {{ color: #8b5cf6; text-decoration: none; }}
                </style>
            </head>
            <body>
                <div class="success">✓</div>
                <h1>Google Connected!</h1>
                <p>Successfully connected as <strong>{email}</strong></p>
                <p>Gmail and Drive access is now enabled.</p>
                <br>
                <a href="/">Return to Dashboard</a>
            </body>
            </html>
            """)
            
    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        return HTMLResponse(f"""
        <html><body>
        <h1>Error</h1>
        <p>{str(e)}</p>
        <p><a href="/">Return to Dashboard</a></p>
        </body></html>
        """, status_code=500)


@router.get("/google/status")
async def google_oauth_status():
    """Check if Google OAuth is connected"""
    import os
    
    has_credentials = bool(os.environ.get("GOOGLE_CLIENT_ID"))
    connected_accounts = list(google_tokens.keys())
    
    return {
        "configured": has_credentials,
        "connected_accounts": connected_accounts,
        "gmail_enabled": len(connected_accounts) > 0,
        "drive_enabled": len(connected_accounts) > 0,
    }
