"""Twitter OAuth Routes - Authenticate users for personal feed access.

Implements OAuth 1.0a for Twitter/X to enable:
- Personal home timeline reading
- Notifications access
- DM monitoring (with permission)
- User context operations

Flow:
1. User hits /auth/twitter/login
2. We get request token from Twitter
3. Redirect user to Twitter to authorize
4. Twitter redirects back with oauth_verifier
5. We exchange for access token
6. Store tokens securely for future API calls
"""

import os
import hmac
import hashlib
import base64
import time
import urllib.parse
from typing import Optional
import secrets

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
import httpx

from src.logger import get_logger
from src.config import get_settings

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter(prefix="/auth/twitter", tags=["Twitter OAuth"])

# Twitter OAuth endpoints
TWITTER_REQUEST_TOKEN_URL = "https://api.twitter.com/oauth/request_token"
TWITTER_AUTHORIZE_URL = "https://api.twitter.com/oauth/authorize"
TWITTER_ACCESS_TOKEN_URL = "https://api.twitter.com/oauth/access_token"

# In-memory storage for OAuth state (use Redis in production)
_oauth_tokens: dict = {}
_user_tokens: dict = {}


def _generate_oauth_signature(
    method: str,
    url: str,
    params: dict,
    consumer_secret: str,
    token_secret: str = ""
) -> str:
    """Generate OAuth 1.0a signature.
    
    Args:
        method: HTTP method (GET, POST)
        url: Full URL (without query string)
        params: All OAuth params + request params
        consumer_secret: API Secret Key
        token_secret: OAuth token secret (empty for request token)
    
    Returns:
        Base64 encoded HMAC-SHA1 signature
    """
    # Sort and encode params
    sorted_params = sorted(params.items())
    param_string = urllib.parse.urlencode(sorted_params, safe="")
    
    # Create signature base string
    signature_base = "&".join([
        method.upper(),
        urllib.parse.quote(url, safe=""),
        urllib.parse.quote(param_string, safe="")
    ])
    
    # Create signing key
    signing_key = "&".join([
        urllib.parse.quote(consumer_secret, safe=""),
        urllib.parse.quote(token_secret, safe="")
    ])
    
    # Generate signature
    signature = hmac.new(
        signing_key.encode(),
        signature_base.encode(),
        hashlib.sha1
    ).digest()
    
    return base64.b64encode(signature).decode()


def _generate_oauth_params(
    consumer_key: str,
    token: Optional[str] = None,
    callback_url: Optional[str] = None,
    verifier: Optional[str] = None
) -> dict:
    """Generate base OAuth 1.0a parameters."""
    params = {
        "oauth_consumer_key": consumer_key,
        "oauth_nonce": secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_version": "1.0",
    }
    
    if token:
        params["oauth_token"] = token
    if callback_url:
        params["oauth_callback"] = callback_url
    if verifier:
        params["oauth_verifier"] = verifier
    
    return params


def _build_auth_header(params: dict) -> str:
    """Build OAuth Authorization header from params."""
    auth_parts = [
        f'{urllib.parse.quote(k, safe="")}="{urllib.parse.quote(v, safe="")}"'
        for k, v in sorted(params.items())
        if k.startswith("oauth_")
    ]
    return "OAuth " + ", ".join(auth_parts)


@router.get("/login")
async def twitter_login(request: Request):
    """Initiate Twitter OAuth login flow.
    
    Redirects user to Twitter to authorize CaseyOS.
    
    Returns:
        RedirectResponse to Twitter authorization page
    """
    consumer_key = os.getenv("TWITTER_CONSUMER_KEY") or os.getenv("TWITTER_API_KEY")
    consumer_secret = os.getenv("TWITTER_CONSUMER_SECRET") or os.getenv("TWITTER_API_SECRET")
    
    if not consumer_key or not consumer_secret:
        raise HTTPException(
            status_code=500,
            detail="Twitter OAuth not configured. Set TWITTER_CONSUMER_KEY and TWITTER_CONSUMER_SECRET"
        )
    
    # Build callback URL
    callback_url = str(request.url_for("twitter_callback"))
    # Fix for Railway/production
    if "localhost" not in callback_url and not callback_url.startswith("https"):
        callback_url = callback_url.replace("http://", "https://")
    
    # Generate OAuth parameters
    oauth_params = _generate_oauth_params(
        consumer_key=consumer_key,
        callback_url=callback_url
    )
    
    # Generate signature
    signature = _generate_oauth_signature(
        method="POST",
        url=TWITTER_REQUEST_TOKEN_URL,
        params=oauth_params,
        consumer_secret=consumer_secret
    )
    oauth_params["oauth_signature"] = signature
    
    # Make request for request token
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                TWITTER_REQUEST_TOKEN_URL,
                headers={"Authorization": _build_auth_header(oauth_params)}
            )
            response.raise_for_status()
            
            # Parse response
            token_data = dict(urllib.parse.parse_qsl(response.text))
            oauth_token = token_data.get("oauth_token")
            oauth_token_secret = token_data.get("oauth_token_secret")
            
            if not oauth_token:
                raise HTTPException(500, "Failed to get request token from Twitter")
            
            # Store token secret for callback
            _oauth_tokens[oauth_token] = oauth_token_secret
            
            # Redirect to Twitter for authorization
            auth_url = f"{TWITTER_AUTHORIZE_URL}?oauth_token={oauth_token}"
            logger.info(f"Redirecting to Twitter for OAuth: {auth_url[:50]}...")
            
            return RedirectResponse(url=auth_url)
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Twitter OAuth error: {e.response.text}")
            raise HTTPException(500, f"Twitter OAuth failed: {e.response.text}")
        except Exception as e:
            logger.error(f"Twitter OAuth error: {e}")
            raise HTTPException(500, f"Twitter OAuth failed: {str(e)}")


