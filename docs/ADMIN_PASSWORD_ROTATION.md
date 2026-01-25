# Admin Password Rotation Guide

**Status:** ✅ SECURE - Production is using a strong admin password

## Immediate Action Required

The admin password must be changed in Railway's environment variables.

### Step 1: Access Railway Dashboard
1. Go to https://railway.app
2. Open project: `ideal-fascination`
3. Select service: `web`
4. Click on "Variables" tab

### Step 2: Update ADMIN_PASSWORD
1. Find `ADMIN_PASSWORD` variable
2. Ensure a strong password is set (see below)
3. Click "Deploy" or save changes

### Generated Secure Password
```
t5MDoLbY1HOqWY0AlsIZ7gvKFmqST9PGs-LBxwHgSVM
```

**OR** generate your own:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Step 3: Verify the Change
```bash
# Old password should fail (401)
# (If you see 401, rotation is complete)
curl -s -H "X-Admin-Token: test123" https://web-production-a6ccf.up.railway.app/api/gdpr/status

# New password should work (200)
curl -s -H "X-Admin-Token: YOUR_NEW_PASSWORD" https://web-production-a6ccf.up.railway.app/api/gdpr/status
```

### Step 4: Store Password Securely
- Add to 1Password, LastPass, or similar password manager
- Never commit to git
- Share via secure channel only

## Endpoints Requiring Admin Token

These endpoints require `X-Admin-Token` header:
- `GET /api/gdpr/status` - GDPR compliance status
- `POST /api/gdpr/delete/{email}` - Delete user data
- `POST /api/admin/emergency-stop` - Kill switch
- `POST /api/admin/trigger-poll` - Manual signal refresh

## Password Requirements
- Minimum 32 characters
- URL-safe characters only (a-z, A-Z, 0-9, -, _)
- Generated cryptographically (not human-chosen)

---
**Last Updated:** 2026-01-24
**Sprint:** 7.2
