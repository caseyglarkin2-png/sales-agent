# Google OAuth Setup for Sales Agent

## Overview

The sales agent needs access to Google APIs for:
- **Gmail** — Read email threads, send replies
- **Google Drive** — Find and read proposal documents
- **Google Calendar** — Check availability for meeting scheduling

This guide walks through the setup for local development and Codespaces.

---

## Quick Start

### 1. Setup Google OAuth Credentials

Visit [Google Cloud Console](https://console.cloud.google.com/):

```
1. Create a new project:
   - Project name: "Sales Agent Local"
   - Click CREATE

2. Enable APIs:
   Go to: APIs & Services → Enabled APIs & services
   - Click "+ ENABLE APIS AND SERVICES"
   - Search & Enable: "Gmail API"
   - Search & Enable: "Google Drive API"
   - Search & Enable: "Google Calendar API"

3. Create OAuth 2.0 Credentials:
   - Go to: APIs & Services → Credentials
   - Click: + CREATE CREDENTIALS → OAuth 2.0 Client ID
   - Application type: Desktop application
   - Name: "Sales Agent CLI"
   - Click CREATE

4. Configure Consent Screen:
   - Go to: APIs & Services → OAuth consent screen
   - User type: External
   - Required scopes: Gmail, Drive, Calendar
   - Test users: Add your email

5. Download Credentials:
   - Go to: APIs & Services → Credentials
   - Under "OAuth 2.0 Client IDs", click your app
   - Click "DOWNLOAD JSON" button ⬇️
   - Save file as: client_secret.json (project root)
```

### 2. Run Authorization

```bash
# Interactive setup (opens browser)
make auth-google

# Or with Python directly
python -m src.commands.auth_google
```

### 3. Grant Permissions

A browser window opens. You'll see:
- "Sign in with Google" → Enter your email
- "Sales Agent wants to access your Google Account" → Click "Advanced"
- "Go to Sales Agent (unsafe)" → Click the link
- Permission requests → Click "Allow"

```
✓ All authorizations successful!

📁 Token saved to: .tokens/google_tokens.json
   (This file is in .gitignore - never commit it)
```

---

## Commands

### Full Setup (All Services)
```bash
make auth-google
# or
python -m src.commands.auth_google
```

Grants access to:
- Gmail (read & send emails)
- Google Drive (read files)
- Google Calendar (read calendar)

### Gmail Only
```bash
python -m src.commands.auth_google --gmail
```

### Google Drive Only
```bash
python -m src.commands.auth_google --drive
```

### Google Calendar Only
```bash
python -m src.commands.auth_google --calendar
```

### Show Token Info
```bash
python -m src.commands.auth_google --info

# Output:
# Status: VALID
# Client ID: xxx.apps.googleusercontent.com
# Expires At: 2026-02-19T01:31:49
# Time Until Expiry: 720.5 hours
# Scopes: 7 service(s)
#   - Gmail (read/write)
#   - Drive (read-only)
#   - Calendar (read-only)
```

### Revoke Access
```bash
python -m src.commands.auth_google --revoke

# Deletes: .tokens/google_tokens.json
# Re-run auth-google to set up again
```

---

## How It Works

### Token Storage

Tokens are cached in `.tokens/google_tokens.json`:

```
.tokens/
└── google_tokens.json          # OAuth token (never commit)
    - Access token
    - Refresh token
    - Expiry timestamp
    - Scopes
    - Client ID
```

**Security:**
- File permissions: `0o600` (owner read/write only)
- In `.gitignore` (never committed)
- Refresh token stored securely
- Can be revoked anytime

### Token Lifecycle

```
Authorization Request
  ↓
Browser opens (localhost:8888)
  ↓
User logs in & grants permission
  ↓
Token received & cached to disk
  ↓
Token used for API calls (Gmail, Drive, Calendar)
  ↓
[Expires after 1 hour]
  ↓
Automatic refresh (using refresh token)
  ↓
Updated token cached to disk
```

### Automatic Refresh

Tokens refresh automatically when:
- About to expire (< 5 minutes remaining)
- Making API calls with expired token
- Before requests using `refresh_if_needed()`

---

## Usage in Code

### Get Credentials
```python
from src.auth.google_oauth import get_oauth_manager

manager = get_oauth_manager()

# Get valid credentials (auto-refresh if needed)
credentials = manager.get_credentials()

# Or get credentials for specific scopes
from src.auth.google_oauth import GMAIL_SCOPES
credentials = manager.get_credentials(GMAIL_SCOPES)
```

### Use with Google Client Library
```python
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

manager = get_oauth_manager()
creds = manager.get_credentials()

# Build Gmail service
gmail_service = build("gmail", "v1", credentials=creds)
threads = gmail_service.users().threads().list(userId="me").execute()

# Build Drive service
drive_service = build("drive", "v3", credentials=creds)
files = drive_service.files().list(pageSize=10).execute()

# Build Calendar service
calendar_service = build("calendar", "v3", credentials=creds)
events = calendar_service.events().list(calendarId="primary").execute()
```

### Check Token Status
```python
manager = get_oauth_manager()
info = manager.get_token_info()

if info["status"] == "valid":
    print(f"Token valid for {info['time_until_expiry'] / 3600:.1f} more hours")
elif info["status"] == "expired":
    print("Token expired, re-authorize with: make auth-google")
else:
    print("No token cached")
```

---

## Troubleshooting

### "client_secret.json not found"

**Cause:** You haven't downloaded credentials from Google Cloud Console.

**Fix:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create OAuth 2.0 Desktop credentials
3. Download JSON to `client_secret.json` (project root)
4. Re-run: `make auth-google`

---

### "This app isn't verified"

**Cause:** Google hasn't verified your app yet (expected for personal/dev apps).

**Fix:**
1. Click "Advanced" at bottom of warning
2. Click "Go to Sales Agent (unsafe)"
3. Click "Allow" on permissions

This is safe—you're authenticating your own credentials.

---

### "Token expired" when running code

**Cause:** Your cached token is older than 1 hour.

**Fix:**
Tokens auto-refresh, but if you see this:
```bash
python -m src.commands.auth_google --revoke
make auth-google
```

---

### "Port 8888 already in use"

**Cause:** Another process is using the redirect URI port.

**Fix:**
- Stop other services on port 8888
- Or use a different port:
  ```bash
  GOOGLE_REDIRECT_PORT=8889 make auth-google
  ```

---

### "scopes don't match"

**Cause:** You asked for different scopes than what's cached.

**Fix:**
Revoke and re-authorize with all scopes:
```bash
python -m src.commands.auth_google --revoke
make auth-google  # Full setup with all scopes
```

---

## Codespaces Setup

In GitHub Codespaces, OAuth redirect needs special handling:

### Method 1: Port Forwarding (Recommended)

```bash
# Run auth-google
make auth-google

# Codespaces will prompt:
# "Open http://localhost:8888 in browser?"
# → Click "Open in Browser"

# Browser opens (authenticated to Codespaces)
# Grant permissions → Token saved
```

### Method 2: Public Port

Set `GOOGLE_REDIRECT_URI` to public port:

```bash
# In Codespaces terminal
GOOGLE_REDIRECT_URI="https://your-codespace-url:8888/" make auth-google
```

### Codespaces .env

Add to `.env` in Codespaces:

```bash
# .env (only in Codespaces)
GOOGLE_CREDENTIALS_FILE=client_secret.json
GOOGLE_TOKEN_CACHE_DIR=.tokens

# Optional: For public Codespaces URL
# GOOGLE_REDIRECT_URI=https://your-codespace-url:8888/
```

---

## Production Deployment

For production (e.g., Cloud Run), use **Service Account** credentials instead:

```python
from google.oauth2.service_account import Credentials

creds = Credentials.from_service_account_file(
    "service_account.json",
    scopes=["https://www.googleapis.com/auth/gmail.readonly", ...]
)
```

Store service account JSON in Secret Manager:
```bash
gcloud secrets create google-service-account \
  --data-file=service_account.json

# In Cloud Run, inject as environment variable
--set-secrets=GOOGLE_SERVICE_ACCOUNT_JSON=google-service-account:latest
```

---

## Architecture

```
┌─────────────────────────────────┐
│   Sales Agent Application       │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│   GoogleOAuthManager            │
│  - get_credentials()            │
│  - authorize_user()             │
│  - refresh_if_needed()          │
│  - revoke()                     │
└──────────────┬──────────────────┘
               │
    ┌──────────┼──────────┐
    ▼          ▼          ▼
┌────────┐ ┌────────┐ ┌──────────┐
│ Gmail  │ │ Drive  │ │ Calendar │
│ API    │ │ API    │ │ API      │
└────────┘ └────────┘ └──────────┘
    ▲          ▲          ▲
    └──────────┼──────────┘
               │
        ┌──────┴──────┐
        │ OAuth 2.0   │
        │ Access Token│
        │ (in memory) │
        │             │
        │ Refresh     │
        │ Token       │
        │ (.tokens/)  │
        └─────────────┘
```

---

## Security Best Practices

1. **Never commit tokens** — Always in `.gitignore`
2. **Secure file permissions** — `0o600` (owner only)
3. **Minimize scopes** — Request only needed permissions
4. **Use refresh tokens** — Auto-rotate long-lived tokens
5. **Revoke unused access** — `make auth-google --revoke`
6. **Separate credentials** — Dev vs. production accounts
7. **Monitor token usage** — Check [Google Security Checkup](https://myaccount.google.com/security-checkup)

---

## Next Steps

After OAuth setup:

1. Test email access:
   ```bash
   python -c "
   from src.auth.google_oauth import get_oauth_manager
   from googleapiclient.discovery import build
   
   creds = get_oauth_manager().get_credentials()
   service = build('gmail', 'v1', credentials=creds)
   print(service.users().getProfile(userId='me').execute())
   "
   ```

2. Run smoke test:
   ```bash
   make smoke-formlead
   ```

3. Try demo endpoints:
   ```bash
   curl http://localhost:8000/api/agents/demo/prospecting
   ```

---

## Reference

- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [Gmail API Scopes](https://developers.google.com/gmail/api/auth/scopes)
- [Google Drive API Scopes](https://developers.google.com/drive/api/guides/about-auth)
- [Google Calendar API Scopes](https://developers.google.com/calendar/api/guides/auth)
- [Service Account Setup](https://developers.google.com/identity/protocols/oauth2/service-account)
