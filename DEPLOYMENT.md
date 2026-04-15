# Deployment Guide

This guide covers deploying both the Backend (Flask API) and Frontend (React app).

---

## Runtime Baseline

- Backend deploy target should use Python `3.12`, matching `Backend/runtime.txt`.
- Backend dependencies are pinned in `Backend/requirements.txt`.
- After backend deployment, verify health at `/health` or `/api/health`.

## Best Fully Free Layout for This Project

For this specific prototype, the best free deployment layout is:

1. `Frontend`: Vercel `Hobby`
2. `Backend API`: Render free web service
3. `Database`: Supabase free Postgres
4. `Reminder emails`: Brevo free transactional email API over HTTPS
5. `Scheduled reminder trigger`: Windows Task Scheduler on the prototype machine (GitHub Actions optional)

For the Supabase-hosted always-on reminder route, see:

- `SUPABASE_BREVO_BABY_STEPS.md`

This layout is recommended because:

- Vercel Hobby is free and serves the PWA frontend well over HTTPS.
- Render free works for the Flask backend, but its free tier blocks outbound SMTP ports.
- Brevo's HTTP API avoids that SMTP restriction and keeps reminder emails working on a free backend.
- A free hosted Postgres database is more stable than relying on a temporary local database for deployment.
- For a dissertation prototype running from your own machine, Windows Task Scheduler is the preferred free scheduler because it does not require hosted secrets or a hosted database client path beyond the app itself.

---

## Backend Deployment (Flask API)

### Option 1: Render (Recommended - Free Tier Available)

