# Deployment Guide

This guide covers deploying both the Backend (Flask API) and Frontend (React app).

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
   FLASK_DEBUG=false
   CORS_ORIGINS=https://your-frontend-url.com
   ```
7. For database, use Render PostgreSQL or [Supabase](https://supabase.com) (free tier)

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
   - **Publish directory**: `Frontend/build`
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
FLASK_DEBUG=false
CORS_ORIGINS=https://your-frontend-domain.com
PORT=5000

# Optional: Email reminders
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

## Quick Deploy Checklist

- [ ] Database is set up and accessible
- [ ] Backend environment variables are configured
- [ ] Backend is deployed and running
- [ ] Frontend REACT_APP_API_URL points to backend
- [ ] CORS_ORIGINS in backend allows frontend domain
- [ ] Frontend is deployed and accessible
