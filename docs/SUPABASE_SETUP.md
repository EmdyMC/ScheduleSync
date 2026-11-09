# Supabase Setup Guide for ScheduleSync

This guide details how to set up **Supabase (PostgreSQL)** as the persistent cloud database for ScheduleSync, whether running locally, on **Netlify**, **Render**, or **Docker**.

---

## 🚀 Step 1: Create a Supabase Project

1. Go to [supabase.com](https://supabase.com) and sign in or create a free account.
2. Click **"New Project"**.
3. Choose an organization, enter a project name (e.g., `schedulesync`), and set a strong database password.
4. Select a region close to your users (e.g., `South Asia (Mumbai)` or `East US`).
5. Click **"Create new project"** (takes ~1-2 minutes to provision).

---

## 📄 Step 2: Initialize the Database Schema

1. In your Supabase dashboard, click **SQL Editor** on the left navigation bar.
2. Click **"New Query"**.
3. Open the file [`database/supabase_schema.sql`](file:///database/supabase_schema.sql) in this repository and copy its entire contents.
4. Paste the SQL script into the Supabase SQL Editor and click **Run**.
5. You should see a `Success. No rows returned` message. All 7 tables, views, and indexes are now created:
   - `users`
   - `timetables`
   - `timetable_slots`
   - `friendships`
   - `groups`
   - `group_members`
   - `share_links`
   - Views: `v_user_friends`, `v_active_slots`, `v_group_members_details`

---

## 🔑 Step 3: Get Your Connection String

1. In Supabase, go to **Project Settings** (gear icon) &rarr; **Database**.
2. Scroll to **Connection string**.
3. Select **URI** mode:
   - For serverless platforms like **Netlify** or **AWS Lambda**, choose **Transaction** or **Session** pooler (port `6543`), or use the direct URI (port `5432`):
     ```text
     postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
     ```
     *(Or transaction pooler)*:
     ```text
     postgresql://postgres.[PROJECT-REF]:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?sslmode=require
     ```
4. Replace `[YOUR-PASSWORD]` with the database password you chose in Step 1.

---

## ⚙️ Step 4: Configure Environment Variables

### In Netlify
1. Go to your site in the [Netlify Dashboard](https://app.netlify.com).
2. Go to **Site configuration** &rarr; **Environment variables**.
3. Add:
   | Key | Value |
   |---|---|
   | `DATABASE_URL` | `postgresql://postgres:[PASSWORD]@db.[REF].supabase.co:5432/postgres` |
   | `SECRET_KEY` | *(A random 32+ character string for JWT signing)* |

### For Local Development
Create a `.env` file in the project root:
```env
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[REF].supabase.co:5432/postgres
SECRET_KEY=your-super-secret-production-key-here
```
ScheduleSync will automatically detect `DATABASE_URL`, connect via `psycopg2`, and use your live Supabase cloud database!

If `DATABASE_URL` is omitted, ScheduleSync automatically falls back to local SQLite for offline development.

---

## 🔒 Security Best Practices
- Keep your database password secure.
- ScheduleSync hashes all user passwords using industry-standard `bcrypt` before storing them in Supabase.
- All API routes issue standard cryptographically signed JWT tokens with 7-day expiration.
