# Campaign Generator - Quick Start Guide

## 🚀 Quick Start (5 Minutes)

### Step 1: Sync HubSpot Contacts

First, sync your HubSpot contacts to the local database:

```bash
curl -X POST http://localhost:8000/api/contacts/sync/hubspot
```

Expected output:
```json
{
  "total_synced": 1247,
  "by_segment": {
    "chainge": 42,
    "high_value": 156,
    "engaged": 320,
    "cold": 89
  },
  "duration_seconds": 12.5
}
```

### Step 2: Check Available Segments

See what contacts are available:

```bash
curl http://localhost:8000/api/campaigns/generate/segments
```

### Step 3: Generate Your First Campaign

Start with a small test (5 contacts):

```bash
curl -X POST http://localhost:8000/api/campaigns/generate \
  -H "Content-Type: application/json" \
  -d '{
    "segment": "chainge",
    "limit": 5,
    "auto_queue": true
  }'
```

Expected output:
```json
{
  "status": "success",
  "drafts_created": 5,
  "queued_for_approval": 5,
  "errors": 0,
  "contacts_processed": 5,
  "segment": "chainge",
  "duration_seconds": 4.2
}
```

### Step 4: Review Drafts

Check the approval queue:

```bash
curl http://localhost:8000/api/campaigns/generate/queue
```

### Step 5: Approve/Send

View and approve drafts in the operator UI:

```bash
# Get pending drafts
curl http://localhost:8000/api/operator/pending

# Approve a draft
curl -X POST http://localhost:8000/api/operator/approve/DRAFT_ID
```

## 📊 Production Campaign (50+ Contacts)

Once you've tested with 5 contacts, scale up:

```bash
# CHAINge campaign (50 contacts)
curl -X POST http://localhost:8000/api/campaigns/generate \
  -H "Content-Type: application/json" \
  -d '{
    "segment": "chainge",
    "limit": 50,
    "auto_queue": true,
    "batch_size": 10
  }'

# High value campaign (100 contacts)
curl -X POST http://localhost:8000/api/campaigns/generate \
  -H "Content-Type: application/json" \
  -d '{
    "segment": "high_value",
    "limit": 100,
    "batch_size": 20
  }'
```

## 🎯 Segment Strategies

### CHAINge (Event-Based)
**When to use**: CHAINge NA attendees, time-sensitive
**Template focus**: Partnership, networking, event opportunities
**Best timing**: 1-2 weeks before event

```bash
curl -X POST http://localhost:8000/api/campaigns/generate \
  -H "Content-Type: application/json" \
  -d '{"segment": "chainge", "limit": 42}'
```

### High Value (Enterprise)
**When to use**: Enterprise contacts, C-level executives
**Template focus**: ROI, revenue impact, strategic value
**Best timing**: Quarterly business planning cycles

```bash
curl -X POST http://localhost:8000/api/campaigns/generate \
  -H "Content-Type: application/json" \
  -d '{"segment": "high_value", "limit": 100}'
```

### Engaged (Active Contacts)
**When to use**: Recently active, replied to previous emails
**Template focus**: Continuation, follow-up, next steps
**Best timing**: Within 1 week of last interaction

```bash
curl -X POST http://localhost:8000/api/campaigns/generate \
  -H "Content-Type: application/json" \
  -d '{"segment": "engaged", "limit": 75}'
```

### Cold (Re-engagement)
**When to use**: No activity in 90+ days
**Template focus**: Soft reconnection, "what's new", low-pressure
**Best timing**: Beginning of quarter, product launches

```bash
curl -X POST http://localhost:8000/api/campaigns/generate \
  -H "Content-Type: application/json" \
  -d '{"segment": "cold", "limit": 50}'
```

## 🔧 Common Workflows

### Workflow 1: Weekly CHAINge Campaign

```bash
# Monday: Sync contacts
curl -X POST http://localhost:8000/api/contacts/sync/hubspot

# Tuesday: Generate campaign
curl -X POST http://localhost:8000/api/campaigns/generate \
  -d '{"segment": "chainge", "limit": 50}'

# Wednesday: Approve drafts
curl http://localhost:8000/api/operator/pending
# Review and approve in UI

# Thursday: Monitor responses
curl http://localhost:8000/api/analytics/campaigns
```

