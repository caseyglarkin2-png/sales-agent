# Sprint 13: Social Intelligence & Twitter Personal Feed

**Status:** 🟢 IN PROGRESS  
**Started:** January 24, 2026  
**Target Completion:** January 27, 2026

---

## Sprint Goal

**Demo Statement:** Casey opens CaseyOS and sees social signals from his Twitter feed powering recommendations. Grok provides real-time market intel on competitors.

---

## Prerequisites ✅

- [x] Twitter Bearer Token configured
- [x] Twitter Consumer Key configured
- [x] Twitter Consumer Secret configured
- [x] Twitter OAuth routes deployed
- [x] Grok connector built
- [ ] xAI API Key (pending user action)

---

## Tasks

### Task 13.1: Test Twitter OAuth Flow End-to-End

**Priority:** HIGH  
**Effort:** 1 hour  
**Dependencies:** None

**One-liner:** Verify the full OAuth 1.0a flow works in production.

**Scope:**
- Visit `/auth/twitter/login` in production
- Complete Twitter authorization
- Verify callback receives tokens
- Test home timeline endpoint

**Does NOT include:**
- Storing tokens in database (future task)
- Multi-user support

**Validation:**
```bash
# 1. Open in browser
open https://web-production-a6ccf.up.railway.app/auth/twitter/login

# 2. Authorize on Twitter

# 3. Check status shows authenticated user
curl https://web-production-a6ccf.up.railway.app/auth/twitter/status | jq '.authenticated_users'

# 4. Get home timeline (if authenticated)
curl "https://web-production-a6ccf.up.railway.app/auth/twitter/user/{user_id}/home_timeline?count=5" | jq '.data | length'
```

**Acceptance Criteria:**
- [ ] OAuth flow redirects to Twitter
- [ ] Callback receives access tokens
- [ ] `/auth/twitter/status` shows authenticated user
- [ ] Home timeline endpoint returns tweets

**Rollback:** OAuth routes are stateless, no rollback needed.

---

### Task 13.2: Create Social Signal Provider

**Priority:** HIGH  
**Effort:** 2 hours  
**Dependencies:** 13.1

**One-liner:** Connect Twitter home timeline to the Signal pipeline.

**Scope:**
- Create `SocialHomeTimelineProvider` class
- Poll authenticated user's timeline
- Filter for GTM-relevant content (keywords, hashtags)
- Generate `Signal` records

**Files:**
- Create: `src/signals/providers/twitter_home.py`
- Modify: `src/signals/providers/__init__.py`

**Contracts:**
```python
class TwitterHomeProvider(SignalProvider):
    """Poll authenticated user's home timeline for signals."""
    
    async def poll(self, user_id: str) -> List[Signal]:
        """Get new tweets since last poll and convert to signals."""
        
    def _is_gtm_relevant(self, tweet: Tweet) -> bool:
        """Check if tweet contains GTM-relevant content."""
        keywords = ["sales", "CRM", "B2B", "SaaS", "revenue", "pipeline"]
        # Check text, hashtags, mentions
```

**Validation:**
```bash
python -c "
from src.signals.providers.twitter_home import TwitterHomeProvider
provider = TwitterHomeProvider()
print(f'Keywords: {provider.gtm_keywords[:5]}')
"
```

**Acceptance Criteria:**
- [ ] Provider polls home timeline via OAuth
- [ ] Filters tweets by GTM relevance
- [ ] Creates Signal records with tweet data
- [ ] Handles rate limits gracefully

**Rollback:** Remove provider file.

---

### Task 13.3: Add Social Signals to Command Queue

**Priority:** MEDIUM  
**Effort:** 1.5 hours  
**Dependencies:** 13.2

**One-liner:** Convert social signals into actionable recommendations.

**Scope:**
- Create `SocialSignalProcessor` 
- Calculate APS for social signals (engagement weight)
- Generate "Engage with tweet" recommendations
- Add to Today's Moves with social domain

**Files:**
- Create: `src/signals/processors/social_processor.py`
- Modify: `src/signals/__init__.py`

**Contracts:**
```python
class SocialSignalProcessor:
    """Convert social signals to command queue items."""
    
    async def process(self, signal: Signal) -> Optional[CommandQueueItem]:
        # High-engagement tweets from thought leaders → higher APS
        # Industry trends → medium APS
        # General mentions → low APS
```

