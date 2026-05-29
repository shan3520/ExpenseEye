# Deployment Guide

## Overview

ExpenseEye uses a **two-service architecture**:
- **Backend API**: Flask, deployed on Render
- **Frontend UI**: React + Vite, deployed on Cloudflare Pages

This guide walks through deploying both services from scratch.

---

## Prerequisites

- GitHub account
- Render account (free tier available)
- Cloudflare account (free tier available)
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
flask
flask-cors
pandas
numpy
```

### Step 2: Create Render Web Service

1. **Go to [Render Dashboard](https://dashboard.render.com/)**

2. **Click "New +" → "Web Service"**

3. **Connect your GitHub repository:**
   - Select "ExpenseEye" repository
   - Click "Connect"

4. **Configure the service:**

| Setting | Value |
|---------|-------|
| Name | `ExpenseEye-api` |
| Region | Choose closest to your users |
| Branch | `main` |
| Root Directory | (leave empty) |
| Runtime | `Python 3` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `python api/app.py` |

5. **Set environment variables:**
   - Click "Advanced"
   - Add environment variables:
     - `FLASK_ENV` = `production`
     - `CORS_ORIGINS` = your Cloudflare Pages URL, e.g. `https://expenseeye.pages.dev`
       (comma-separated for multiple origins; defaults to `*` if unset)

6. **Choose plan:**
   - Free tier is sufficient for testing
   - Upgrade to paid for production

7. **Click "Create Web Service"**

### Step 3: Verify Deployment

1. **Wait for build to complete** (2-3 minutes)

2. **Check logs** for:
```
Starting ExpenseEye API...
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

4. **Copy your Render URL** (e.g., `https://ExpenseEye-api.onrender.com`)

---

## Part 2: Frontend Deployment (Cloudflare Pages)

The frontend is a React + Vite single-page app in `viewer/`. It reads the API
base URL from the `VITE_API_URL` build-time environment variable.

### Step 1: Create the Pages Project

1. **Go to the [Cloudflare dashboard](https://dash.cloudflare.com/)** → **Workers & Pages** → **Create** → **Pages** → **Connect to Git**.

2. **Select the `shan3520/ExpenseEye` repository** and click **Begin setup**.

3. **Configure the build:**

| Setting | Value |
|---------|-------|
| Production branch | `main` |
| Framework preset | `Vite` |
| Root directory | `viewer` |
| Build command | `npm run build` |
| Build output directory | `dist` |

### Step 2: Set Environment Variables

Under **Settings → Environment variables**, add for the **Production** environment:

```
VITE_API_URL = https://your-render-app.onrender.com
```

> `VITE_API_URL` must be set **before** the build runs — Vite inlines it at
> build time. After changing it, trigger a new deploy.

### Step 3: Deploy

1. **Click "Save and Deploy".** Cloudflare installs deps, runs `npm run build`,
   and serves `dist/`. The `viewer/public/_redirects` file routes all paths to
   `index.html` for SPA behavior.

2. **Wait for the build** (1-2 minutes). Your app is live at
   `https://<project>.pages.dev`.

3. **Auto-deploys:** every push to `main` rebuilds automatically.

### Step 4: Verify Deployment

1. **Open** `https://<project>.pages.dev`.
2. **Upload a sample CSV**, confirm it processes and analytics display.
3. If requests fail with a CORS error in the browser console, make sure
   `CORS_ORIGINS` on the Render backend matches your Pages URL exactly.

---

## Part 3: Post-Deployment Configuration

### CORS (already configured)

CORS is enabled in `api/app.py` via `flask-cors`. The allowed origins are
controlled by the `CORS_ORIGINS` environment variable:

```python
# api/app.py
_cors_origins = os.getenv('CORS_ORIGINS', '*')
CORS(app, origins=_allowed_origins)
```

Set `CORS_ORIGINS` on Render to your Cloudflare Pages URL (comma-separated for
multiple), e.g.:

```
CORS_ORIGINS=https://expenseeye.pages.dev
```

If unset, it defaults to `*` (acceptable here since the API uses no
cookies/credentials, but pin it to your frontend origin for production).

### Set Up Custom Domain (Optional)

**For Render:**
1. Go to service settings
2. Click "Custom Domain"
3. Follow DNS configuration instructions

**For Cloudflare Pages:**
1. Go to the Pages project → **Custom domains**
2. Add your domain and follow the DNS instructions (free on any plan)

### Configure Environment-Specific Settings

For local backend development, create a `.env` (add to `.gitignore`):
```bash
FLASK_ENV=development
CORS_ORIGINS=http://localhost:5173
```

For the frontend, create `viewer/.env`:
```bash
VITE_API_URL=http://localhost:5000
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

**Cloudflare Pages:**
1. Go to the Pages project
2. Open **Deployments** → select a deployment → **View build log**

### Update Deployment

**Automatic (recommended):**
- Push to `main` branch
- Render and Cloudflare Pages auto-deploy

**Manual:**
- Render: Click "Manual Deploy" → "Deploy latest commit"
- Cloudflare Pages: Open the latest deployment → "Retry deployment"

### Rollback

**Render:**
1. Go to "Events" tab
2. Find previous successful deploy
3. Click "Redeploy"

**Cloudflare Pages:**
1. Open **Deployments**
2. Find a previous successful build → "..." → **Rollback to this deployment**

---

## Part 5: Scaling & Performance

### Backend Scaling (Render)

**Vertical Scaling:**
- Upgrade to higher tier for more RAM/CPU
- Recommended for 100+ concurrent users

**Horizontal Scaling:**
- Not needed for session-based architecture
- Each request is independent

### Frontend Scaling (Cloudflare Pages)

- Served as static assets from Cloudflare's global CDN
- No configuration needed
- Scales to millions of requests automatically

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

- [ ] HTTPS enabled (automatic on Render/Cloudflare Pages)
- [ ] VITE_API_URL uses HTTPS
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
- **Cause:** Wrong VITE_API_URL
- **Fix:** Verify the `VITE_API_URL` env var in Cloudflare Pages, then redeploy (Vite inlines it at build time)

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

**Cloudflare Pages (Free):**
- Unlimited static requests/bandwidth
- 500 builds/month
- Custom domains included

### Paid Tiers

**Render Starter ($7/month):**
- Always-on service
- Faster performance
- Custom domains

**Cloudflare Pages Pro ($20/month):**
- More concurrent builds
- Advanced analytics
- (Free tier is sufficient for most frontends)

### Expected Costs for Production

**Small scale (< 100 users/day):**
- Render: Free or $7/month
- Cloudflare Pages: Free
- **Total: $0-7/month**

**Medium scale (100-1000 users/day):**
- Render: $25/month
- Cloudflare Pages: Free
- **Total: $25/month**

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
   - Cloudflare Pages serves cached static assets
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
- Cloudflare Pages: https://developers.cloudflare.com/pages/
- GitHub Issues: https://github.com/shan3520/ExpenseEye/issues

---

**Last Updated:** 2024-12-19  
**Version:** 1.0.0