### Workflow 2: Custom Target List

```bash
# Create custom contact list
curl -X POST http://localhost:8000/api/campaigns/generate/custom \
  -H "Content-Type: application/json" \
  -d '{
    "contacts": [
      {
        "email": "ceo@targetcorp.com",
        "firstname": "Sarah",
        "company": "Target Corp",
        "jobtitle": "CEO"
      },
      {
        "email": "vp@targetcorp.com",
        "firstname": "Mike",
        "company": "Target Corp",
        "jobtitle": "VP Sales"
      }
    ],
    "segment_name": "high_value"
  }'
```

### Workflow 3: Multi-Segment Blitz

```bash
# Generate for all segments
for segment in chainge high_value engaged cold; do
  curl -X POST http://localhost:8000/api/campaigns/generate \
    -H "Content-Type: application/json" \
    -d "{\"segment\": \"$segment\", \"limit\": 25}"
  sleep 5
done

# Check total queue
curl http://localhost:8000/api/campaigns/generate/queue
```

## 📈 Performance Tuning

### Faster Generation
```json
{
  "segment": "chainge",
  "limit": 100,
  "batch_size": 25  // Increase from default 10
}
```

### Rate Limit Safe
```json
{
  "segment": "high_value",
  "limit": 500,
  "batch_size": 5  // Decrease for stability
}
```

## ⚡ Python Usage

### Basic Script

```python
import asyncio
import httpx

async def generate_campaign():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/campaigns/generate",
            json={
                "segment": "chainge",
                "limit": 50,
                "auto_queue": True
            }
        )
        result = response.json()
        print(f"Created {result['drafts_created']} drafts")

asyncio.run(generate_campaign())
```

### Advanced Script

```python
from src.campaigns.campaign_generator import create_campaign_generator

async def main():
    generator = create_campaign_generator()
    
    # Generate for multiple segments
    segments = ["chainge", "high_value", "engaged"]
    
    for segment in segments:
        result = await generator.generate_for_segment(
            segment_name=segment,
            limit=25,
            auto_queue=True
        )
        
        print(f"{segment}: {result['drafts_created']} drafts")
        print(f"  Queued: {result['queued_for_approval']}")
        print(f"  Errors: {result['errors']}")
        print()

asyncio.run(main())
```

## 🐛 Troubleshooting

### No contacts found
```bash
# Problem: drafts_created = 0

# Solution: Sync HubSpot first
curl -X POST http://localhost:8000/api/contacts/sync/hubspot

# Check segment counts
curl http://localhost:8000/api/campaigns/generate/segments
```

### OpenAI rate limits
```bash
# Problem: "Rate limit exceeded"

# Solution: Reduce batch_size
{
  "segment": "chainge",
  "limit": 50,
  "batch_size": 5  // Slower but safer
}
```

### Drafts not in queue
```bash
# Problem: queued_for_approval = 0

# Solution: Set auto_queue=true
{
  "segment": "chainge",
  "limit": 10,
  "auto_queue": true  // Must be true
}
```

## 📚 Next Steps

1. **Read Full Docs**: [CAMPAIGN_GENERATOR_DOCS.md](CAMPAIGN_GENERATOR_DOCS.md)
2. **Test Suite**: `python test_campaign_generator.py`
3. **API Reference**: [API_ENDPOINTS.md](API_ENDPOINTS.md)
4. **Voice Training**: [VOICE_TRAINING_GUIDE.md](VOICE_TRAINING_GUIDE.md)

## 💡 Pro Tips

1. **Start Small**: Always test with 5-10 contacts first
2. **Review Templates**: Customize templates for your brand voice
3. **Monitor Metrics**: Track open rates, reply rates per segment
4. **Sync Often**: Sync HubSpot daily for fresh data
5. **Batch Wisely**: batch_size=10 is optimal for most cases
6. **Time It Right**: Send campaigns Tuesday-Thursday 10am-2pm
7. **A/B Test**: Try different templates on same segment
8. **Clean Data**: Better contact data = better personalization

---

**Ready to launch?** Start with Step 1 above! 🚀
