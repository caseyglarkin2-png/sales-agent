# Twitter/X & Grok Integration Setup

**Date:** January 24, 2026  
**Author:** CaseyOS Development

This document covers the setup and configuration for Twitter/X API and xAI Grok integration in CaseyOS.

---

## Overview

CaseyOS integrates with:
1. **Twitter/X API v2** - For social monitoring, trend detection, and credible voice tracking
2. **xAI Grok** - For real-time market intelligence and social signal analysis

These integrations power:
- `MarketTrendMonitorAgent` - Tracks industry trends and thought leaders
- `SocialSignalProvider` - Ingests social signals into the Command Queue
- Real-time competitive intelligence

---

## Twitter/X API Setup

### Step 1: Create Developer Account

1. Go to [developer.x.com](https://developer.x.com)
2. Sign in with your X (Twitter) account
3. Apply for developer access (describe use case: "monitoring market trends and keywords via API")
4. Wait for approval (usually quick for non-commercial uses)

### Step 2: Create an App

1. Go to Developer Portal dashboard
2. Click "Create an App" or navigate to "Projects & Apps"
3. Fill in app details:
   - **Name:** "CaseyOS Social Monitor" (or similar)
   - **Description:** "Polling public posts on keywords like outreach, sales, market trends"
4. Agree to terms

### Step 3: Get API Keys

In your app's "Keys and Tokens" tab:
- **API Key** (Consumer Key)
- **API Secret Key** (Consumer Secret)
- Keep these secure!

### Step 4: Generate Bearer Token

**Option A: Via Developer Portal**
- Under "Keys and Tokens", click to generate Bearer Token
- Copy the long string (starts with "AAAAA...")

**Option B: Via API (programmatic)**
```bash
# Base64 encode your credentials
ENCODED=$(echo -n "$API_KEY:$API_SECRET" | base64)

# Get Bearer Token
curl -X POST https://api.twitter.com/oauth2/token \
  -H "Authorization: Basic $ENCODED" \
  -H "Content-Type: application/x-www-form-urlencoded;charset=UTF-8" \
  -d "grant_type=client_credentials"

# Response contains access_token - this is your Bearer Token
```

### Step 5: Set Environment Variable

```bash
# In Railway (production)
TWITTER_BEARER_TOKEN=AAAA...your_bearer_token...

# Locally (.env file)
export TWITTER_BEARER_TOKEN="your_token_here"
```

### API Limits (Free Tier)

| Endpoint | Limit |
|----------|-------|
| Search Tweets | 10 requests/min |
| User Timeline | 5 requests/min |
| User Lookup | 100 requests/24h |

For higher limits, consider Twitter API Pro tier.

---

## xAI Grok Setup

### Step 1: Create xAI Account

1. Go to [console.x.ai](https://console.x.ai)
2. Click "Sign in" and authorize with your X account

### Step 2: Generate API Key

1. Navigate to API section in dashboard
2. Click to generate a new API key
3. Copy securely (format: `xai-...`)

### Step 3: Set Environment Variable

```bash
# In Railway (production)
XAI_API_KEY=xai-your-api-key-here

# Locally (.env file)
export XAI_API_KEY="xai-your-api-key-here"
```

### Grok Models Available

| Model | Best For |
|-------|----------|
| `grok-4` | Most capable, real-time knowledge |
| `grok-3` | Fast, general purpose |

### API Pricing

Grok uses pay-as-you-go pricing. Check [docs.x.ai](https://docs.x.ai) for current rates.

---

## CaseyOS Integration

### Twitter Connector

**File:** `src/connectors/twitter.py`

```python
from src.connectors.twitter import get_twitter

twitter = get_twitter()

# Search recent tweets
tweets = await twitter.search_recent_tweets(
    query="Salesforce OR HubSpot",
    max_results=100,
    since_hours=24
)

# Monitor credible voices
results = await twitter.monitor_credible_voices(
    usernames=["jasonlk", "dharmesh", "paborito"],
    keywords=["sales", "CRM", "GTM"],
    since_hours=24
)

# Track keywords
tweets = await twitter.track_keywords(
    keywords=["B2B sales", "revenue operations"],
    min_followers=5000,
    since_hours=48
)
```

### Grok Connector

**File:** `src/connectors/grok.py`

```python
from src.connectors.grok import get_grok

grok = get_grok()

# Generate text
response = await grok.generate(
    prompt="Analyze Tesla's market position",
    temperature=0.7
)

# Market intelligence
intel = await grok.analyze_market_intel(
    topic="B2B sales automation",
    context={"industry": "SaaS", "target": "mid-market"}
)

# Competitive insights
insights = await grok.get_competitive_insights(
    company="Outreach",
    industry="Sales Engagement",
    competitors=["SalesLoft", "Gong", "Apollo"]
)

# Summarize social signals
summary = await grok.summarize_social_signals(
    signals=tweets,
    focus_topics=["sales automation", "AI in sales"]
)
```

### Market Trend Monitor Agent

**File:** `src/agents/market_trend_monitor.py`

```python
from src.agents.market_trend_monitor import MarketTrendMonitorAgent

agent = MarketTrendMonitorAgent()

# Get trends
result = await agent.execute({
    "action": "get_trends",
    "topic": "revenue operations",
    "timeframe": "24h"
})

# Monitor topic
result = await agent.execute({
    "action": "monitor_topic",
    "keywords": ["sales automation", "CRM"],
    "min_engagement": 100
})

# Get competitor intel
result = await agent.execute({
    "action": "get_competitor_intel",
    "company": "HubSpot",
    "industry": "CRM"
})
```

### Social Signal Provider

**File:** `src/signals/providers/social_signal.py`

```python
from src.signals.providers.social_signal import SocialSignalProvider

provider = SocialSignalProvider(
    keywords=["B2B sales", "sales automation"],
    thought_leaders=["jasonlk", "dharmesh"],
    min_engagement=50
)

# Poll for new signals
signals = await provider.poll()

# Each signal can be processed into Command Queue items
for signal in signals:
    # Signal has: id, source, type, data, timestamp
    print(f"New signal: {signal.type} from {signal.source}")
```

---

## Data Hygiene Agents

These agents help maintain data quality at scale (100k+ contacts).

### ContactValidationAgent
- Email format validation
- Phone number normalization
- Disposable email detection
- Job title standardization

### DuplicateWatcherAgent
- Fuzzy name matching
- Email/phone exact matching
- Merge recommendations

### DataDecayAgent
- Flags stale contacts (90/180/365 days)
- Recommends: ENRICH, ARCHIVE, VERIFY

### EnrichmentOrchestratorAgent
- Coordinates Clearbit/Apollo/ZoomInfo
- Tracks credit usage

### SyncHealthAgent
- Monitors HubSpot sync health
- Rate limit tracking
- Alert generation

**Files:** `src/agents/data_hygiene/`

---

## Personal Twitter Feed Integration (Future)

For personal feed access (home timeline, notifications, DMs), OAuth 2.0 with user context is required:

1. **App Permissions**: Request "Read" access
2. **User Auth Flow**: OAuth 2.0 PKCE or OAuth 1.0a
3. **User Access Tokens**: Generated per-user

This enables:
- Reading home timeline
- Notifications integration
- DM monitoring (with permission)

**Note:** This is a future enhancement. Current implementation focuses on public data via Bearer Token.

---

## Environment Variables Summary

| Variable | Description | Required |
|----------|-------------|----------|
| `TWITTER_BEARER_TOKEN` | Twitter API v2 Bearer Token | For social features |
| `XAI_API_KEY` | xAI Grok API Key | For Grok features |
| `GEMINI_API_KEY` | Google Gemini API Key | Optional fallback |
| `OPENAI_API_KEY` | OpenAI API Key | Required for core LLM |

---

## Troubleshooting

### Twitter 429 Rate Limit
- Reduce polling frequency
- Implement backoff logic (already built-in)
- Consider upgrading API tier

### Grok API Errors
- Verify XAI_API_KEY is set correctly
- Check API status at [status.x.ai](https://status.x.ai)
- Retry with exponential backoff (built-in)

### Missing Signals
- Check TWITTER_BEARER_TOKEN is valid
- Verify search query syntax
- Check API rate limit status

---

## Validation Commands

```bash
# Test Twitter connector
python -c "
import asyncio
from src.connectors.twitter import get_twitter
async def test():
    t = get_twitter()
    health = await t.health_check()
    print(health)
asyncio.run(test())
"

# Test Grok connector
python -c "
import asyncio
from src.connectors.grok import get_grok
async def test():
    g = get_grok()
    health = await g.health_check()
    print(health)
asyncio.run(test())
"

# Test Market Trend Agent
python -c "
import asyncio
from src.agents.market_trend_monitor import MarketTrendMonitorAgent
async def test():
    agent = MarketTrendMonitorAgent()
    result = await agent.execute({'action': 'get_trends', 'topic': 'B2B sales'})
    print(result)
asyncio.run(test())
"
```

---

## Commit History

- `249601e` - feat: Add HubSpot batch APIs, Data Hygiene agents, Twitter connector, and Social signal framework
- (this commit) - docs: Add Twitter/Grok setup documentation

---

**Last Updated:** January 24, 2026
