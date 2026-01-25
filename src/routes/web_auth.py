"""Web Authentication Routes for CaseyOS.

Sprint 1 - Google OAuth web flow for browser-based login.
"""
import json
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Request, Depends, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.db import get_db
from src.models.user import User, UserSession
from src.auth.session import create_session, get_session_by_token, delete_session
from src.auth.allowed_users import is_email_allowed
from src.auth.decorators import SESSION_COOKIE_NAME
from src.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Web Auth"])

# Google OAuth configuration
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "")

# OAuth scopes - request all upfront per Sprint 1 plan
OAUTH_SCOPES = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
]

# State tokens for CSRF protection
# Note: In production with multiple workers, use Redis instead
# For single-worker Railway deployment, in-memory is acceptable
_oauth_states: dict[str, dict] = {}

# Cookie security - only require HTTPS in production
_is_production = bool(os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("PRODUCTION"))


def get_base_url(request: Request) -> str:
    """Get the base URL for redirects."""
    # Check for forwarded headers (Railway, etc.)
    forwarded_proto = request.headers.get("x-forwarded-proto", "http")
    forwarded_host = request.headers.get("x-forwarded-host", request.headers.get("host", "localhost"))
    return f"{forwarded_proto}://{forwarded_host}"


@router.get("/login")
async def login_page(request: Request, error: Optional[str] = None):
    """Render the login page."""
    base_url = get_base_url(request)
    
    # Check if already logged in
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    if session_token:
        return RedirectResponse(url="/dashboard", status_code=302)
    
    error_html = ""
    if error:
        error_messages = {
            "access_denied": "Access denied. Your email is not authorized.",
            "oauth_failed": "Google sign-in failed. Please try again.",
            "no_email": "Could not get email from Google. Please try again.",
        }
        error_text = error_messages.get(error, "An error occurred. Please try again.")
        error_html = f'<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">{error_text}</div>'
    
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CaseyOS - Login</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gradient-to-br from-purple-900 via-indigo-900 to-blue-900 min-h-screen flex items-center justify-center">
    <div class="bg-white rounded-2xl shadow-2xl p-8 w-full max-w-md">
        <div class="text-center mb-8">
            <h1 class="text-3xl font-bold text-gray-800 mb-2">🎯 CaseyOS</h1>
            <p class="text-gray-600">GTM Command Center</p>
        </div>
        
        {error_html}
        
        <a href="/auth/google" 
           class="w-full flex items-center justify-center gap-3 bg-white border-2 border-gray-200 rounded-lg px-6 py-3 text-gray-700 font-medium hover:bg-gray-50 hover:border-gray-300 transition-all">
            <img src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg" class="w-5 h-5">
            Sign in with Google
        </a>
        
        <p class="text-center text-gray-500 text-sm mt-6">
            Only authorized users can access CaseyOS
        </p>
    </div>
