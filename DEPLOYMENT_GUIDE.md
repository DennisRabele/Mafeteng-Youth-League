# Mafeteng Youth League - Deployment Guide

## Project Summary
- **Frontend:** Vite + HTML/CSS/JavaScript (Framework-less)
- **Backend:** FastAPI (Python)
- **Database:** Supabase (PostgreSQL)
- **File Storage:** Supabase Storage (Images & Documents)
- **Hosting:** Vercel (Frontend), Render/Railway (Backend)
- **Two Separate Apps:** Super Admin App + Team Admin App

---

## Phase 1: Pre-Deployment Preparation (2-3 Days)

### 1.1 Environment & Dependencies
**Tasks:**
- [ ] Create `.env.production` files for both apps
- [ ] Update database URLs to Supabase PostgreSQL
- [ ] Configure Cloudinary API credentials
- [ ] Set up SMTP email credentials (production account)
- [ ] Review and update all configuration files

**Time Estimate:** 4-6 hours

### 1.2 Database Migration to Supabase
**Steps:**
1. Create Supabase project
2. Create database dump from current SQLite/MySQL database
3. Create all tables in Supabase using SQLAlchemy models
4. Migrate data using Python scripts
5. Test data integrity

**Critical Updates Needed:**
- Update `app/db/session.py` to use Supabase PostgreSQL connection
- Update all SQLAlchemy models for PostgreSQL compatibility
- Add migration script for loan tracking fields:
  ```sql
  ALTER TABLE players ADD COLUMN is_on_loan BOOLEAN DEFAULT FALSE;
  ALTER TABLE players ADD COLUMN original_team_id INTEGER REFERENCES teams(team_id);
  ALTER TABLE players ADD COLUMN loan_end_date DATE;
  
  ALTER TABLE player_transfer_requests ADD COLUMN rejection_reason TEXT;
  ALTER TABLE player_transfer_requests ADD COLUMN consent_form_uploaded BOOLEAN DEFAULT FALSE;
  ALTER TABLE player_transfer_requests ADD COLUMN loan_end_date DATE;
  ALTER TABLE player_transfer_requests ADD COLUMN approved_by_super_admin_at TIMESTAMP;
  
  ALTER TABLE player_transfer_requests DROP COLUMN status;
  -- Transfer status now uses approval_status enum
  ```

**Time Estimate:** 8-12 hours

### 1.3 Supabase Storage Configuration
**Setup:**
1. Create the Supabase buckets:
   - `player photos` - Player profile pictures
   - `player documents` - Identity docs, medical certs
   - `player agreements` - Consent forms
   - `team logos` - Team logos
   - `admin photos` - Admin profile pictures
2. Make each bucket public in Supabase Storage.
3. Set `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` in `.env` or your hosting dashboard.
4. Keep `app/services/storage.py` pointed at Supabase Storage so uploads return public URLs.

**Time Estimate:** 3-4 hours

### 1.4 Email Service Configuration
**Update for Production:**
- Switch from development SMTP to production email service
- Options:
  - SendGrid
  - Mailgun
  - AWS SES
  - Gmail (with app-specific password)

**Current Config Location:** `app/services/email.py`

**Time Estimate:** 2-3 hours

---

## Phase 2: Backend Deployment (1-2 Days)

### 2.1 Choose Hosting Provider

#### Option A: Render.com (Recommended)
- ✅ Easy PostgreSQL integration with Supabase
- ✅ Free tier available
- ✅ Built-in environment variables
- ✅ Auto-deploy from GitHub
- Pricing: $7/month (Starter), $25/month (Standard)

#### Option B: Railway.app
- ✅ Simple deployment
- ✅ Good Supabase integration
- ✅ Usage-based pricing
- Pricing: $5 minimum, then usage

#### Option C: Heroku Alternative (Replit, Fly.io)
- Various pricing models

### 2.2 Prepare Backend for Deployment
**File Structure:**
```
requirements.txt          # Include all dependencies
runtime.txt              # Specify Python version: 3.11
.env.production          # Production environment vars
Procfile                 # For Heroku/Render
```

**Update `requirements.txt`:**
```
fastapi==0.104.1
uvicorn==0.24.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9   # PostgreSQL adapter
cloudinary==1.35.0
python-multipart==0.0.6
python-dotenv==1.0.0
email-validator==2.1.0
pydantic==2.5.0
# ... add all other dependencies
```

**Create `Procfile`:**
```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

**Time Estimate:** 2-3 hours

### 2.3 Deploy to Render/Railway
**Steps:**
1. Push code to GitHub
2. Connect GitHub to Render/Railway
3. Configure environment variables:
   ```
   DATABASE_URL=postgresql://...
   CLOUDINARY_CLOUD_NAME=...
   CLOUDINARY_API_KEY=...
   CLOUDINARY_API_SECRET=...
   SMTP_HOST=...
   SMTP_USER=...
   SMTP_PASSWORD=...
   APP_MODE=combined  # or super_admin, team_admin
   ```
4. Deploy
5. Run database migrations:
   ```
   python -m alembic upgrade head
   ```

**Time Estimate:** 2-4 hours (first deployment), 30 mins (subsequent)

### 2.4 Backend Testing
- [ ] Test all API endpoints
- [ ] Verify email notifications work
- [ ] Check file uploads to Cloudinary
- [ ] Test database queries
- [ ] Monitor error logs

**Time Estimate:** 4-6 hours

---

## Phase 3: Frontend Deployment to Vercel (1 Day)

### 3.1 Prepare Frontend
**Create Vite Config Files:**

`super_admin/vite.config.js`:
```javascript
import { defineConfig } from 'vite'

export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'https://your-backend-url.com',
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: false
  }
})
```

`team_admin/vite.config.js`:
```javascript
import { defineConfig } from 'vite'

