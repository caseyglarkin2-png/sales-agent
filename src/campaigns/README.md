# Campaign Email Generator

**Production-ready campaign email generator for HubSpot contact segments**

## 🎯 What It Does

Generates personalized email drafts for HubSpot contact segments using:
- ✅ AI-powered email generation (OpenAI GPT-4o)
- ✅ Template-based personalization with {{variables}}
- ✅ Industry-specific messaging
- ✅ Segment-based targeting
- ✅ Batch processing with rate limiting
- ✅ Operator approval workflow

## 🚀 Quick Start

```bash
# 1. Sync HubSpot contacts
curl -X POST http://localhost:8000/api/contacts/sync/hubspot

# 2. Generate campaign (5 test drafts)
curl -X POST http://localhost:8000/api/campaigns/generate \
  -H "Content-Type: application/json" \
  -d '{"segment": "chainge", "limit": 5}'

# 3. Review drafts
curl http://localhost:8000/api/campaigns/generate/queue

# 4. Approve and send (use operator UI)
```

## 📁 Files

- **`src/campaigns/campaign_generator.py`** - Main implementation (700+ lines)
- **`src/routes/campaigns.py`** - API endpoints (updated)
- **`test_campaign_generator.py`** - Test suite
- **`CAMPAIGN_GENERATOR_DOCS.md`** - Complete documentation
- **`CAMPAIGN_QUICK_START.md`** - Quick start guide
- **`CAMPAIGN_IMPLEMENTATION_SUMMARY.md`** - Implementation summary

## 📊 API Endpoints

### Generate Campaign
```bash
POST /api/campaigns/generate
{
  "segment": "chainge",      # chainge, high_value, engaged, cold, all
  "limit": 50,               # max drafts to generate
  "auto_queue": true,        # queue for approval
  "batch_size": 10           # concurrent generation
}
```

### Custom Contact List
```bash
POST /api/campaigns/generate/custom
{
  "contacts": [...],         # array of contact objects
  "segment_name": "high_value",
  "auto_queue": true
}
```

### Get Segments
```bash
GET /api/campaigns/generate/segments
# Returns: segments with contact counts
```

### Get Queue
```bash
GET /api/campaigns/generate/queue
# Returns: pending drafts by segment
```

## 🎨 Segments & Templates

### CHAINge
**Focus**: Partnership/networking  
**Template**: Event-based, collaborative  
**Use When**: CHAINge NA attendees

### High Value
**Focus**: ROI/enterprise impact  
**Template**: Professional, value-focused  
**Use When**: Enterprise contacts, C-level

### Engaged
**Focus**: Continuation/follow-up  
**Template**: Friendly, helpful  
**Use When**: Recently active contacts

### Cold
**Focus**: Re-engagement  
**Template**: Casual, low-pressure  
**Use When**: Inactive 90+ days

## 🔧 Configuration

```bash
# Required
OPENAI_API_KEY=sk-...
HUBSPOT_API_KEY=pat-...

# Optional
OPENAI_MODEL=gpt-4o
OPERATOR_APPROVAL_REQUIRED=true
```

## 🧪 Testing

```bash
python test_campaign_generator.py
```

## 📚 Documentation

- **Quick Start**: [CAMPAIGN_QUICK_START.md](CAMPAIGN_QUICK_START.md)
- **Full Docs**: [CAMPAIGN_GENERATOR_DOCS.md](CAMPAIGN_GENERATOR_DOCS.md)
- **Summary**: [CAMPAIGN_IMPLEMENTATION_SUMMARY.md](CAMPAIGN_IMPLEMENTATION_SUMMARY.md)

## ✨ Features

- ✅ 5 segment types with custom templates
- ✅ 8+ personalization variables
- ✅ Industry auto-detection (9 industries)
- ✅ Industry-specific pain points
- ✅ Auto-generated meeting slots
- ✅ Batch processing (1-50 concurrent)
- ✅ Rate limiting protection
- ✅ Error isolation and recovery
- ✅ PII safety validation
- ✅ Queue integration
- ✅ Statistics tracking
- ✅ Complete type hints
- ✅ Comprehensive error handling
- ✅ Production-ready

## 🎉 Status

**PRODUCTION READY** ✅

- No placeholders
- Complete implementation
- Full documentation
- Test suite included
- All requirements met

---

**Version**: 1.0.0  
**Date**: January 23, 2026
