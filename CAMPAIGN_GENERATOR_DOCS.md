# Campaign Email Generator - Complete Documentation

## Overview

The Campaign Email Generator is a production-ready system that creates personalized email drafts for HubSpot contact segments using AI-powered generation and template-based personalization.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   API Layer                              │
│  POST /api/campaigns/generate                           │
│  POST /api/campaigns/generate/custom                    │
│  GET  /api/campaigns/generate/segments                  │
│  GET  /api/campaigns/generate/queue                     │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│            CampaignGenerator                             │
│  • generate_for_segment()                               │
│  • generate_for_contacts()                              │
│  • personalize_email()                                  │
│  • queue_all_drafts()                                   │
└─────────────────────────────────────────────────────────┘
          │                    │                    │
          ▼                    ▼                    ▼
┌──────────────────┐  ┌──────────────┐  ┌──────────────┐
│ HubSpotSync      │  │ DraftGenerator│  │ DraftQueue   │
│ Service          │  │ (AI-powered)  │  │ (Approval)   │
└──────────────────┘  └──────────────┘  └──────────────┘
```

## Components

### 1. CampaignGenerator (`src/campaigns/campaign_generator.py`)

Main class that orchestrates campaign email generation.

#### Key Methods:

**`generate_for_segment(segment_name, limit, auto_queue, batch_size)`**
- Generates drafts for a specific HubSpot segment
- Supports: chainge, high_value, engaged, cold, all
- Returns campaign statistics

**`generate_for_contacts(contact_list, segment_name, auto_queue, batch_size)`**
- Generates drafts for a custom contact list
- Allows targeting specific contacts
- Returns campaign statistics

**`personalize_email(contact, template)`**
- Personalizes email templates with contact data
- Replaces {{firstname}}, {{company}}, {{industry}}, etc.
- Adds industry-specific pain points

**`queue_all_drafts()`**
- Queues all generated drafts for operator approval
- Returns queue statistics

### 2. Email Templates

Pre-built templates for each segment with personalization variables:

#### CHAINge Template
```
Subject: Re: CHAINge NA — Partnership Opportunity
Focus: Partnership/networking
Talking Points: Partnership ecosystem, networking ROI, event collaboration
```

#### High Value Template
```
Subject: Quick question about {{company}}'s growth
Focus: ROI/enterprise impact
Talking Points: Revenue optimization, sales automation, AI orchestration
```

#### Engaged Template
```
Subject: Following up on your interest
Focus: Active follow-up
Talking Points: Interest follow-up, stage-appropriate solutions, success stories
```

#### Cold Template
```
Subject: Catching up — {{company}} updates?
Focus: Re-engagement
Talking Points: Soft reconnection, new capabilities, low-pressure approach
```

### 3. Personalization System

#### Template Variables
- `{{firstname}}` - Contact first name
- `{{lastname}}` - Contact last name
- `{{company}}` - Company name
- `{{jobtitle}}` - Job title
- `{{industry}}` - Auto-detected industry
- `{{pain_point}}` - Industry-specific pain point
- `{{signature}}` - Voice profile signature
- `{{meeting_slots}}` - Auto-generated meeting times

#### Industry Detection
Automatically detects industry from company name:
- Technology/Software/SaaS
- Finance/Banking
- Healthcare/Medical
- Consulting/Advisory
- Manufacturing
- Retail
- Real Estate
- Education

#### Industry Pain Points
Each industry gets specific pain points:
- **Technology**: "scaling sales operations efficiently"
- **SaaS**: "customer acquisition costs and retention"
- **Finance**: "compliance while maintaining growth"
- **Consulting**: "client relationship management"
- etc.

### 4. Integration Points

#### With DraftGenerator
- Uses OpenAI GPT-4o for AI-powered email generation
- Applies voice profile for tone/style
- Includes PII safety validation
- Generates subject lines and body content

#### With DraftQueue (OperatorMode)
- Creates drafts with PENDING_APPROVAL status
- Stores in PostgreSQL for persistence
- Enables operator review workflow
- Tracks approval/rejection

#### With HubSpotContactSyncService
- Fetches contacts by segment
- Retrieves contact properties
- Applies segment filters
- Handles pagination

## API Endpoints

### POST /api/campaigns/generate

Generate campaign emails for a segment.

**Request:**
```json
{
  "segment": "chainge",
  "limit": 50,
  "auto_queue": true,
  "batch_size": 10
}
```

**Response:**
```json
{
  "status": "success",
  "drafts_created": 50,
  "queued_for_approval": 50,
  "errors": 0,
  "contacts_processed": 50,
  "segment": "chainge",
  "duration_seconds": 45.2
}
```

**Valid Segments:**
- `chainge` - CHAINge NA attendees
- `high_value` - Enterprise/high-value contacts
- `engaged` - Recently active contacts
- `cold` - Inactive contacts (90+ days)
- `all` - All contacts

**Parameters:**
- `segment` (required): Segment name
- `limit` (optional): Max drafts to generate (default: 50, max: 500)
- `auto_queue` (optional): Queue for approval (default: true)
- `batch_size` (optional): Concurrent generation batch size (default: 10, max: 50)

### POST /api/campaigns/generate/custom

Generate campaign emails for custom contact list.

**Request:**
```json
{
  "contacts": [
    {
      "email": "john@example.com",
      "firstname": "John",
      "lastname": "Doe",
      "company": "Example Corp",
      "jobtitle": "CEO",
      "hubspot_id": "12345"
    }
  ],
  "segment_name": "high_value",
  "auto_queue": true,
  "batch_size": 10
}
```

**Response:**
```json
{
  "status": "success",
  "drafts_created": 25,
  "queued_for_approval": 25,
  "errors": 0,
  "contacts_processed": 25,
  "segment": "custom_list",
  "duration_seconds": 22.1
}
```

### GET /api/campaigns/generate/segments

Get available segments with contact counts.

**Response:**
```json
{
  "segments": [
    {
      "name": "chainge",
      "description": "CHAINge NA attendees - Partnership/networking focused emails",
      "template": "partnership_networking",
      "contact_count": 42
    },
    {
      "name": "high_value",
      "description": "High-value enterprise contacts - ROI/revenue focused emails",
      "template": "enterprise_roi",
      "contact_count": 156
    }
  ],
  "total_segments": 5
}
```

### GET /api/campaigns/generate/queue

Get campaign draft queue status.

**Response:**
```json
{
  "total_pending": 125,
  "by_segment": {
    "chainge": 50,
    "high_value": 40,
    "engaged": 20,
    "cold": 15
  },
  "drafts": [
    {
      "id": "draft-123",
      "recipient": "john@example.com",
      "subject": "Re: CHAINge NA — Partnership Opportunity",
      "status": "PENDING_APPROVAL",
      "created_at": "2026-01-23T10:30:00Z",
      "metadata": {
        "segment": "chainge",
        "campaign": "chainge_campaign_20260123"
      }
    }
  ]
}
```

## Usage Examples

### Example 1: Generate CHAINge Campaign

```bash
curl -X POST http://localhost:8000/api/campaigns/generate \
  -H "Content-Type: application/json" \
  -d '{
    "segment": "chainge",
    "limit": 50,
    "auto_queue": true
  }'