</body>
</html>
"""
    return HTMLResponse(content=html)


@router.get("/auth/google")
async def google_auth_redirect(request: Request):
    """Initiate Google OAuth flow."""
    if not GOOGLE_CLIENT_ID:
        logger.error("GOOGLE_CLIENT_ID not configured")
        raise HTTPException(status_code=500, detail="Google OAuth not configured")
    
    # Generate state token for CSRF protection
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = {
        "created_at": datetime.utcnow(),
        "redirect_after": request.query_params.get("redirect", "/dashboard"),
    }
    
    # Clean up old states (older than 10 minutes)
    cutoff = datetime.utcnow().timestamp() - 600
    for s in list(_oauth_states.keys()):
        if _oauth_states[s]["created_at"].timestamp() < cutoff:
            del _oauth_states[s]
    
    # Build the redirect URI
    base_url = get_base_url(request)
    redirect_uri = GOOGLE_REDIRECT_URI or f"{base_url}/auth/callback"
    
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(OAUTH_SCOPES),
        "state": state,
        "access_type": "offline",  # Get refresh token
        "prompt": "consent",  # Always show consent to get refresh token
    }
    
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    logger.info(f"Redirecting to Google OAuth: {auth_url[:100]}...")
    
    return RedirectResponse(url=auth_url, status_code=302)


@router.get("/auth/callback")
async def google_auth_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Handle Google OAuth callback."""
    # Check for OAuth error
    if error:
        logger.warning(f"OAuth error from Google: {error}")
        return RedirectResponse(url="/login?error=oauth_failed", status_code=302)
    
    # Validate state
    if not state or state not in _oauth_states:
        logger.warning("Invalid or missing OAuth state")
        return RedirectResponse(url="/login?error=oauth_failed", status_code=302)
    
    state_data = _oauth_states.pop(state)
    redirect_after = state_data.get("redirect_after", "/dashboard")
    
    if not code:
        logger.warning("No authorization code received")
        return RedirectResponse(url="/login?error=oauth_failed", status_code=302)
    
    # Exchange code for tokens
    base_url = get_base_url(request)
    redirect_uri = GOOGLE_REDIRECT_URI or f"{base_url}/auth/callback"
    
    try:
        async with httpx.AsyncClient() as client:
            # Exchange code for tokens
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                },
            )
            
            if token_response.status_code != 200:
                logger.error(f"Token exchange failed: {token_response.text}")
                return RedirectResponse(url="/login?error=oauth_failed", status_code=302)
            
            tokens = token_response.json()
            access_token = tokens.get("access_token")
            refresh_token = tokens.get("refresh_token")
            expires_in = tokens.get("expires_in", 3600)
            
            # Get user info
            userinfo_response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            
            if userinfo_response.status_code != 200:
                logger.error(f"Failed to get user info: {userinfo_response.text}")
                return RedirectResponse(url="/login?error=oauth_failed", status_code=302)
            
            userinfo = userinfo_response.json()
            email = userinfo.get("email", "").lower()
            name = userinfo.get("name", "")
            picture = userinfo.get("picture", "")
            
            if not email:
                logger.error("No email in userinfo response")
                return RedirectResponse(url="/login?error=no_email", status_code=302)
            
            # Check if email is allowed
            if not is_email_allowed(email):
                logger.warning(f"Unauthorized email attempted login: {email}")
                return RedirectResponse(url="/login?error=access_denied", status_code=302)
            
            # Find or create user
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            
            # Calculate token expiry correctly
            token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)
            
            if user:
                # Update existing user
                user.name = name
                user.picture = picture
                user.google_access_token = access_token
                user.google_refresh_token = refresh_token or user.google_refresh_token
                user.google_token_expiry = token_expiry
                user.google_token_scopes = OAUTH_SCOPES
                user.last_login = datetime.utcnow()
                user.is_allowed = True
                logger.info(f"Updated existing user: {email}")
            else:
                # Create new user
                user = User(
                    email=email,
                    name=name,
                    picture=picture,
                    google_access_token=access_token,
                    google_refresh_token=refresh_token,
                    google_token_expiry=token_expiry,
                    google_token_scopes=OAUTH_SCOPES,
                    last_login=datetime.utcnow(),
                    is_active=True,
                    is_allowed=True,
                )
                db.add(user)
                logger.info(f"Created new user: {email}")
            
            await db.commit()
            await db.refresh(user)
            
            # Create session
            session = await create_session(
                db=db,
                user_id=user.id,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )
            
            # Set session cookie and redirect
            response = RedirectResponse(url=redirect_after, status_code=302)
            response.set_cookie(
                key=SESSION_COOKIE_NAME,
                value=session.session_token,
                httponly=True,
                secure=_is_production,  # Only require HTTPS in production
                samesite="lax",
                max_age=7 * 24 * 60 * 60,  # 7 days
            )
            
            logger.info(f"User logged in: {email}")
            return response
            
    except Exception as e:
        logger.exception(f"OAuth callback error: {e}")
        return RedirectResponse(url="/login?error=oauth_failed", status_code=302)


