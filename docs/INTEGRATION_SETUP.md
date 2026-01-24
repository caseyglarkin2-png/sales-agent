# CaseyOS Integration Setup Guide

**Last Updated:** January 24, 2026

This guide covers setting up production OAuth for Google Workspace (Gmail/Calendar) and AI providers (OpenAI + Gemini).

---

## Quick Environment Variables

Add these to your Railway environment:

```bash
# Google OAuth (Gmail, Calendar, Drive)
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=https://web-production-a6ccf.up.railway.app/auth/callback

# HubSpot CRM
HUBSPOT_API_KEY=pat-na1-xxxxxxxx  # Private App token

# AI Providers
OPENAI_API_KEY=sk-xxxxxxxx  # GPT-4 for fallback
GEMINI_API_KEY=xxxxxxxx  # Google AI (primary)
LLM_PROVIDER=gemini  # or "openai"
```

---

## Google Workspace OAuth Setup

### Step 1: Create OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Select or create a project
3. Navigate to **APIs & Services** → **Credentials**
4. Click **Create Credentials** → **OAuth client ID**
5. Choose **Web application**
6. Add authorized redirect URI:
   ```
   https://web-production-a6ccf.up.railway.app/auth/callback
   ```
7. Copy the **Client ID** and **Client Secret**

### Step 2: Enable Required APIs

Enable these APIs in your Google Cloud project:

- Gmail API
- Google Calendar API  
- Google Drive API
- Google Docs API

### Step 3: Configure Consent Screen

1. Go to **APIs & Services** → **OAuth consent screen**
2. Select **Internal** (for Google Workspace organizations)
3. Fill in app details:
   - App name: `CaseyOS`
   - User support email: your-email@your-domain.com
   - Developer contact: your-email@your-domain.com

4. Add scopes:
   ```
   openid
   email
   profile
   https://www.googleapis.com/auth/gmail.send
   https://www.googleapis.com/auth/gmail.compose  
   https://www.googleapis.com/auth/gmail.readonly
   https://www.googleapis.com/auth/calendar
   https://www.googleapis.com/auth/calendar.events
   ```

### Step 4: Set Environment Variables

In Railway:
```bash
GOOGLE_CLIENT_ID=123456789.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxxxxxxx
GOOGLE_REDIRECT_URI=https://web-production-a6ccf.up.railway.app/auth/callback
```

### Step 5: Test Login

1. Go to https://web-production-a6ccf.up.railway.app/login
2. Click "Sign in with Google"
3. Complete OAuth flow
4. You should be redirected to `/dashboard`

---

## Gemini AI Setup (Google AI Studio)

### Step 1: Get API Key