```

### Example 2: Generate High-Value Campaign

```bash
curl -X POST http://localhost:8000/api/campaigns/generate \
  -H "Content-Type: application/json" \
  -d '{
    "segment": "high_value",
    "limit": 100,
    "batch_size": 20
  }'
```

### Example 3: Custom Contact List

```bash
curl -X POST http://localhost:8000/api/campaigns/generate/custom \
  -H "Content-Type: application/json" \
  -d '{
    "contacts": [
      {
        "email": "jane@techcorp.com",
        "firstname": "Jane",
        "company": "TechCorp",
        "jobtitle": "VP Sales"
      }
    ],
    "segment_name": "high_value"
  }'
```

### Example 4: Check Available Segments

```bash
curl http://localhost:8000/api/campaigns/generate/segments
```

### Example 5: View Draft Queue

```bash
curl http://localhost:8000/api/campaigns/generate/queue
```

## Python Usage

```python
from src.campaigns.campaign_generator import create_campaign_generator

# Create generator
generator = create_campaign_generator()

# Generate for segment
result = await generator.generate_for_segment(
    segment_name="chainge",
    limit=50,
    auto_queue=True,
    batch_size=10
)

print(f"Created {result['drafts_created']} drafts")
print(f"Queued {result['queued_for_approval']} for approval")

# Generate for custom contacts
contacts = [
    {
        "email": "john@example.com",
        "firstname": "John",
        "company": "Example Corp"
    }
]

result = await generator.generate_for_contacts(
    contact_list=contacts,
    segment_name="high_value"
)

# Personalize email manually
contact = {
    "firstname": "John",
    "company": "Example Corp"
}

template = "Hi {{firstname}}, I saw {{company}} is growing fast!"
personalized = generator.personalize_email(contact, template)
# Output: "Hi John, I saw Example Corp is growing fast!"
```

## Configuration

### Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-...                    # For AI generation
HUBSPOT_API_KEY=pat-...                  # For contact sync

# Optional
OPENAI_MODEL=gpt-4o                      # AI model (default: gpt-4o)
OPERATOR_APPROVAL_REQUIRED=true          # Enable approval workflow
```

### Voice Profile

Configure in `src/voice_profile.py`:
- Signature style
- Tone (professional, friendly, casual)
- CTA approach (direct, soft, question-based)
- P.S. inclusion
- Meeting slot count

## Rate Limiting & Performance

### Batch Processing
- Default batch size: 10 concurrent drafts
- Adjustable via `batch_size` parameter
- Automatic delays between batches (1 second)

### OpenAI Rate Limits
- Batch processing prevents overwhelming API
- Automatic retry on rate limit errors
- PII safety validation on all drafts

