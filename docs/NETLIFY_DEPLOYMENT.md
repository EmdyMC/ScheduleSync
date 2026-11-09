# Deploying ScheduleSync on Netlify

This guide details how to deploy **ScheduleSync** on **Netlify** using Serverless Functions and Netlify's modern Edge CDN.

---

## ⚡ Architecture Overview

```
                      ┌───────────────────────────────────────────────┐
                      │              Netlify Edge CDN                 │
                      └──────────────────────┬────────────────────────┘
                                             │
                       ┌─────────────────────┴───────────────────────┐
                       │                                             │
                 Static Assets                               Serverless API
          (/static/*, CSS, JS, Fonts)                  (FastAPI via Mangum)
                       │                                             │
                       ▼                                             ▼
                 Browser Client                          netlify/functions/api.py
                                                                     │
                                                                     ▼
                                                          SQLite Database (/tmp)
                                                         (Auto-seeded on cold start)
```

1. **Frontend**: Static assets (`/static/css`, `/static/js`) and Jinja2 templates are bundled and served with instant cache invalidation via Netlify.
2. **Backend**: FastAPI runs via the [Mangum](https://mangum.io/) ASGI adapter on Netlify Serverless Functions (AWS Lambda).
3. **Database**: On serverless cold start, the application automatically provisions `schedulesync.db` in `/tmp` and populates all precomputed OCR timetables and demo accounts.
4. **Routing**: `netlify.toml` automatically handles rewrites and redirects so `/api/*`, `/share/*`, `/presentation`, and `/docs` routes route to the FastAPI handler seamlessly.

---

## 🚀 Option 1: One-Click Netlify Git Deployment

### Step 1: Push Repository to GitHub
Make sure your latest code is pushed to your GitHub repository:
```bash
git add .
git commit -m "Configure Netlify deployment and clean UI"
git push origin main
```

### Step 2: Connect to Netlify
1. Log in to [Netlify](https://app.netlify.com/).
2. Click **"Add new site"** &rarr; **"Import an existing project"**.
3. Choose **GitHub** and select your `ScheduleSync` repository.

### Step 3: Configure Build Settings
Netlify will automatically detect `netlify.toml` in the repository root. Ensure the settings match:
- **Build command:** `pip install -r requirements.txt`
- **Publish directory:** `app/static`
- **Functions directory:** `netlify/functions`

### Step 4: Environment Variables (Optional)
Under **Site configuration > Environment variables**, you can set:
| Variable | Default Value | Description |
|---|---|---|
| `SECRET_KEY` | *(Auto-generated)* | JWT signing secret |
| `NETLIFY` | `true` | Informs backend of serverless runtime |
| `PYTHON_VERSION` | `3.11` | Python runtime version |

Click **Deploy site**. In 1–2 minutes, your project is live at `https://<your-site-name>.netlify.app`!

---

## 🛠️ Option 2: Netlify CLI (Deploy from Terminal)

You can also deploy directly from your command line using the Netlify CLI:

```bash
# 1. Install Netlify CLI globally
npm install -g netlify-cli

# 2. Login to your Netlify account
netlify login

# 3. Test functions locally with Netlify Dev
netlify dev

# 4. Deploy to production
netlify deploy --prod
```

---

## 🌐 Hybrid Deployment: Netlify Frontend + Cloud Backend (Alternative)

If you plan to process real-time high-resolution OpenCV/Tesseract OCR on uploads (which requires C++ system libraries like `libtesseract`), the recommended production pattern is:

1. **Backend**: Deploy the FastAPI Docker container on **Railway** or **Render** (which has persistent disks and `apt-get install tesseract-ocr`).
2. **Frontend**: Deploy on **Netlify** for CDN speed, custom domains, and SSL.
3. Configure `netlify.toml` proxy rewrites:
   ```toml
   [[redirects]]
     from = "/api/*"
     to = "https://your-backend.onrender.com/api/:splat"
     status = 200
   ```
4. Set `window.SCHEDULESYNC_API_BASE = "https://your-backend.onrender.com/api"` if calling directly across domains.

---

## 📋 Verification Checklist

Once deployed, verify that:
- [ ] Root dashboard opens at `https://<your-site>.netlify.app/`
- [ ] Demo accounts log in instantly (e.g. Michael, Jack, Elena)
- [ ] 5×11 Heatmap renders with the 5-stop color gradient
- [ ] Academic schedule slot editor toggles slots smoothly
- [ ] Public share links work at `https://<your-site>.netlify.app/share/demo-team04`
- [ ] Presentation slides work at `https://<your-site>.netlify.app/presentation`
- [ ] FastAPI Swagger documentation is accessible at `https://<your-site>.netlify.app/docs`