1. Push your code to GitHub
2. Go to [render.com](https://render.com) and create account
3. Click "New" → "Web Service"
4. Connect your GitHub repo
5. Configure:
   - **Root Directory**: `Backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
6. Add Environment Variables:
   ```
   DB_NAME=your_db_name
   DB_USER=your_db_user
   DB_PASSWORD=your_db_password
   DB_HOST=your_db_host
   DB_PORT=5432
   DB_CONNECT_TIMEOUT=5
   DB_SSLMODE=require
   FLASK_DEBUG=false
   SESSION_TTL_HOURS=12
   CORS_ORIGINS=https://your-frontend-url.com
   GROQ_API_KEY=your_key_if_using_llm_features
   EMAIL_PROVIDER=brevo
   BREVO_API_KEY=your_brevo_api_key
   BREVO_FROM_EMAIL=your_verified_sender@example.com
   BREVO_FROM_NAME=Agentic AI Prototype
   ```
7. For database, use Render PostgreSQL or [Supabase](https://supabase.com) (free tier)
8. After deploy, open `https://your-backend-url/health` and confirm HTTP `200`

### Option 2: Heroku

1. Install Heroku CLI: https://devcenter.heroku.com/articles/heroku-cli
2. Login: `heroku login`
3. Create app: `heroku create your-app-name`
4. Add PostgreSQL: `heroku addons:create heroku-postgresql:mini`
5. Set environment variables:
   ```bash
   heroku config:set FLASK_DEBUG=false
   heroku config:set CORS_ORIGINS=https://your-frontend-url.com
   ```
6. Deploy:
   ```bash
   cd Backend
   git subtree push --prefix Backend heroku main
   ```

### Option 3: Railway

1. Go to [railway.app](https://railway.app)
2. Connect GitHub repo
3. Select Backend folder
4. Add PostgreSQL from Railway's database options
5. Railway auto-detects Flask and sets up deployment

---

## Frontend Deployment (React)

### Option 1: Vercel (Recommended)

1. Push your code to GitHub
2. Go to [vercel.com](https://vercel.com)
3. Import your GitHub repo
4. Configure:
   - **Root Directory**: `Frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `build`
5. Add Environment Variable:
   ```
   REACT_APP_API_URL=https://your-backend-url.com
   ```

### Option 2: Netlify

1. Go to [netlify.com](https://netlify.com)
2. Connect GitHub repo
3. Configure:
   - **Base directory**: `Frontend`
   - **Build command**: `npm run build`
   - **Publish directory**: `build`
4. Add redirect rule (create `Frontend/public/_redirects`):
   ```
   /api/*  https://your-backend-url.com/api/:splat  200
   ```

### Option 3: GitHub Pages

1. Install gh-pages: `npm install gh-pages --save-dev`
2. Add to package.json:
   ```json
   "homepage": "https://yourusername.github.io/your-repo",
   "scripts": {
     "predeploy": "npm run build",
     "deploy": "gh-pages -d build"
   }
   ```
3. Run: `npm run deploy`

### PWA Requirements

For the frontend to behave as a proper PWA after deployment, these conditions must be met:

1. The frontend must be served over `HTTPS`.
   - `localhost` works for local testing.
   - deployed PWA installability requires a secure origin.

2. The production build must be deployed, not the development server.
   - build locally with:
     ```bash
     cd Frontend
     npm.cmd run build
     ```
   - deploy the generated `Frontend/build` output.

3. These files must be publicly available from the frontend root:
   - `/manifest.json`
   - `/service-worker.js`
   - `/logo192.png`
   - `/logo512.png`

4. The frontend host must preserve SPA fallback to `index.html`.
   - the existing `Frontend/public/_redirects` supports this on Netlify-style hosts.

5. The backend API must also be reachable over `HTTPS`, and frontend environment variable `REACT_APP_API_URL` must point to that deployed backend.

### How to Confirm PWA Is Active

After deployment:

1. Open the deployed frontend URL in Chrome or Edge.
2. Open Developer Tools -> `Application`.
3. Check:
   - `Manifest` loads without icon errors
   - `Service Workers` shows the app service worker as installed/activated
   - `Cache Storage` contains the static/app caches
4. Refresh once after first load.
5. You should then be able to:
   - install the app from the browser menu
   - reload the basic shell offline
   - read previously cached API GET responses offline

### Current Offline Scope

The current PWA implementation provides:

- installable app shell
- cached frontend shell and static assets
- cached API GET responses for offline read fallback
- queued sync messaging for offline task actions

It does not make the entire backend fully offline. Features that require fresh server processing still need connectivity unless the relevant data has already been cached.

---

## Database Setup (PostgreSQL)

### Option 1: Supabase (Free)
1. Create account at [supabase.com](https://supabase.com)
2. Create new project
3. Go to Settings → Database → Connection string
4. Use the connection details in your environment variables

### Option 2: Render PostgreSQL
1. In Render dashboard, click "New" → "PostgreSQL"
2. Copy connection details to environment variables

### Option 3: ElephantSQL (Free)
1. Create account at [elephantsql.com](https://elephantsql.com)
2. Create new instance (Tiny Turtle - Free)
3. Copy connection URL

---

## Environment Variables Reference

### Backend (.env)
```
DB_NAME=your_database_name
DB_USER=your_database_user
DB_PASSWORD=your_database_password
DB_HOST=your_database_host
DB_PORT=5432
DB_CONNECT_TIMEOUT=5
DB_SSLMODE=require
FLASK_DEBUG=false
CORS_ORIGINS=https://your-frontend-domain.com
PORT=5000
SESSION_TTL_HOURS=12
GROQ_API_KEY=your_key_if_using_llm_features

# Recommended for free deployment on Render
EMAIL_PROVIDER=brevo
BREVO_API_KEY=your_brevo_api_key
BREVO_FROM_EMAIL=your_verified_sender@example.com
BREVO_FROM_NAME=Agentic AI Prototype

# Optional SMTP fallback for local/dev
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
SMTP_FROM=your_email@gmail.com
SMTP_USE_TLS=true
```

### Frontend
Update the API URL in your frontend code or use environment variable:
```
REACT_APP_API_URL=https://your-backend-url.com
```

---

## Automatic Email Reminder Schedule

The backend includes a scheduler-friendly reminder runner at `Backend/daily_reminder.py`.
It checks all users who have incomplete tasks due within the configured reminder window or already overdue and
then triggers the existing reminder workflow for each matching user. The default reminder
window is `5` days and can be changed with `REMINDER_LOOKAHEAD_DAYS` in `Backend/.env`
or with the `--days` command-line flag.

### Manual test

Run this first to confirm reminder emails work before scheduling automation:

```bash
.\.venv\Scripts\python.exe Backend/daily_reminder.py --days 5
```

If you want to test the reminder selection without sending email:

```bash
.\.venv\Scripts\python.exe Backend/daily_reminder.py --days 5 --no-send-email
```

### What it does

- selects users who have at least one incomplete task due within the next `5` days or already overdue
- skips users with no email address on file
- calls the existing `reminders:` workflow for each matching user
- sends a reminder email if SMTP is configured

### Windows Task Scheduler

On Windows, schedule it to run once per day. Example:

```powershell
schtasks /Create /SC DAILY /TN "AgenticAI-5DayReminders" /ST 08:00 /TR "\"C:\path\to\project\.venv\Scripts\python.exe\" \"C:\path\to\project\Backend\daily_reminder.py\" --days 5"
```

Replace `C:\path\to\project` with the real project path on the target machine.

Suggested schedule:

- run daily at `08:00`
- keep `--days 5` for a rolling 5-day countdown reminder window

This means a task due in five days can appear in daily reminder emails until it is completed, and overdue pending tasks can continue appearing until they are completed
or the deadline passes. If you only want to test a specific user, add:

```bash
--user-id 3
```

### Linux cron

On Linux, add a cron entry like this:

```cron
0 8 * * * /path/to/project/.venv/bin/python /path/to/project/Backend/daily_reminder.py --days 5 >> /path/to/project/logs/reminders.log 2>&1
```

This runs every day at `08:00` and appends output to a log file.

### Optional free scheduler: GitHub Actions

The repository also includes a scheduled workflow for cases where you want cloud-based automation and your database/email services are hosted:

- `.github/workflows/daily-reminders.yml`

It runs the reminder script once per day and can also be triggered manually from the
GitHub Actions tab.

To use it:

1. Push the repository to GitHub.
2. Open `Settings -> Secrets and variables -> Actions`.
3. Add the database and email secrets used by the workflow:
   - `DB_NAME`
   - `DB_USER`
   - `DB_PASSWORD`
   - `DB_HOST`
   - `DB_PORT`
   - `DB_CONNECT_TIMEOUT`
   - `DB_SSLMODE`
   - `EMAIL_PROVIDER`
   - `BREVO_API_KEY`
   - `BREVO_FROM_EMAIL`
   - `BREVO_FROM_NAME`
   - `REMINDER_LOOKAHEAD_DAYS`
4. Leave `EMAIL_PROVIDER=brevo` for a free Render deployment.

The default cron expression in the workflow is:

```yaml
0 15 * * *
```

That is `15:00 UTC` every day. Change it if you want a different reminder time.

### Email provider requirement

For a fully free deployment on Render, use Brevo API over HTTPS:

```env
EMAIL_PROVIDER=brevo
BREVO_API_KEY=your_brevo_api_key
BREVO_FROM_EMAIL=your_verified_sender@example.com
BREVO_FROM_NAME=Agentic AI Prototype
```

This is preferred because Render free blocks SMTP ports on free web services.

SMTP can still be used for local/dev or paid hosting:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
SMTP_FROM=your_email@gmail.com
SMTP_USE_TLS=true
```

Without a configured email provider, the script can still generate reminder output, but it will not send emails.

---

## Quick Deploy Checklist

- [ ] Database is set up and accessible
- [ ] Backend uses Python 3.12 from `Backend/runtime.txt`
- [ ] Backend environment variables are configured
- [ ] Backend `/health` or `/api/health` returns `200`
- [ ] Backend is deployed and running
- [ ] Frontend REACT_APP_API_URL points to backend
- [ ] CORS_ORIGINS in backend allows frontend domain
- [ ] Frontend is deployed and accessible

## Local Verification Commands

Backend:
```bash
.\.venv\Scripts\python.exe -m pytest -q Backend/test_langgraph_agent.py Backend/test_langgraph_agent_edge_cases.py Backend/test_app_api_edge_cases.py
```

Frontend:
```bash
cd Frontend
npm.cmd test -- --watchAll=false --runInBand
npm.cmd run build
```