@router.get("/logout")
@router.post("/logout")
async def logout(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Log out the current user."""
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    
    if session_token:
        await delete_session(db, session_token)
        logger.info(f"User logged out, session deleted")
    
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response


@router.get("/dashboard")
async def dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Render the main dashboard."""
    from src.auth.decorators import get_current_user_optional
    
    user = await get_current_user_optional(request, db)
    
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CaseyOS - Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    <style>
        /* Mobile menu styles */
        .mobile-menu {{
            display: none;
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.5);
            z-index: 100;
        }}
        .mobile-menu.open {{
            display: flex;
        }}
        .mobile-menu-content {{
            background: white;
            width: 280px;
            height: 100%;
            padding: 1.5rem;
            animation: slideIn 0.2s ease;
        }}
        @keyframes slideIn {{
            from {{ transform: translateX(-100%); }}
            to {{ transform: translateX(0); }}
        }}
        .hamburger {{
            display: none;
            background: none;
            border: none;
            font-size: 1.5rem;
            cursor: pointer;
            padding: 0.5rem;
        }}
        @media (max-width: 768px) {{
            .hamburger {{
                display: block;
            }}
        }}
    </style>
</head>
<body class="bg-gray-100 min-h-screen">
    <!-- Mobile Menu Overlay -->
    <div class="mobile-menu" id="mobile-menu" onclick="closeMobileMenu(event)">
        <div class="mobile-menu-content" onclick="event.stopPropagation()">
            <div class="flex justify-between items-center mb-6">
                <span class="text-xl font-bold">🎯 CaseyOS</span>
                <button onclick="toggleMobileMenu()" class="text-2xl">&times;</button>
            </div>
            <nav class="flex flex-col space-y-4">
                <a href="/dashboard" class="text-purple-600 font-medium py-2">Today's Moves</a>
                <a href="/static/command-queue.html" class="text-gray-600 py-2">Command Queue</a>
                <a href="/dashboard/signals" class="text-gray-600 py-2">Signals</a>
                <a href="/dashboard/voice" class="text-gray-600 py-2">Voice</a>
                <a href="/dashboard/settings" class="text-gray-600 py-2">Settings</a>
                <hr class="my-2">
                <a href="/logout" class="text-red-500 py-2">Logout</a>
            </nav>
        </div>
    </div>

    <!-- Top Nav -->
    <nav class="bg-white shadow-sm border-b sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-4 py-3 flex justify-between items-center">
            <div class="flex items-center space-x-4">
                <button class="hamburger" onclick="toggleMobileMenu()">☰</button>
                <a href="/dashboard" class="text-xl font-bold text-gray-800">🎯 CaseyOS</a>
                <div class="hidden md:flex items-center space-x-6 ml-4">
                    <a href="/dashboard" class="text-purple-600 font-medium text-sm border-b-2 border-purple-600 pb-1">Today's Moves</a>
                    <a href="/static/command-queue.html" class="text-gray-600 hover:text-gray-800 text-sm">Queue</a>
                    <a href="/dashboard/signals" class="text-gray-600 hover:text-gray-800 text-sm">Signals</a>
                    <a href="/dashboard/voice" class="text-gray-600 hover:text-gray-800 text-sm">Voice</a>
                    <a href="/dashboard/settings" class="text-gray-600 hover:text-gray-800 text-sm">Settings</a>
                </div>
            </div>
            <div class="flex items-center space-x-4">
                <div class="flex items-center space-x-2">
                    <img src="{user.picture or 'https://ui-avatars.com/api/?name=' + (user.name or user.email)}" 
                         class="w-8 h-8 rounded-full" alt="Profile">
                    <span class="text-sm text-gray-700 hidden md:inline">{user.name or user.email}</span>
                </div>
                <a href="/logout" class="text-gray-500 hover:text-gray-700 text-sm hidden md:inline">Logout</a>
            </div>
        </div>
    </nav>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto px-4 py-8">
        <!-- Welcome Banner -->
        <div class="bg-gradient-to-r from-purple-600 to-indigo-600 rounded-lg shadow-lg p-6 mb-8 text-white">
            <h1 class="text-2xl font-bold mb-2">Good {_get_greeting()}, {(user.name or user.email).split()[0]}! 👋</h1>
            <p class="text-purple-100">Here's what needs your attention today.</p>
        </div>

        <!-- Stats Cards -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            <div class="bg-white rounded-lg shadow p-6">
                <div class="text-sm text-gray-500 mb-1">Today's Moves</div>
                <div class="text-3xl font-bold text-purple-600" id="moves-count">0</div>
                <div class="text-xs text-gray-400 mt-1">Pending actions</div>
            </div>
            <div class="bg-white rounded-lg shadow p-6">
                <div class="text-sm text-gray-500 mb-1">Signals</div>
                <div class="text-3xl font-bold text-blue-600" id="signals-count">0</div>
                <div class="text-xs text-gray-400 mt-1">New this week</div>
            </div>
            <div class="bg-white rounded-lg shadow p-6">
                <div class="text-sm text-gray-500 mb-1">Completed</div>
                <div class="text-3xl font-bold text-green-600" id="completed-count">0</div>
                <div class="text-xs text-gray-400 mt-1">This week</div>
            </div>
            <div class="bg-white rounded-lg shadow p-6">
                <div class="text-sm text-gray-500 mb-1">APS Score</div>
                <div class="text-3xl font-bold text-orange-600" id="aps-score">--</div>
                <div class="text-xs text-gray-400 mt-1">Avg priority</div>
            </div>
        </div>

        <!-- Today's Moves -->
        <div class="bg-white rounded-lg shadow">
            <div class="px-6 py-4 border-b flex justify-between items-center">
                <h2 class="text-lg font-semibold text-gray-800">Today's Moves</h2>
                <button onclick="refreshMoves()" class="text-sm text-purple-600 hover:text-purple-800 flex items-center gap-1">
                    <span>↻</span> Refresh
                </button>
            </div>
            <div id="moves-list" class="divide-y">
                <!-- Placeholder -->
                <div class="p-6 text-center text-gray-500">
                    <p class="mb-2">No moves yet.</p>
                    <p class="text-sm">Connect HubSpot to start ingesting signals.</p>
                </div>
            </div>
        </div>
    </main>

    <!-- Footer -->
    <footer class="max-w-7xl mx-auto px-4 py-8 text-center text-gray-400 text-sm">
        CaseyOS v1.0 · Sprint 1 Complete
    </footer>

    <script>
        async function refreshMoves() {{
            document.getElementById('moves-list').innerHTML = '<div class="p-4 text-center text-gray-400">Loading...</div>';
            await loadMoves();
        }}

        async function loadMoves() {{
            try {{
                const res = await fetch('/api/command-queue/today?limit=10');
                const data = await res.json();
                
                document.getElementById('moves-count').textContent = data.total || 0;
                
                const movesList = document.getElementById('moves-list');
                
                if (!data.items || data.items.length === 0) {{
                    movesList.innerHTML = `
                        <div class="p-6 text-center text-gray-500">
                            <p class="mb-2">✅ All caught up!</p>
                            <p class="text-sm">No pending moves. Check back later.</p>
                        </div>
                    `;
                    return;
                }}
                
                movesList.innerHTML = data.items.map(item => `
                    <div class="p-4 hover:bg-gray-50 flex items-center justify-between">
                        <div class="flex items-center gap-4">
                            <div class="w-10 h-10 rounded-full flex items-center justify-center text-white text-sm font-bold"
                                 style="background: ${{item.priority_score >= 0.8 ? '#ef4444' : item.priority_score >= 0.6 ? '#f59e0b' : '#10b981'}}">
                                ${{Math.round(item.priority_score * 100)}}
                            </div>
                            <div>
                                <div class="font-medium text-gray-800">${{item.title}}</div>
                                <div class="text-sm text-gray-500">
                                    <span class="px-2 py-0.5 bg-purple-100 text-purple-700 rounded text-xs">${{item.action_type}}</span>
                                    ${{item.due_by ? ' · Due ' + new Date(item.due_by).toLocaleDateString() : ''}}
                                </div>
                            </div>
                        </div>
                        <div class="flex gap-2">
                            <button onclick="acceptItem('${{item.id}}')" 
                                    class="px-3 py-1.5 bg-green-500 text-white text-sm rounded hover:bg-green-600">
                                ✓ Accept
                            </button>
                            <button onclick="skipItem('${{item.id}}')"
                                    class="px-3 py-1.5 bg-gray-200 text-gray-700 text-sm rounded hover:bg-gray-300">
                                Skip
                            </button>
                        </div>
                    </div>
                `).join('');
                
                // Calculate avg APS
                if (data.items.length > 0) {{
                    const avgAps = data.items.reduce((sum, i) => sum + i.priority_score, 0) / data.items.length;
                    document.getElementById('aps-score').textContent = Math.round(avgAps * 100);
                }}
            }} catch (err) {{
                console.error('Failed to load moves:', err);
                document.getElementById('moves-list').innerHTML = '<div class="p-4 text-center text-red-500">Failed to load</div>';
            }}
        }}

        async function loadStats() {{
            try {{
                const [signalsRes, outcomesRes] = await Promise.all([
                    fetch('/api/signals?limit=1'),
                    fetch('/api/outcomes/stats?days=7')
                ]);
                
                if (signalsRes.ok) {{
                    const signalsData = await signalsRes.json();
                    document.getElementById('signals-count').textContent = signalsData.total || 0;
                }}
                
                if (outcomesRes.ok) {{
                    const outcomesData = await outcomesRes.json();
                    document.getElementById('completed-count').textContent = outcomesData.positive_outcomes || 0;
                }}
            }} catch (err) {{
                console.error('Failed to load stats:', err);
            }}
        }}

        async function acceptItem(id) {{
            try {{
                await fetch(`/api/command-queue/${{id}}/accept`, {{ method: 'POST' }});
                await loadMoves();
            }} catch (err) {{
                console.error('Failed to accept item:', err);
            }}
        }}

        async function skipItem(id) {{
            try {{
                await fetch(`/api/command-queue/${{id}}/dismiss`, {{ method: 'POST' }});
                await loadMoves();
            }} catch (err) {{
                console.error('Failed to skip item:', err);
            }}
        }}

        // Mobile menu functions
        function toggleMobileMenu() {{
            document.getElementById('mobile-menu').classList.toggle('open');
        }}
        
        function closeMobileMenu(event) {{
            if (event.target.id === 'mobile-menu') {{
                document.getElementById('mobile-menu').classList.remove('open');
            }}
        }}

        // Initial load
        loadMoves();
        loadStats();
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html)


