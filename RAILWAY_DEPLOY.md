# Railway Deployment Guide for JARVIS

## Quick Deploy to Railway

### 1. Install Railway CLI (if not already installed)
```bash
npm i -g @railway/cli
# or
curl -fsSL https://railway.app/install.sh | sh
```

### 2. Login to Railway
```bash
railway login
```

### 3. Link to your project (or create new)
```bash
# If project exists:
railway link

# If creating new:
railway init
```

### 4. Set Environment Variables
```bash
# Required
railway variables set OPENAI_API_KEY="your-openai-api-key"
railway variables set HUBSPOT_API_KEY="your-hubspot-api-key"

# Optional (already have defaults)
railway variables set DATABASE_URL="postgresql://..."
railway variables set REDIS_URL="redis://..."

# Set expected form ID
railway variables set EXPECTED_HUBSPOT_FORM_ID="db8b22de-c3d4-4fc6-9a16-011fe322e82c"

# Production mode
railway variables set API_ENV="production"
railway variables set LOG_LEVEL="INFO"
```

### 5. Deploy!
```bash
railway up
```

That's it! Railway will:
- Build the Docker image
- Run database migrations
- Start the app on a public URL
- Provide SSL/HTTPS automatically

### 6. Get Your Public URL
```bash
railway domain
```

### 7. Access JARVIS
Your JARVIS interface will be live at:
```
https://your-app.railway.app/jarvis
```

## Environment Variables Needed

**Required:**
- `OPENAI_API_KEY` - For voice transcription and AI parsing
- `HUBSPOT_API_KEY` - For fetching contacts and forms

**Optional (auto-configured):**
- `DATABASE_URL` - Railway provides PostgreSQL automatically
- `REDIS_URL` - For caching and queues
- `PORT` - Railway sets this automatically

## Features Available on Public URL

✅ **JARVIS Voice Approval** - `/jarvis`  
✅ **Voice Profiles** - `/voice-profiles`  
✅ **API Documentation** - `/docs`  
✅ **Main Dashboard** - `/`  
✅ **Agents Panel** - `/agents`  

## Post-Deployment Steps

1. **Load Email Drafts**
   ```bash
   # SSH into Railway container
   railway run python scripts/load_drafts_to_jarvis.py
   ```

2. **Test JARVIS**
   - Open `https://your-app.railway.app/jarvis`
   - Click microphone or type a command
   - Verify voice approval works

3. **Share with Team**
   - Anyone can access the public URL
   - Mobile devices work great for voice commands
   - Approve emails from anywhere!

## Monitoring

```bash
# View logs
railway logs

# Check status
railway status

# Open in browser
railway open
```

## Scaling

Railway auto-scales based on usage. For high traffic:
```bash
# Upgrade plan in Railway dashboard
# Add more instances if needed
```

## Custom Domain

To use your own domain:
1. Go to Railway dashboard
2. Click on your service
3. Settings → Domains
4. Add custom domain
5. Update DNS records as shown

Example: `jarvis.yourdomain.com`

## Troubleshooting

**Issue**: Voice not working on mobile  
**Fix**: Ensure you're using HTTPS (Railway provides this automatically)

**Issue**: Database connection errors  
**Fix**: Railway auto-provisions PostgreSQL. Check `railway variables` to see DATABASE_URL

**Issue**: Audio upload fails  
**Fix**: Check file size limits. Railway has 50MB limit by default.

## Security Notes

- All traffic is HTTPS by default
- Environment variables are encrypted
- Voice data is processed via OpenAI (ephemeral, not stored)
- Database credentials auto-rotated by Railway

---

**Ready to deploy?** Run `railway up` and you'll have JARVIS live in ~2 minutes! 🚀