**Validation:**
```bash
curl https://web-production-a6ccf.up.railway.app/api/command-queue/today?domain=marketing | jq '.today_moves | map(select(.action_type | contains("social")))'
```

**Acceptance Criteria:**
- [ ] Social signals create queue items
- [ ] Domain set to "marketing"
- [ ] APS considers engagement metrics
- [ ] Action type includes "engage", "share", "reply"

**Rollback:** Feature flag or remove processor.

---

### Task 13.4: Set Up xAI API Key

**Priority:** HIGH  
**Effort:** 15 minutes  
**Dependencies:** User action

**One-liner:** Configure xAI Grok API key in production.

**Scope:**
- User gets API key from console.x.ai
- Set `XAI_API_KEY` in Railway

**Validation:**
```bash
# Set the key (user provides value)
railway variables set XAI_API_KEY="xai-..."

# Verify Grok health
curl https://web-production-a6ccf.up.railway.app/api/jarvis/health | jq '.llm_providers.grok'
```

**Acceptance Criteria:**
- [ ] `XAI_API_KEY` set in Railway
- [ ] Grok health check passes
- [ ] Can generate text with Grok

**Rollback:** Unset variable, falls back to other LLMs.

---

### Task 13.5: Integrate Grok Market Intelligence

**Priority:** MEDIUM  
**Effort:** 2 hours  
**Dependencies:** 13.4

**One-liner:** Use Grok for real-time market intelligence reports.

**Scope:**
- Connect `MarketTrendMonitorAgent` to Grok connector
- Generate market intel from social signals
- Auto-update competitive battle cards

**Files:**
- Modify: `src/agents/market_trend_monitor.py`
- Modify: `src/connectors/grok.py` (if needed)

**Contracts:**
```python
# In MarketTrendMonitorAgent
async def get_competitor_intel_with_grok(self, company: str) -> Dict:
    """Use Grok for real-time competitor analysis."""
    grok = get_grok()
    return await grok.get_competitive_insights(
        company=company,
        industry=self.industry,
        competitors=self.tracked_competitors
    )
```

**Validation:**
```bash
curl -X POST https://web-production-a6ccf.up.railway.app/api/jarvis/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the latest trends in B2B sales?"}' | jq '.answer | .[:200]'
```

**Acceptance Criteria:**
- [ ] Grok generates market intel
- [ ] Battle cards include real-time data
- [ ] Response time <5 seconds

**Rollback:** Fall back to cached data or OpenAI.

---

### Task 13.6: Twitter Thought Leader Monitoring

**Priority:** LOW  
**Effort:** 1 hour  
**Dependencies:** 13.1

**One-liner:** Track specific industry thought leaders for signals.

**Scope:**
- Configure list of thought leaders to monitor
- Poll their timelines using Bearer Token
- Generate signals for high-engagement posts

**Files:**
- Modify: `src/connectors/twitter.py` (add thought_leaders config)
- Create: `src/signals/providers/twitter_leaders.py`

**Validation:**
```bash
curl https://web-production-a6ccf.up.railway.app/api/signals/health | jq '.providers.twitter_leaders'
```

**Acceptance Criteria:**
- [ ] Monitors 5-10 thought leaders
- [ ] Generates signals for their posts
- [ ] Configurable via environment/config

**Rollback:** Disable provider.

---

## Sprint 13 Exit Criteria

- [ ] Twitter OAuth flow works end-to-end
- [ ] Personal feed tweets appear as signals (if OAuth'd)
- [ ] Social signals create command queue items
- [ ] xAI API key configured (pending user)
- [ ] Grok generates market intel reports

---

## Demo Script

```bash
# 1. Show Twitter OAuth status
curl https://web-production-a6ccf.up.railway.app/auth/twitter/status | jq .

# 2. Complete OAuth (in browser)
open https://web-production-a6ccf.up.railway.app/auth/twitter/login

# 3. Show social signals in command queue
curl "https://web-production-a6ccf.up.railway.app/api/command-queue/today?domain=marketing" | jq '.today_moves | .[0]'

# 4. Show Grok market intel
curl -X POST https://web-production-a6ccf.up.railway.app/api/jarvis/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "Give me competitive intel on HubSpot"}' | jq '.answer'
```

---

## Notes

- Twitter API free tier: 1,500 tweet reads/month
- Grok API: Pay-as-you-go, check console.x.ai for pricing
- Bearer Token = public data only, OAuth = personal feed

---

**Last Updated:** January 24, 2026
