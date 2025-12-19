# Deployment Guide

## Overview

SmartSpend uses a **two-service architecture**:
- **Backend API**: Deployed on Render
- **Frontend UI**: Deployed on Streamlit Cloud

This guide walks through deploying both services from scratch.

---

## Prerequisites

- GitHub account
- Render account (free tier available)
- Streamlit Cloud account (free tier available)
- Git installed locally

---

## Part 1: Backend Deployment (Render)

### Step 1: Prepare Repository

1. **Ensure your code is pushed to GitHub:**
```bash
git add .
git commit -m "Prepare for deployment"
git push origin main
```

2. **Verify `requirements.txt` exists in root:**
```txt
flask==3.0.0
pandas==2.1.3
werkzeug==3.0.1
```

### Step 2: Create Render Web Service

1. **Go to [Render Dashboard](https://dashboard.render.com/)**

2. **Click "New +" → "Web Service"**

3. **Connect your GitHub repository:**
   - Select "smartspend" repository
   - Click "Connect"

4. **Configure the service:**

| Setting | Value |
|---------|-------|
| Name | `smartspend-api` |
| Region | Choose closest to your users |
| Branch | `main` |
| Root Directory | (leave empty) |
| Runtime | `Python 3` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `python api/app.py` |

5. **Set environment variables:**
   - Click "Advanced"
   - Add environment variable:
     - Key: `FLASK_ENV`
     - Value: `production`

6. **Choose plan:**
   - Free tier is sufficient for testing
   - Upgrade to paid for production

7. **Click "Create Web Service"**

### Step 3: Verify Deployment

1. **Wait for build to complete** (2-3 minutes)

2. **Check logs** for:
```
Starting SmartSpend API...
Available endpoints:
  GET  /health
  POST /upload
  ...
Listening on http://0.0.0.0:5000
```

3. **Test health endpoint:**
```bash
curl https://your-app-name.onrender.com/health
```

Expected response:
```json
{"status": "ok"}
```

4. **Copy your Render URL** (e.g., `https://smartspend-api.onrender.com`)

---

## Part 2: Frontend Deployment (Streamlit Cloud)

### Step 1: Prepare Streamlit App

1. **Ensure `viewer/requirements.txt` exists:**
```txt
streamlit==1.29.0
requests==2.31.0
pandas==2.1.3
```

2. **Update API URL in `viewer/app.py`:**

Option A: Use Streamlit secrets (recommended)
```python
# In viewer/app.py
import streamlit as st

API_BASE_URL = st.secrets.get("API_BASE_URL", "http://localhost:5000")
```

Option B: Hardcode (not recommended for production)
```python
API_BASE_URL = "https://your-render-app.onrender.com"
```

### Step 2: Deploy to Streamlit Cloud

1. **Go to [Streamlit Cloud](https://share.streamlit.io/)**

2. **Click "New app"**

3. **Configure deployment:**

| Setting | Value |
|---------|-------|
| Repository | `shan3520/smartspend` |
| Branch | `main` |
| Main file path | `viewer/app.py` |
| App URL | `smartspend` (or custom) |

4. **Add secrets (if using Option A):**
   - Click "Advanced settings"
   - Add to secrets:
```toml
API_BASE_URL = "https://your-render-app.onrender.com"
```

5. **Click "Deploy!"**

### Step 3: Verify Deployment

1. **Wait for deployment** (1-2 minutes)

2. **Access your app** at `https://smartspend.streamlit.app`

3. **Test CSV upload:**
   - Upload a sample CSV
   - Verify it processes successfully
   - Check analytics display

---

## Part 3: Post-Deployment Configuration

### Enable CORS (if needed)

If frontend and backend are on different domains, add CORS to `api/app.py`:

```python
from flask_cors import CORS

app = Flask(__name__)
CORS(app, origins=["https://smartspend.streamlit.app"])
```

Update `requirements.txt`:
```txt
flask-cors==4.0.0
```

### Set Up Custom Domain (Optional)

**For Render:**
1. Go to service settings
2. Click "Custom Domain"
3. Follow DNS configuration instructions

**For Streamlit:**
1. Upgrade to paid plan
2. Configure custom domain in settings

### Configure Environment-Specific Settings

Create `.env` file for local development (add to `.gitignore`):
```bash
FLASK_ENV=development
API_BASE_URL=http://localhost:5000
```

---

## Part 4: Monitoring & Maintenance

### Health Checks

**Render automatically monitors:**
- HTTP health check on `/health`
- Restarts service if unhealthy
- Sends email alerts

**Manual health check:**
```bash
curl https://your-api.onrender.com/health
```

### View Logs

**Render:**
1. Go to service dashboard
2. Click "Logs" tab
3. Filter by error level

**Streamlit:**
1. Go to app dashboard
2. Click "Manage app"
3. View logs in real-time

### Update Deployment

**Automatic (recommended):**
- Push to `main` branch
- Render and Streamlit auto-deploy

**Manual:**
- Render: Click "Manual Deploy" → "Deploy latest commit"
- Streamlit: Click "Reboot app"

### Rollback

**Render:**
1. Go to "Events" tab
2. Find previous successful deploy
3. Click "Redeploy"

**Streamlit:**
1. Revert Git commit
2. Push to trigger redeploy

---

## Part 5: Scaling & Performance

### Backend Scaling (Render)

**Vertical Scaling:**
- Upgrade to higher tier for more RAM/CPU
- Recommended for 100+ concurrent users

**Horizontal Scaling:**
- Not needed for session-based architecture
- Each request is independent

### Frontend Scaling (Streamlit)

- Streamlit Cloud auto-scales
- No configuration needed
- Handles 1000s of concurrent users

### Database Considerations

**Current:** Ephemeral SQLite in `/tmp`
- ✅ Perfect for session-based usage
- ✅ No external database needed
- ❌ Lost on service restart (expected)

**Future:** For persistent storage
- Migrate to PostgreSQL (Render add-on)
- Update `core/loader.py` to use SQLAlchemy

---

## Part 6: Security Checklist

### Before Going Live

- [ ] HTTPS enabled (automatic on Render/Streamlit)
- [ ] API_BASE_URL uses HTTPS
- [ ] File size limits configured (10MB)
- [ ] CORS properly configured
- [ ] No secrets in code (use environment variables)
- [ ] `.gitignore` excludes sensitive files
- [ ] Error messages don't leak sensitive data
- [ ] Health check endpoint is public
- [ ] Upload endpoint validates file types

### Production Hardening

- [ ] Rate limiting on `/upload` endpoint
- [ ] Request timeout configuration
- [ ] Disk space monitoring for `/tmp`
- [ ] Logging for security events
- [ ] Regular dependency updates

---

## Part 7: Troubleshooting

### Common Issues

**Issue:** "Connection refused" from frontend
- **Cause:** Wrong API_BASE_URL
- **Fix:** Verify URL in Streamlit secrets

**Issue:** "File too large" error
- **Cause:** Exceeds 10MB limit
- **Fix:** Increase `MAX_CONTENT_LENGTH` in Flask config

**Issue:** "Module not found" on Render
- **Cause:** Missing dependency in `requirements.txt`
- **Fix:** Add missing package and redeploy

**Issue:** Slow CSV processing
- **Cause:** Large file or complex parsing
- **Fix:** Upgrade Render tier for more CPU

**Issue:** Database file not found
- **Cause:** Session expired or service restarted
- **Fix:** Re-upload CSV (expected behavior)

### Debug Mode

**Enable debug logging in production (temporarily):**

```python
# In api/app.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

**View detailed logs in Render dashboard**

---

## Part 8: Cost Estimation

### Free Tier Limits

**Render (Free):**
- 750 hours/month
- Spins down after 15 min inactivity
- Slower cold starts

**Streamlit Cloud (Free):**
- Unlimited apps
- Community support
- Public apps only

### Paid Tiers

**Render Starter ($7/month):**
- Always-on service
- Faster performance
- Custom domains

**Streamlit Cloud Team ($250/month):**
- Private apps
- Custom domains
- Priority support

### Expected Costs for Production

**Small scale (< 100 users/day):**
- Render: Free or $7/month
- Streamlit: Free
- **Total: $0-7/month**

**Medium scale (100-1000 users/day):**
- Render: $25/month
- Streamlit: Free or $250/month
- **Total: $25-275/month**

---

## Part 9: Backup & Disaster Recovery

### Code Backup
- ✅ GitHub repository (automatic)
- ✅ Version control with Git
- ✅ Easy rollback

### Data Backup
- ⚠️ No persistent data (by design)
- ⚠️ Users must re-upload CSV after session

### Disaster Recovery Plan

1. **Service outage:**
   - Render auto-restarts
   - Streamlit auto-recovers
   - No data loss (ephemeral by design)

2. **Code corruption:**
   - Rollback to previous Git commit
   - Redeploy from GitHub

3. **Complete failure:**
   - Redeploy from scratch (< 10 minutes)
   - No data migration needed

---

## Part 10: Next Steps

After successful deployment:

1. **Test with real data**
   - Upload actual bank statements
   - Verify analytics accuracy
   - Check performance

2. **Monitor usage**
   - Track upload success rate
   - Monitor error logs
   - Analyze user feedback

3. **Iterate**
   - Add support for new CSV formats
   - Improve analytics algorithms
   - Enhance UI/UX

4. **Scale**
   - Upgrade tiers as needed
   - Add caching if needed
   - Optimize database queries

---

## Support

For deployment issues:
- Render: https://render.com/docs
- Streamlit: https://docs.streamlit.io/streamlit-cloud
- GitHub Issues: https://github.com/shan3520/smartspend/issues

---

**Last Updated:** 2024-12-19  
**Version:** 1.0.0
