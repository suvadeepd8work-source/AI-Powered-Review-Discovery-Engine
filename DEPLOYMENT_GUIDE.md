# Production Deployment Guide

This guide covers deploying the AI-Powered Review Discovery Engine to production using Vercel (frontend) and Render (backend).

---

## Architecture Overview

**Frontend:** Next.js 14 deployed on Vercel
**Backend:** FastAPI deployed on Render
**Database:** SQLite (can be upgraded to PostgreSQL for production)

---

## Prerequisites

- GitHub account with repository access
- Vercel account (free tier available)
- Render account (free tier available)
- Groq API key

---

## Step 1: Deploy Backend on Render

### 1.1 Create Render Project

1. Go to [render.com](https://render.com) and sign in
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Configure:
   - **Name:** `review-discovery-backend`
   - **Root Directory:** `phase4_backend_api`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn src.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type:** Free

### 1.2 Configure Environment Variables

In Render project settings, add these environment variables:

```bash
GROQ_API_KEY=your_groq_api_key_here
DB_CONN_STR=sqlite:///pipeline_state.db
ALLOWED_ORIGINS=https://your-vercel-app.vercel.app
SCHEDULE_TIME=10:00
SCHEDULE_DAY=mon
TIMEZONE=Asia/Kolkata
BATCH_SIZE_ANALYZER=15
BATCH_SIZE_CLUSTERING=50
BATCH_SIZE_SEGMENTATION=60
```

### 1.3 Deploy

1. Click "Create Web Service"
2. Wait for deployment to complete
3. Render will provide a URL like: `https://your-backend.onrender.com`
4. Copy this URL for frontend configuration

### 1.4 Verify Deployment

```bash
curl https://your-backend.onrender.com/
curl https://your-backend.onrender.com/api/health
```

---

## Step 2: Deploy Frontend on Vercel

### 2.1 Create Vercel Project

1. Go to [vercel.com](https://vercel.com) and sign in
2. Click "Add New..." → "Project"
3. Import your GitHub repository
4. Configure:
   - **Framework Preset:** Next.js
   - **Root Directory:** `phase5_frontend_ui`
   - **Build Command:** `npm run build` (auto-detected)
   - **Output Directory:** `.next` (auto-detected)

### 2.2 Configure Environment Variables

In Vercel project settings → Environment Variables, add:

```bash
NEXT_PUBLIC_API_BASE_URL=https://your-backend.onrender.com
```

### 2.3 Deploy

1. Click "Deploy"
2. Wait for deployment to complete
3. Vercel will provide a URL like: `https://your-app.vercel.app`

### 2.4 Update Backend CORS

Go back to Render and update the `ALLOWED_ORIGINS` environment variable:

```bash
ALLOWED_ORIGINS=https://your-app.vercel.app
```

Redeploy the backend to apply changes.

---

## Step 3: Configure GitHub Actions for Production

### 3.1 Update GitHub Secrets

Add these secrets to your GitHub repository (Settings → Secrets and variables → Actions):

```bash
GROQ_API_KEY=your_groq_api_key_here
BACKEND_URL=https://your-backend.onrender.com
FRONTEND_URL=https://your-app.vercel.app
```

### 3.2 Update GitHub Actions Workflow

The workflow will run weekly and can also be triggered manually. It will:
- Execute the pipeline
- Generate reports
- Upload artifacts

---

## Step 4: Verify Production Deployment

### 4.1 Test Backend

```bash
# Health check
curl https://your-backend.onrender.com/api/health

# Test endpoints
curl https://your-backend.onrender.com/api/reviews
curl https://your-backend.onrender.com/api/insights/themes
```

### 4.2 Test Frontend

1. Open your Vercel URL
2. Verify all pages load correctly
3. Test API integration
4. Check that data displays properly

### 4.3 Test Pipeline

```bash
# Trigger pipeline via API
curl -X POST https://your-backend.onrender.com/api/pipeline/run

# Check status
curl https://your-backend.onrender.com/api/pipeline/status/{run_id}
```

---

## Step 5: Monitor and Maintain

### 5.1 Monitoring

- **Render:** Monitor logs and resource usage
- **Vercel:** Monitor build logs and analytics
- **GitHub Actions:** Monitor workflow runs

### 5.2 Database Considerations

For production, consider migrating from SQLite to PostgreSQL:

1. Create PostgreSQL database on Render
2. Update `DB_CONN_STR` environment variable:
   ```bash
   DB_CONN_STR=postgresql://user:password@host:port/database
   ```
3. No code changes needed - SQLAlchemy handles both

### 5.3 Rate Limiting

Monitor Groq API usage:
- Free tier: 6000 TPM (tokens per minute)
- Upgrade to Dev Tier if needed for higher limits

---

## Troubleshooting

### Frontend Issues

**CORS errors:**
- Ensure `ALLOWED_ORIGINS` in backend includes your Vercel URL
- Redeploy backend after updating CORS settings

**API connection errors:**
- Verify `NEXT_PUBLIC_API_BASE_URL` is correct in Vercel
- Check backend is running and accessible
- Review Vercel build logs

### Backend Issues

**Deployment failures:**
- Check Railway/Render logs
- Verify all dependencies are in requirements.txt
- Ensure Python version is compatible

**Database errors:**
- Verify database file permissions
- Consider PostgreSQL for production
- Check database connection string

### GitHub Actions Issues

**Workflow failures:**
- Verify `GROQ_API_KEY` is set in GitHub Secrets
- Check workflow logs for specific errors
- Ensure all dependencies are installed

---

## Cost Summary

**Free Tier Limits:**

- **Vercel:**
  - 100GB bandwidth/month
  - Unlimited projects
  - Automatic SSL

- **Render:**
  - 750 hours/month free
  - 512MB RAM
  - Shared CPU

- **Groq API:**
  - Free tier: 6000 TPM
  - Dev Tier: Higher limits (paid)

---

## Security Checklist

- [x] API keys stored in environment variables
- [x] CORS configured for specific origins
- [x] .env files in .gitignore
- [x] No hardcoded secrets in code
- [x] HTTPS enabled (automatic on Vercel/Railway/Render)
- [ ] Regular API key rotation
- [ ] Monitor for suspicious activity

---

## Scaling Considerations

### When to Scale Up

- **Backend:** High API traffic or slow response times
  - Upgrade Railway/Render instance
  - Add load balancing
  - Implement caching

- **Database:** Large dataset or concurrent users
  - Migrate to PostgreSQL
  - Add connection pooling
  - Consider read replicas

- **Frontend:** High traffic
  - Vercel automatically scales
  - Consider CDN for static assets

---

## Backup and Recovery

### Database Backups

For SQLite:
- Regular file backups to cloud storage
- Export database periodically

For PostgreSQL:
- Enable automatic backups on Railway/Render
- Regular point-in-time recovery

### Code Backups

- GitHub repository serves as backup
- Tag releases for major versions
- Keep deployment configurations in version control

---

## Support and Documentation

- **Architecture:** `architecture.md`
- **Deployment Readiness:** `DEPLOYMENT_READINESS.md`
- **GitHub Actions:** `.github/README.md`
- **API Documentation:** Available at `/docs` endpoint on backend

---

## Next Steps

1. Deploy backend to Railway or Render
2. Deploy frontend to Vercel
3. Configure environment variables
4. Test all functionality
5. Set up monitoring
6. Document any custom configurations
7. Plan for scaling as needed
