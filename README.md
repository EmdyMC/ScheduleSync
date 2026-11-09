# 🗓️ ScheduleSync: Academic Timetable Aggregator & Common Free Time Analyzer

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-3ECF8E.svg?style=flat&logo=supabase&logoColor=white)](https://supabase.com)
[![Netlify](https://img.shields.io/badge/Netlify-Ready-00C7B7.svg?style=flat&logo=netlify&logoColor=white)](https://www.netlify.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?style=flat&logo=docker&logoColor=white)](https://www.docker.com)

**ScheduleSync** is a full-stack web application designed for university students to aggregate academic timetables, identify overlapping courses, and calculate real-time common free times for project teams, study groups, and clubs.

---

## 🌟 Key Features

- 🔐 **Secure Authentication:** JWT and bcrypt-hashed authentication with customizable student profiles (registration number, campus, avatars).
- 📅 **Interactive Schedule Editor:**
  - **Visual 5×11 Slot Grid:** Instant slot toggling (Mon–Fri, 8:00 AM – 5:35 PM) with standard university slot codes (`A1`, `B1`, `L1–L58`), and bulk actions (*Mark All Free*, *Mark All Busy*).
  - **Computer Vision OCR Uploader:** Upload timetable screenshots; automatically scans course cells using OpenCV and Tesseract OCR to populate the matrix.
- 👥 **Student Social Network:**
  - Real-time search by username, full name, or registration number.
  - Send, accept, and manage friend requests.
  - Multi-select friend comparison to immediately view shared availability.
- 👥 **Project Teams & Study Groups:**
  - Create study groups with auto-generated invite codes (e.g. `HACK26`, `STUDY4`).
  - Manage member roles (Admin / Member).
  - Generate aggregated group availability heatmaps with 100% free meeting windows.
- 🔥 **Availability Heatmap Engine:**
  - 5-stop color gradient indicating free/busy ratios (Green = 100% Free, Amber = Partial, Red = All Busy).
  - Cell click inspection modal showing available vs. in-class members.
  - Automatic best meeting slot recommendation banner.
- 🔗 **Public Share Links:** Generate tokenized public links to share read-only heatmaps with external collaborators (`/share/<token>`).
- 🗄️ **Production-Ready Database:** Native support for **Supabase (PostgreSQL)** with seamless local SQLite fallback for offline development.

---

## 🚀 Quickstart & Local Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment (Optional)
To connect to **Supabase (PostgreSQL)**, set `DATABASE_URL` in your environment or a `.env` file:
```env
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
SECRET_KEY=your-production-secret-jwt-key
```
*(If `DATABASE_URL` is omitted, the app will automatically use a local SQLite database).*

### 3. Seed Database with Realistic Data
```bash
python database/seed_data.py
```

### 4. Run the Application
```bash
python run.py
```

- **Web Dashboard:** Open [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **API Swagger Documentation:** Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## ☁️ Deployment

### 1. Supabase (Database)
1. Create a project at [supabase.com](https://supabase.com).
2. Run [`database/supabase_schema.sql`](file:///database/supabase_schema.sql) in the Supabase SQL Editor.
3. Copy your project connection URI from **Project Settings > Database**.
4. See [docs/SUPABASE_SETUP.md](file:///docs/SUPABASE_SETUP.md) for full instructions.

### 2. Netlify Deployment
ScheduleSync is configured with [`netlify.toml`](file:///netlify.toml) and [`netlify/functions/api.py`](file:///netlify/functions/api.py):
1. Connect your repository to Netlify.
2. In **Site configuration > Environment variables**, add `DATABASE_URL` pointing to your Supabase instance and `SECRET_KEY`.
3. Deploy! Netlify will automatically build the site and deploy FastAPI via the Mangum serverless adapter.
4. See [docs/NETLIFY_DEPLOYMENT.md](file:///docs/NETLIFY_DEPLOYMENT.md) for details.

### 3. Docker / Cloud Containers (Render, Railway, Fly.io)
Deploy using the included [`Dockerfile`](file:///Dockerfile):
```bash
docker build -t schedulesync .
docker run -p 8000:8000 -e DATABASE_URL="<your-supabase-url>" schedulesync
```

---

## 📁 Project Structure

```text
ScheduleSync/
├── app/
│   ├── config.py           # Configuration, Supabase detection & slot matrices
│   ├── database.py         # Database connection proxy (Supabase PG + SQLite)
│   ├── auth.py             # Bcrypt hashing & JWT token dependencies
│   ├── schemas.py          # Pydantic validation models
│   ├── ocr_service.py      # OpenCV & Tesseract OCR timetable parser
│   ├── heatmap_service.py  # Free-time relational aggregation engine
│   ├── routers/            # Modular FastAPI route controllers
│   ├── static/             # Frontend styles & Vanilla JS client
│   └── templates/          # Jinja2 HTML templates (Dashboard & Share)
├── database/
│   ├── supabase_schema.sql # Production Supabase PostgreSQL schema
│   ├── schema.sql          # Local SQLite development schema
│   ├── seed_data.py        # Database seeder with realistic test schedules
│   └── precomputed_timetables.json # Precomputed timetable matrices
├── docs/
│   ├── SUPABASE_SETUP.md      # Supabase setup & connection guide
│   ├── NETLIFY_DEPLOYMENT.md  # Step-by-step Netlify deployment guide
│   └── AWS_DEPLOYMENT.md      # AWS production reference
├── netlify/
│   └── functions/
│       └── api.py          # Mangum ASGI adapter for Netlify Functions
├── Dockerfile              # Production container with OCR pre-installed
├── netlify.toml            # Netlify build configuration & redirect rules
├── Procfile                # Heroku / Railway process definition
├── render.yaml             # Render infrastructure specification
├── requirements.txt        # Python package dependencies
├── run.py                  # Server entrypoint
└── README.md
```

---

## 📜 License
Distributed under the MIT License.
