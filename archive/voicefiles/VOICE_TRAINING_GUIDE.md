# Voice Training & Contact Queue Guide

## Overview

This guide shows you how to train the voice profile on videos (like "Dude, What's The Bid?!") and newsletters (like "Freight Marketer"), then queue up contacts and generate personalized email proposals.

## Prerequisites

1. **Install dependencies:**
   ```bash
   pip install youtube-transcript-api
   ```

2. **Set environment variables:**
   ```bash
   export HUBSPOT_API_KEY="your_hubspot_api_key"
   export OPENAI_API_KEY="your_openai_key"
   ```

## Part 1: Training Voice Profiles

### Option A: Train from YouTube Videos

Train the voice on "Dude, What's The Bid?!" episodes or any YouTube videos:

```bash
# Using CLI
python -m src.cli.train_voice --videos \
  "https://www.youtube.com/watch?v=VIDEO_ID_1" \
  "https://www.youtube.com/watch?v=VIDEO_ID_2" \
  "https://www.youtube.com/watch?v=VIDEO_ID_3" \
  --profile-name "dude_whats_the_bid"
```

**Using API:**
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

### Option B: Train from HubSpot Newsletters

Train on "Freight Marketer" newsletters or any HubSpot marketing emails:

```bash
# Using CLI
python -m src.cli.train_voice --newsletters "freight marketer" \
  --profile-name "freight_marketer_voice"
```

**Using API:**
```bash
curl -X POST http://localhost:8000/api/voice/training/hubspot-newsletters \
  -H "Content-Type: application/json" \
  -d '{
    "search_query": "freight marketer",
    "limit": 20,
    "profile_name": "freight_marketer_voice"
  }'
```

### Option C: Train from Both

```bash
python -m src.cli.train_voice --all
```

This will:
1. Transcribe "Dude, What's The Bid?!" videos
2. Fetch "Freight Marketer" newsletters
3. Analyze all content
4. Create combined voice profiles

### Step 3: Create Voice Profile from Training

After adding training samples, generate the voice profile:

```bash
curl -X POST http://localhost:8000/api/voice/training/create-profile?profile_name=my_custom_voice
```

Response:
```json
{
  "status": "created",
  "profile_id": "my_custom_voice",
  "profile_name": "My Custom Voice",
  "tone": "professional",
  "samples_used": 23
}
```

### Step 4: Check Training Status

```bash
curl http://localhost:8000/api/voice/training/status
```

---

## Part 2: Queue Up Contacts

### Add Single Contact

```bash
curl -X POST http://localhost:8000/api/contact-queue/add \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john.doe@freightcompany.com",
    "first_name": "John",
    "last_name": "Doe",
    "company": "Freight Company Inc",
    "job_title": "VP of Operations",
    "voice_profile": "freight_marketer_voice",
    "priority": 1
  }'
```

### Add Multiple Contacts

```bash
curl -X POST http://localhost:8000/api/contact-queue/add-bulk \
  -H "Content-Type: application/json" \
  -d '{
    "contacts": [
      {
        "email": "jane@logistics.com",
        "first_name": "Jane",
        "last_name": "Smith",
        "company": "Logistics Co",
        "job_title": "Director of Marketing",
        "voice_profile": "dude_whats_the_bid"
      },
      {
        "email": "bob@shipping.com",
        "first_name": "Bob",
        "last_name": "Johnson",
        "company": "Shipping Solutions",
        "job_title": "CEO",
        "voice_profile": "freight_marketer_voice",
        "priority": 2
      }
    ]
  }'
```

### List Contacts in Queue

```bash
# All contacts
curl http://localhost:8000/api/contact-queue/list

# Filter by status
curl "http://localhost:8000/api/contact-queue/list?status=pending"

# With pagination
curl "http://localhost:8000/api/contact-queue/list?limit=20&offset=0"
```

---

## Part 3: Research Contacts

For each contact, run research to gather insights:

```bash
curl -X POST http://localhost:8000/api/contact-queue/{contact_id}/research
```

This will:
- Enrich contact data
- Analyze company information
- Identify pain points and opportunities
- Suggest messaging angles

Response:
```json
{
  "status": "success",
  "contact_id": "abc-123",
  "research": {
    "contact_info": {
      "email": "john.doe@freightcompany.com",
      "name": "John Doe",
      "company": "Freight Company Inc",
      "title": "VP of Operations"
    },
    "company_info": {
      "name": "Freight Company Inc",
      "industry": "Logistics",
      "size": "50-200 employees"
    },
    "insights": [
      "Recently expanded into new market",
      "Focus on operational efficiency"
    ],
    "recommended_angle": "Focus on ROI and efficiency gains"
  }
}
```

---

## Part 4: Generate Email Proposals

After research, propose personalized emails:

```bash
curl -X POST http://localhost:8000/api/contact-queue/{contact_id}/propose-email?num_variants=3
```

This generates multiple email variants using:
- The trained voice profile
- Research insights
- Personalization based on role and industry

Response:
```json
{
  "status": "success",
  "contact_id": "abc-123",
  "proposals": [
    {
      "id": "proposal-1",
      "variant": 1,
      "subject": "Re: Freight Company's growth",
      "body": "Hi John,\n\nI noticed Freight Company is focused on operational efficiency...",
      "reasoning": "Using problem_solving approach based on research",
      "personalization_notes": [
        "Referenced company focus from research",
        "Industry-specific language",
        "Low-commitment ask (15 min)"
      ],
      "voice_profile": "freight_marketer_voice"
    },
    {
      "id": "proposal-2",
      "variant": 2,
      "subject": "Logistics efficiency insights",
      "body": "...",
      "reasoning": "Using industry_insight approach",
      "personalization_notes": [...]
    }
  ]
}
```

