# Quick Start: Voice Training & Contact Outreach

## 🎯 Goal
Train AI voice on "Dude, What's The Bid?!" videos and "Freight Marketer" newsletters, then queue contacts and generate personalized emails.

## 🚀 Quick Setup (5 minutes)

### 1. Install Dependencies
```bash
pip install youtube-transcript-api
```

### 2. Set API Keys
```bash
export HUBSPOT_API_KEY="your_key_here"
export OPENAI_API_KEY="your_key_here"
```

### 3. Start Server
```bash
uvicorn src.main:app --reload
```

## 📹 Train from "Dude, What's The Bid?!" Videos

### Example Video URLs
Replace these with actual "Dude, What's The Bid?!" episode URLs:

```bash
python -m src.cli.train_voice --videos \
  "https://www.youtube.com/watch?v=dQw4w9WgXcQ" \
  "https://www.youtube.com/watch?v=dQw4w9WgXcQ" \
  "https://www.youtube.com/watch?v=dQw4w9WgXcQ" \
  --profile-name "dude_whats_the_bid"
```

**Or via API:**
```bash
curl -X POST http://localhost:8000/api/voice/training/youtube-videos \
  -H "Content-Type: application/json" \
  -d '{
    "video_urls": [
      "https://www.youtube.com/watch?v=VIDEO_ID_1",
      "https://www.youtube.com/watch?v=VIDEO_ID_2",
      "https://www.youtube.com/watch?v=VIDEO_ID_3"
    ],
    "profile_name": "dude_whats_the_bid"
  }'
```

## 📧 Train from Freight Marketer Newsletters

```bash
# CLI
python -m src.cli.train_voice --newsletters "freight marketer"

# API
curl -X POST http://localhost:8000/api/voice/training/hubspot-newsletters \
  -H "Content-Type: application/json" \
  -d '{
    "search_query": "freight marketer",
    "limit": 20
  }'
```

## ✅ Create Voice Profile

```bash
curl -X POST "http://localhost:8000/api/voice/training/create-profile?profile_name=freight_voice"
```

## 👥 Queue Up Contacts

```bash
curl -X POST http://localhost:8000/api/contact-queue/add-bulk \
  -H "Content-Type: application/json" \
  -d '{
    "contacts": [
      {
        "email": "john@trucking.com",
        "first_name": "John",
        "last_name": "Doe",
        "company": "Trucking Co",
        "job_title": "VP Operations",
        "voice_profile": "freight_voice",
        "priority": 1
      },
      {
        "email": "jane@logistics.com",
        "first_name": "Jane",
        "last_name": "Smith",
        "company": "Logistics Inc",
        "job_title": "Director Marketing",
        "voice_profile": "freight_voice"
      }
    ]
  }'
```

## 🔍 Research & Generate Emails

### 1. List Queued Contacts
```bash
curl http://localhost:8000/api/contact-queue/list?status=pending
```

### 2. Research Contact
```bash
# Replace {contact_id} with actual ID from step 1
curl -X POST http://localhost:8000/api/contact-queue/{contact_id}/research
```

### 3. Generate Email Proposals
```bash
curl -X POST "http://localhost:8000/api/contact-queue/{contact_id}/propose-email?num_variants=3"
```

### 4. View Proposals
```bash
curl http://localhost:8000/api/contact-queue/{contact_id}
```

## 📊 Complete Example Flow

```python
#!/usr/bin/env python3
"""Complete workflow example."""
import asyncio
import httpx

async def main():
    base = "http://localhost:8000"
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # 1. Train from videos
        print("🎥 Training from videos...")
        r = await client.post(f"{base}/api/voice/training/youtube-videos", json={
            "video_urls": [
                "https://www.youtube.com/watch?v=VIDEO1",
                "https://www.youtube.com/watch?v=VIDEO2",
            ]
        })
        print(f"✅ {r.json()['transcripts_added']} videos transcribed")
        
        # 2. Train from newsletters
        print("\n📧 Training from newsletters...")
        r = await client.post(f"{base}/api/voice/training/hubspot-newsletters", json={
            "search_query": "freight marketer",
            "limit": 15
        })
        print(f"✅ {r.json()['newsletters_fetched']} newsletters fetched")
        
        # 3. Create profile
        print("\n🎨 Creating voice profile...")
        r = await client.post(f"{base}/api/voice/training/create-profile?profile_name=freight_voice")
        print(f"✅ Profile created: {r.json()['profile_name']}")
        
        # 4. Add contacts
        print("\n👥 Adding contacts to queue...")
        r = await client.post(f"{base}/api/contact-queue/add-bulk", json={
            "contacts": [{
                "email": "test@example.com",
                "first_name": "Test",
                "last_name": "User",
                "company": "Test Co",
                "job_title": "VP Ops",
                "voice_profile": "freight_voice"
            }]
        })
        contact_id = r.json()["contact_ids"][0]
        print(f"✅ Contact added: {contact_id}")
        
        # 5. Research
        print(f"\n🔍 Researching contact...")
        r = await client.post(f"{base}/api/contact-queue/{contact_id}/research")
        print(f"✅ Research complete")
        
        # 6. Generate emails
        print(f"\n✉️ Generating email proposals...")
        r = await client.post(f"{base}/api/contact-queue/{contact_id}/propose-email?num_variants=2")
        proposals = r.json()["proposals"]
        
        print(f"\n📬 Generated {len(proposals)} email variants:")
        for p in proposals:
            print(f"\n--- Variant {p['variant']} ---")
            print(f"Subject: {p['subject']}")
            print(f"\n{p['body']}")
            print(f"\nReasoning: {p['reasoning']}")

asyncio.run(main())
```

Save as `test_workflow.py` and run:
```bash
python test_workflow.py
```

## 🎯 Key Endpoints

| Action | Method | Endpoint |
|--------|--------|----------|
| Train from videos | POST | `/api/voice/training/youtube-videos` |
| Train from newsletters | POST | `/api/voice/training/hubspot-newsletters` |
| Create voice profile | POST | `/api/voice/training/create-profile` |
| Add contacts | POST | `/api/contact-queue/add-bulk` |
| List queue | GET | `/api/contact-queue/list` |
| Research contact | POST | `/api/contact-queue/{id}/research` |
| Generate emails | POST | `/api/contact-queue/{id}/propose-email` |
| View contact | GET | `/api/contact-queue/{id}` |

## 📝 Notes

- Videos must have captions enabled
- HubSpot newsletters require Marketing API access
- Training takes 1-2 minutes per video
- Email generation is instant
- All data stored in-memory (restart to clear)

## 🐛 Troubleshooting

**"youtube-transcript-api not installed"**
```bash
pip install youtube-transcript-api
```

**"No captions available"**
- Video must have subtitles/captions
- Try auto-generated captions
- Use different video

**"HubSpot connector not configured"**
```bash
export HUBSPOT_API_KEY="your_key"
```

**"No newsletters found"**
- Check exact search term
- Verify API key has marketing scope
- Try broader search

---

See [VOICE_TRAINING_GUIDE.md](VOICE_TRAINING_GUIDE.md) for complete documentation.