export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'https://your-backend-url.com',
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: false
  }
})
```

**Create `.env.production`:**
```
VITE_API_URL=https://your-backend-url.com
VITE_APP_MODE=super_admin  # or team_admin
```

**Time Estimate:** 2-3 hours

### 3.2 Deploy to Vercel
**Steps:**
1. Push code to GitHub (separate repos recommended)
2. Import project to Vercel
3. Configure build settings:
   - Framework: Vite
   - Build Command: `npm run build`
   - Output Directory: `dist`
4. Add environment variables in Vercel dashboard
5. Deploy

**Deployment Urls:**
- Super Admin: `https://mafeteng-super-admin.vercel.app`
- Team Admin: `https://mafeteng-team-admin.vercel.app`

**Time Estimate:** 1-2 hours

---

## Phase 4: Post-Deployment (1-2 Days)

### 4.1 Testing & Verification
- [ ] Test user login flow
- [ ] Verify email verification codes
- [ ] Test player registration with photo upload
- [ ] Test transfer workflow
- [ ] Verify loan tracking
- [ ] Test cross-team transfers
- [ ] Check admin approval workflows
- [ ] Monitor error logs

**Time Estimate:** 6-8 hours

### 4.2 Data Backup & Security
- [ ] Setup automatic database backups (Supabase)
- [ ] Configure Cloudinary backup
- [ ] Setup monitoring & alerts
- [ ] Enable HTTPS everywhere
- [ ] Configure CORS properly
- [ ] Setup rate limiting
- [ ] Enable database encryption

**Time Estimate:** 2-4 hours

### 4.3 Performance Optimization
- [ ] Enable CDN for static files
- [ ] Setup caching headers
- [ ] Optimize database queries
- [ ] Monitor API response times
- [ ] Setup load testing

**Time Estimate:** 4-6 hours

### 4.4 Documentation
- [ ] API documentation (Swagger/OpenAPI)
- [ ] User guides for admins
- [ ] System architecture documentation
- [ ] Troubleshooting guide

**Time Estimate:** 4-6 hours

---

## Phase 5: Continuous Deployment (Ongoing)

### 5.1 CI/CD Pipeline
**Setup GitHub Actions:**
```yaml
name: Deploy to Render

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Deploy to Render
        run: |
          curl -X POST https://api.render.com/deploy/srv-xxxxx?key=${{ secrets.RENDER_DEPLOY_KEY }}
```

**Time Estimate:** 2-3 hours setup

### 5.2 Monitoring & Maintenance
- [ ] Daily log reviews
- [ ] Weekly performance reports
- [ ] Monthly security updates
- [ ] Database optimization
- [ ] User feedback collection

---

## Estimated Total Timeline

| Phase | Tasks | Estimate | Notes |
|-------|-------|----------|-------|
| Phase 1 | Pre-Deployment Prep | 2-3 days | Database migration is critical |
| Phase 2 | Backend Deployment | 1-2 days | Testing is crucial |
| Phase 3 | Frontend Deployment | 1 day | Usually fastest phase |
| Phase 4 | Testing & Security | 1-2 days | Don't skip this! |
| Phase 5 | CI/CD Setup | 0.5 day | Optional but recommended |
| **TOTAL** | **All Phases** | **5-9 days** | **1-2 weeks realistic** |

---

## Cost Estimates (Monthly)

| Service | Cost | Notes |
|---------|------|-------|
| Supabase | $25-100 | Database + backups |
| Cloudinary | $15-50 | File storage (pay as you grow) |
| Render/Railway | $7-50 | Backend hosting |
| Vercel | Free-$20 | Frontend (free tier sufficient) |
| Email Service | $10-50 | SendGrid/Mailgun |
| Domain | $10-15 | Annual DNS |
| **TOTAL** | **$67-285** | **Scales with usage** |

---

## Important Considerations

### Database Relationships to Preserve
✅ **Keep these relationships:**
- User → TeamAdmin/SuperAdmin
- TeamAdmin → Teams
- Team → Players
- Player → Documents
- Player → RegistrationRequests
- PlayerTransferRequest → From/To Teams

### New Fields for Loan Tracking
✅ **Ensure migration includes:**
- `players.is_on_loan` (boolean)
- `players.original_team_id` (foreign key)
- `players.loan_end_date` (date)
- `player_transfer_requests.rejection_reason` (text)
- `player_transfer_requests.consent_form_uploaded` (boolean)

### Critical Configurations
⚠️ **Don't forget:**
- Set `CORS_ORIGINS` for frontend URLs
- Enable HTTPS
- Set secure session cookies
- Configure email verification codes expiry
- Set login code expiry to 10 minutes

---

## Rollback Plan

If deployment fails:
1. Keep previous version deployed
2. Check logs for errors
3. Fix issues in development
4. Test thoroughly before re-deployment
5. Use blue-green deployment if possible

---

## Success Checklist

- [ ] Database fully migrated to Supabase
- [ ] All files uploadable to Cloudinary
- [ ] Email notifications working
- [ ] Admin login & verification working
- [ ] Team registration workflow complete
- [ ] Player registration with photos working
- [ ] Transfer workflow (pending→approved→rejected) working
- [ ] Loan tracking active
- [ ] All tests passing
- [ ] Performance acceptable (<1s response time)
- [ ] Error monitoring setup
- [ ] Backups configured
- [ ] Users can access both apps

---

## Contact & Support

For deployment issues:
1. Check Vercel/Render logs
2. Review Supabase database logs
3. Check Cloudinary API logs
4. Review application error logs
5. Contact service providers' support

---

**Last Updated:** 2026-06-16  
**Deployment Complexity:** ⭐⭐⭐⭐ (Moderate-High - Database migration is complex)