1. Go to [Google AI Studio](https://aistudio.google.com)
2. Click **Get API key** in the left sidebar
3. Click **Create API key**
4. Copy the key

### Step 2: Set Environment Variables

```bash
GEMINI_API_KEY=AIzaSyxxxxxxxxxxxxxxxxxx
LLM_PROVIDER=gemini  # Use Gemini as primary
GEMINI_MODEL=gemini-2.0-flash-exp  # Default model
```

### Step 3: Test Gemini

```bash
# Check LLM health
curl https://web-production-a6ccf.up.railway.app/api/llm/health

# List available providers
curl https://web-production-a6ccf.up.railway.app/api/llm/providers

# Test generation
curl -X POST https://web-production-a6ccf.up.railway.app/api/llm/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is CaseyOS?", "provider": "gemini"}'

# Deep research with grounding
curl -X POST https://web-production-a6ccf.up.railway.app/api/llm/research \
  -H "Content-Type: application/json" \
  -d '{"topic": "B2B sales automation trends 2026"}'

# Draft an email
curl -X POST https://web-production-a6ccf.up.railway.app/api/llm/draft-email \
  -H "Content-Type: application/json" \
  -d '{
    "recipient_name": "John",
    "recipient_company": "Acme Corp",
    "recipient_role": "VP Sales",
    "purpose": "Follow up on demo request"
  }'
```

### Available Gemini Models

| Model | Description | Use Case |
|-------|-------------|----------|
| `gemini-2.0-flash-exp` | Fast, multimodal | Default, most tasks |
| `gemini-1.5-pro` | High capability, 1M context | Complex analysis |
| `gemini-1.5-flash` | Fast and versatile | Quick tasks |
| `gemini-1.5-flash-8b` | Efficient | Summarization |
| `gemini-exp-1206` | Enhanced reasoning | Research |

### Gemini Features

1. **Deep Research** - Multi-step research with Google Search grounding
2. **Grounding** - Real-time web data for factual responses
3. **Long Context** - 1M token context window (Pro)
4. **Multimodal** - Image understanding (coming soon)

---

## HubSpot Integration

### Step 1: Create Private App

1. Go to HubSpot → Settings → Integrations → Private Apps
2. Click **Create a private app**
3. Name: `CaseyOS`
4. Add scopes:
   - `crm.objects.contacts.read`
   - `crm.objects.contacts.write`
   - `crm.objects.companies.read`
   - `crm.objects.companies.write`
   - `crm.objects.deals.read`
   - `crm.objects.deals.write`
   - `crm.schemas.contacts.read`
   - `crm.schemas.companies.read`
   - `crm.schemas.deals.read`

5. Click **Create app**
6. Copy the **Access token**

### Step 2: Set Environment Variable

```bash
HUBSPOT_API_KEY=pat-na1-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

### Step 3: Test Connection

```bash
# Check HubSpot signals endpoint
curl https://web-production-a6ccf.up.railway.app/api/hubspot/signals/status

# Manually poll for signals
curl -X POST https://web-production-a6ccf.up.railway.app/api/hubspot/signals/refresh
```

---

## Multi-Provider LLM Architecture

CaseyOS supports both OpenAI and Gemini with automatic failover:

```
┌─────────────────┐
│   LLMConnector  │
├─────────────────┤
│ Primary Provider │──▶ (based on LLM_PROVIDER env)
│                 │
│ ┌─────────────┐ │
│ │  OpenAI     │◀┼──▶ GPT-4-turbo-preview
│ └─────────────┘ │
│       ▲         │
│       │ failover│
│       ▼         │
│ ┌─────────────┐ │
│ │  Gemini     │◀┼──▶ gemini-2.0-flash-exp
│ └─────────────┘ │
└─────────────────┘
```

**Failover Behavior:**
- If primary provider fails, automatically tries secondary
- Both providers must have API keys configured for failover
- Errors are logged for monitoring

**Switch Providers:**
```bash
# Use Gemini as primary
LLM_PROVIDER=gemini

# Use OpenAI as primary
LLM_PROVIDER=openai
```

---

## Validation Checklist

### ✅ Google OAuth
- [ ] `GOOGLE_CLIENT_ID` is set
- [ ] `GOOGLE_CLIENT_SECRET` is set  
- [ ] `GOOGLE_REDIRECT_URI` matches Console
- [ ] OAuth consent screen configured
- [ ] Required APIs enabled
- [ ] Can complete login flow

### ✅ Gemini AI
- [ ] `GEMINI_API_KEY` is set
- [ ] `/api/llm/health` shows `gemini.status: healthy`
- [ ] `/api/llm/generate` returns text
- [ ] `/api/llm/research` returns grounded results

### ✅ HubSpot
- [ ] `HUBSPOT_API_KEY` is set
- [ ] Private app has required scopes
- [ ] `/api/hubspot/signals/status` returns 200

### ✅ OpenAI (Fallback)
- [ ] `OPENAI_API_KEY` is set (optional but recommended)
- [ ] `/api/llm/health` shows `openai.status: healthy`

---

## Troubleshooting

### "Google OAuth not configured"
- Check `GOOGLE_CLIENT_ID` is set in Railway
- Verify the value doesn't have quotes or spaces

### "redirect_uri_mismatch"  
- Ensure `GOOGLE_REDIRECT_URI` exactly matches Google Console
- Must be `https://` in production (not `http://`)

### "Gemini API key not configured"
- Set `GEMINI_API_KEY` in Railway environment
- Get key from https://aistudio.google.com

### "Failed to generate text"
- Check API key is valid
- Verify billing is enabled (for OpenAI)
- Check `/api/llm/health` for status

---

## Quick Test Commands

```bash
BASE=https://web-production-a6ccf.up.railway.app

# Test OAuth login page
curl -I $BASE/login

# Test LLM health
curl $BASE/api/llm/health

# Test Gemini generation
curl -X POST $BASE/api/llm/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello world", "provider": "gemini"}'

# Test deep research
curl -X POST $BASE/api/llm/research \
  -H "Content-Type: application/json" \
  -d '{"topic": "SaaS sales best practices"}'

# Test company analysis
curl -X POST "$BASE/api/llm/analyze-company?company_name=Stripe&domain=stripe.com"
```

---

**Ready to go!** Set the environment variables in Railway and deploy.