---

## Complete Workflow Example

Here's a complete Python script to automate the entire process:

```python
import asyncio
import httpx

BASE_URL = "http://localhost:8000"

async def complete_workflow():
    async with httpx.AsyncClient() as client:
        # 1. Train voice from videos
        print("🎥 Training from videos...")
        response = await client.post(
            f"{BASE_URL}/api/voice/training/youtube-videos",
            json={
                "video_urls": [
                    "https://www.youtube.com/watch?v=VIDEO1",
                    "https://www.youtube.com/watch?v=VIDEO2",
                ],
                "profile_name": "dude_whats_the_bid"
            }
        )
        print(response.json())
        
        # 2. Train from HubSpot newsletters
        print("\n📧 Training from newsletters...")
        response = await client.post(
            f"{BASE_URL}/api/voice/training/hubspot-newsletters",
            json={
                "search_query": "freight marketer",
                "limit": 20
            }
        )
        print(response.json())
        
        # 3. Create voice profile
        print("\n🎨 Creating voice profile...")
        response = await client.post(
            f"{BASE_URL}/api/voice/training/create-profile",
            params={"profile_name": "custom_voice"}
        )
        print(response.json())
        
        # 4. Add contacts to queue
        print("\n👥 Adding contacts...")
        response = await client.post(
            f"{BASE_URL}/api/contact-queue/add-bulk",
            json={
                "contacts": [
                    {
                        "email": "prospect1@company.com",
                        "first_name": "John",
                        "last_name": "Doe",
                        "company": "Company Inc",
                        "job_title": "VP Operations",
                        "voice_profile": "custom_voice"
                    }
                ]
            }
        )
        contact_ids = response.json()["contact_ids"]
        print(f"Added {len(contact_ids)} contacts")
        
        # 5. Research each contact
        for contact_id in contact_ids:
            print(f"\n🔍 Researching {contact_id}...")
            response = await client.post(
                f"{BASE_URL}/api/contact-queue/{contact_id}/research"
            )
            print(response.json())
            
            # 6. Generate email proposals
            print(f"\n✉️ Generating proposals for {contact_id}...")
            response = await client.post(
                f"{BASE_URL}/api/contact-queue/{contact_id}/propose-email",
                params={"num_variants": 2}
            )
            proposals = response.json()["proposals"]
            print(f"Generated {len(proposals)} email variants")
            for p in proposals:
                print(f"\n--- Variant {p['variant']} ---")
                print(f"Subject: {p['subject']}")
                print(f"Body:\n{p['body']}")

if __name__ == "__main__":
    asyncio.run(complete_workflow())
```

---

## API Endpoints Reference

### Voice Training
- `POST /api/voice/training/youtube-videos` - Train from YouTube videos
- `POST /api/voice/training/hubspot-newsletters` - Train from HubSpot newsletters
- `POST /api/voice/training/samples` - Add manual training sample
- `POST /api/voice/training/analyze` - Analyze current samples
- `POST /api/voice/training/create-profile` - Create profile from analysis
- `GET /api/voice/training/status` - Check training status
- `POST /api/voice/training/clear` - Clear training samples

### Contact Queue
- `POST /api/contact-queue/add` - Add single contact
- `POST /api/contact-queue/add-bulk` - Add multiple contacts
- `GET /api/contact-queue/list` - List contacts (with filters)
- `GET /api/contact-queue/{contact_id}` - Get contact details
- `POST /api/contact-queue/{contact_id}/research` - Research contact
- `POST /api/contact-queue/{contact_id}/propose-email` - Generate email proposals
- `PATCH /api/contact-queue/{contact_id}/status` - Update contact status
- `DELETE /api/contact-queue/{contact_id}` - Remove from queue

### Voice Profiles
- `GET /api/voice/profiles` - List all profiles
- `GET /api/voice/profiles/{profile_id}` - Get specific profile
- `POST /api/voice/profiles` - Create new profile

---

## Tips & Best Practices

1. **Video Selection**: Choose videos that represent the style and tone you want
   - Videos must have captions/subtitles enabled
   - 3-5 videos is usually sufficient
   - Mix of different topics provides better training

2. **Newsletter Training**: 
   - Search queries should match your newsletter names exactly
   - 15-20 newsletters provides good coverage
   - Newer content may be more relevant

3. **Contact Queue**:
   - Prioritize contacts: 0=normal, 1=high, 2=urgent
   - Always research before generating emails
   - Review proposals before sending

4. **Voice Profiles**:
   - Test with small sample first
   - Compare variants to see what works
   - Iterate and refine based on response rates

---

## Troubleshooting

### "youtube-transcript-api not installed"
```bash
pip install youtube-transcript-api
```

### "No captions available for video"
- Video must have closed captions enabled
- Try auto-generated captions
- Use a different video

### "HubSpot connector not configured"
```bash
export HUBSPOT_API_KEY="your_api_key_here"
```

### "No newsletters found"
- Check search query matches exactly
- Verify HubSpot API key has marketing scope
- Try broader search term

---

## Next Steps

1. ✅ Train voice profiles from your content
2. ✅ Queue up target contacts
3. ✅ Research and generate proposals
4. 📧 Review and send emails
5. 📊 Track responses and iterate

Happy prospecting! 🚀