@router.get("/callback")
async def twitter_callback(oauth_token: str, oauth_verifier: str):
    """Handle Twitter OAuth callback.
    
    Exchanges request token for access token and stores it.
    
    Args:
        oauth_token: Request token from Twitter
        oauth_verifier: Verification code from user authorization
    
    Returns:
        Success message with user info
    """
    consumer_key = os.getenv("TWITTER_CONSUMER_KEY") or os.getenv("TWITTER_API_KEY")
    consumer_secret = os.getenv("TWITTER_CONSUMER_SECRET") or os.getenv("TWITTER_API_SECRET")
    
    # Get stored token secret
    token_secret = _oauth_tokens.pop(oauth_token, "")
    if not token_secret:
        raise HTTPException(400, "Invalid or expired OAuth token")
    
    # Generate OAuth params for access token request
    oauth_params = _generate_oauth_params(
        consumer_key=consumer_key,
        token=oauth_token,
        verifier=oauth_verifier
    )
    
    # Generate signature
    signature = _generate_oauth_signature(
        method="POST",
        url=TWITTER_ACCESS_TOKEN_URL,
        params=oauth_params,
        consumer_secret=consumer_secret,
        token_secret=token_secret
    )
    oauth_params["oauth_signature"] = signature
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                TWITTER_ACCESS_TOKEN_URL,
                headers={"Authorization": _build_auth_header(oauth_params)}
            )
            response.raise_for_status()
            
            # Parse access token response
            token_data = dict(urllib.parse.parse_qsl(response.text))
            access_token = token_data.get("oauth_token")
            access_token_secret = token_data.get("oauth_token_secret")
            user_id = token_data.get("user_id")
            screen_name = token_data.get("screen_name")
            
            if not access_token:
                raise HTTPException(500, "Failed to get access token from Twitter")
            
            # Store user tokens (in production, encrypt and store in database)
            _user_tokens[user_id] = {
                "access_token": access_token,
                "access_token_secret": access_token_secret,
                "screen_name": screen_name,
                "created_at": time.time()
            }
            
            logger.info(f"Twitter OAuth successful for @{screen_name} (user_id: {user_id})")
            
            return {
                "status": "success",
                "message": f"Successfully authenticated as @{screen_name}",
                "user_id": user_id,
                "screen_name": screen_name
            }
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Twitter access token error: {e.response.text}")
            raise HTTPException(500, f"Twitter OAuth failed: {e.response.text}")


@router.get("/status")
async def twitter_oauth_status():
    """Check Twitter OAuth configuration status.
    
    Returns:
        Configuration status and authenticated users
    """
    consumer_key = os.getenv("TWITTER_CONSUMER_KEY") or os.getenv("TWITTER_API_KEY")
    bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
    
    authenticated_users = [
        {"user_id": uid, "screen_name": data.get("screen_name")}
        for uid, data in _user_tokens.items()
    ]
    
    return {
        "oauth_configured": bool(consumer_key),
        "bearer_token_configured": bool(bearer_token),
        "authenticated_users": authenticated_users,
        "capabilities": {
            "public_search": bool(bearer_token),
            "user_timeline": bool(bearer_token),
            "home_timeline": len(authenticated_users) > 0,
            "notifications": len(authenticated_users) > 0,
        }
    }


@router.get("/user/{user_id}/home_timeline")
async def get_home_timeline(user_id: str, count: int = 20):
    """Get authenticated user's home timeline.
    
    Requires user to have completed OAuth flow.
    
    Args:
        user_id: Twitter user ID
        count: Number of tweets to fetch (max 200)
    
    Returns:
        User's home timeline tweets
    """
    if user_id not in _user_tokens:
        raise HTTPException(
            401, 
            "User not authenticated. Complete OAuth flow at /auth/twitter/login"
        )
    
    consumer_key = os.getenv("TWITTER_CONSUMER_KEY") or os.getenv("TWITTER_API_KEY")
    consumer_secret = os.getenv("TWITTER_CONSUMER_SECRET") or os.getenv("TWITTER_API_SECRET")
    user_token = _user_tokens[user_id]
    
    # Twitter API v2 home timeline endpoint
    url = "https://api.twitter.com/2/users/{}/timelines/reverse_chronological".format(user_id)
    
    oauth_params = _generate_oauth_params(
        consumer_key=consumer_key,
        token=user_token["access_token"]
    )
    
    # Add query params to signature
    query_params = {
        "max_results": min(count, 100),
        "tweet.fields": "created_at,public_metrics,entities,author_id",
        "expansions": "author_id",
        "user.fields": "username,name",
    }
    
    all_params = {**oauth_params, **query_params}
    
    signature = _generate_oauth_signature(
        method="GET",
        url=url,
        params=all_params,
        consumer_secret=consumer_secret,
        token_secret=user_token["access_token_secret"]
    )
    oauth_params["oauth_signature"] = signature
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                url,
                headers={"Authorization": _build_auth_header(oauth_params)},
                params=query_params
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Home timeline error: {e.response.text}")
            raise HTTPException(e.response.status_code, e.response.text)


def get_user_tokens(user_id: str) -> Optional[dict]:
    """Get stored OAuth tokens for a user.
    
    Used by other parts of the app to make authenticated requests.
    
    Args:
        user_id: Twitter user ID
    
    Returns:
        Token dict or None if not authenticated
    """
    return _user_tokens.get(user_id)


def set_user_tokens(user_id: str, tokens: dict):
    """Store OAuth tokens for a user.
    
    Used when loading tokens from database.
    
    Args:
        user_id: Twitter user ID
        tokens: Dict with access_token, access_token_secret, screen_name
    """
    _user_tokens[user_id] = tokens