def _get_greeting() -> str:
    """Get time-based greeting."""
    hour = datetime.utcnow().hour
    if hour < 12:
        return "morning"
    elif hour < 17:
        return "afternoon"
    else:
        return "evening"


@router.get("/todays-moves")
async def todays_moves(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Serve the Today's Moves page - the core command queue UI."""
    from src.auth.decorators import get_current_user_optional
    
    user = await get_current_user_optional(request, db)
    
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    # Serve the static HTML file
    import os
    static_path = os.path.join(os.path.dirname(__file__), "..", "static", "command-queue.html")
    
    try:
        with open(static_path, "r") as f:
            html = f.read()
        return HTMLResponse(content=html)
    except FileNotFoundError:
        logger.error(f"command-queue.html not found at {static_path}")
        return RedirectResponse(url="/dashboard", status_code=302)


@router.get("/queue/{item_id}")
async def queue_item_detail(
    item_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Serve the Queue Item Detail page."""
    from src.auth.decorators import get_current_user_optional
    
    user = await get_current_user_optional(request, db)
    
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    # Serve the static HTML file
    import os
    static_path = os.path.join(os.path.dirname(__file__), "..", "static", "queue-item-detail.html")
    
    try:
        with open(static_path, "r") as f:
            html = f.read()
        return HTMLResponse(content=html)
    except FileNotFoundError:
        logger.error(f"queue-item-detail.html not found at {static_path}")
        return RedirectResponse(url="/todays-moves", status_code=302)
