# HubSpot Sync - Quick Reference

## 🚀 Quick Start

### 1. Sync All Contacts (API)

```bash
curl -X POST http://localhost:8000/api/integrations/hubspot/sync \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sync_type": "all"}'
```

### 2. Query Contacts (API)

```bash
# All contacts
curl http://localhost:8000/api/integrations/hubspot/contacts

# CHAINge contacts only
curl http://localhost:8000/api/integrations/hubspot/contacts?segment=chainge

# Pagination
curl http://localhost:8000/api/integrations/hubspot/contacts?limit=50&offset=100
```

### 3. Python Usage

```python
from src.hubspot_sync import get_sync_service

# Sync all contacts
service = get_sync_service()
stats = await service.sync_all_contacts()
print(f"Synced {stats.total_synced} contacts")

# Get CHAINge contacts
result = service.get_contacts(segment="chainge")
print(f"Found {result['total']} CHAINge contacts")

await service.close()
```

### 4. Test Script

```bash
# Quick test (10 contacts)
python test_hubspot_sync.py --max-contacts 10

# Full sync
python test_hubspot_sync.py

# CHAINge only
python test_hubspot_sync.py --chainge-only
```

## 📊 Segments

Automatically applied based on contact properties:

- **chainge** - Company contains "chainge"
- **engaged** - Updated within 30 days
- **cold** - No updates in 90+ days
- **high_value** - Customer/evangelist/opportunity lifecycle stage

## 🔧 Configuration

```bash
# Required environment variable
export HUBSPOT_API_KEY=pat-na1-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# Verify in Railway
railway variables
```

## 📚 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/integrations/hubspot/sync` | Trigger full sync |
| GET | `/api/integrations/hubspot/contacts` | Query contacts |
| GET | `/api/integrations/hubspot/sync/stats` | Get sync stats |
| DELETE | `/api/integrations/hubspot/contacts` | Clear all contacts |

## 🎯 Key Features

✅ Handles 1000+ contacts with automatic pagination  
✅ 4 automatic segment tags (CHAINge, Engaged, Cold, High Value)  
✅ Error handling for 401, 429, 500  
✅ Progress logging every page  
✅ In-memory storage (PostgreSQL-ready)  

## 📁 Files

- `src/hubspot_sync.py` - Main service (475 lines)
- `src/routes/integrations_api.py` - API endpoints (updated)
- `test_hubspot_sync.py` - Test script (187 lines)
- `HUBSPOT_SYNC_DOCS.md` - Full documentation

## 🚨 Troubleshooting

**"API key not configured"**
```bash
railway variables set HUBSPOT_API_KEY=pat-na1-xxx
```

**"401 Unauthorized"**
- Check HubSpot Private App has `crm.objects.contacts.read` scope

**"429 Rate Limited"**
- Service auto-retries after 5 seconds
- Normal during large syncs

## ✅ Status

**PRODUCTION READY** - Deploy to Railway now!

```bash
# Deploy
git add .
git commit -m "feat: HubSpot contact sync with pagination and segments"
git push
railway up
```