### Expected Performance
- **50 drafts**: ~45 seconds
- **100 drafts**: ~90 seconds
- **500 drafts**: ~7-8 minutes

### Error Handling
- Individual draft failures don't stop campaign
- Errors tracked in statistics
- Detailed error information in response
- Continues with remaining contacts

## Draft Approval Workflow

1. **Draft Creation**: CampaignGenerator creates draft
2. **Queue Storage**: Draft stored in PostgreSQL with PENDING_APPROVAL status
3. **Operator Review**: Operator views draft in approval UI
4. **Approval/Rejection**: Operator approves or rejects
5. **Send**: Approved drafts sent via Gmail integration

### Approval API

```bash
# Get pending drafts
GET /api/operator/pending

# Approve draft
POST /api/operator/approve/{draft_id}

# Reject draft
POST /api/operator/reject/{draft_id}
```

## Testing

### Run Test Suite

```bash
python test_campaign_generator.py
```

**Tests Include:**
- Email personalization
- Segment contact retrieval
- Template selection
- Industry detection
- Meeting slot generation
- Personalization hooks
- Dry run statistics

### Manual Testing

```bash
# 1. Sync HubSpot contacts first
curl -X POST http://localhost:8000/api/contacts/sync/hubspot

# 2. Check available segments
curl http://localhost:8000/api/campaigns/generate/segments

# 3. Generate small test campaign
curl -X POST http://localhost:8000/api/campaigns/generate \
  -H "Content-Type: application/json" \
  -d '{"segment": "chainge", "limit": 5}'

# 4. Check draft queue
curl http://localhost:8000/api/campaigns/generate/queue

# 5. Review drafts in operator UI
curl http://localhost:8000/api/operator/pending
```

## Best Practices

### Campaign Planning
1. **Sync contacts first** - Ensure HubSpot data is current
2. **Start small** - Test with limit=5-10 before full campaign
3. **Review templates** - Ensure segment templates match campaign goals
4. **Monitor queue** - Check approval queue regularly
5. **Track metrics** - Monitor open rates, reply rates

### Segment Selection
- **CHAINge**: Time-sensitive (event-based), use for immediate outreach
- **High Value**: Focus on ROI messaging, enterprise language
- **Engaged**: Continuation emails, reference previous interaction
- **Cold**: Soft touch, mention what's new, low-pressure

### Personalization
- Verify contact data quality before generation
- Use custom templates for specialized campaigns
- Add personalization hooks for better relevance
- Test industry detection with sample companies

### Error Handling
- Monitor `errors` count in response
- Check `error_details` for specific issues
- Review PII safety blocks
- Validate contact email addresses

## Troubleshooting

### No contacts in segment
**Issue**: `drafts_created: 0` with no errors

**Solution**:
```bash
# Check segment contact count
curl http://localhost:8000/api/campaigns/generate/segments

# Sync HubSpot contacts
curl -X POST http://localhost:8000/api/contacts/sync/hubspot
```

### High error rate
**Issue**: Many errors in `error_details`

**Common causes**:
- Invalid email addresses
- Missing contact data (firstname, company)
- OpenAI API rate limits
- PII safety blocks

**Solution**:
- Clean contact data
- Reduce batch_size
- Check OpenAI API status
- Review PII validator settings

### Drafts not queued
**Issue**: `queued_for_approval: 0` but `drafts_created > 0`

**Solution**:
```python
# Check auto_queue parameter
{
  "segment": "chainge",
  "limit": 50,
  "auto_queue": true  # <-- Ensure this is true
}
```

### Slow generation
**Issue**: Campaign takes too long

**Solution**:
- Increase batch_size (max 50)
- Reduce limit for testing
- Check OpenAI API latency
- Monitor database performance

## Future Enhancements

### Planned Features
- [ ] A/B testing for templates
- [ ] Multi-touch sequences (follow-up emails)
- [ ] Dynamic content blocks
- [ ] Sentiment analysis
- [ ] Link tracking integration
- [ ] Campaign analytics dashboard
- [ ] Template builder UI
- [ ] Contact similarity matching
- [ ] Optimal send time prediction
- [ ] Response prediction scoring

### Integration Roadmap
- [ ] Gmail integration for sending
- [ ] Calendar integration for scheduling
- [ ] CRM activity logging
- [ ] Email tracking pixels
- [ ] Reply detection/parsing
- [ ] Meeting booking automation

## Support

### Documentation
- [API Endpoints](API_ENDPOINTS.md)
- [HubSpot Sync Docs](HUBSPOT_SYNC_DOCS.md)
- [Voice Training Guide](VOICE_TRAINING_GUIDE.md)

### Logs
```bash
# View campaign generation logs
tail -f logs/app.log | grep "Campaign"

# View draft queue logs
tail -f logs/app.log | grep "Draft"
```

### Metrics
```bash
# Campaign statistics
GET /api/analytics/campaigns

# Draft approval rates
GET /api/analytics/drafts
```

---

**Version**: 1.0.0  
**Last Updated**: January 23, 2026  
**Status**: Production Ready ✅
