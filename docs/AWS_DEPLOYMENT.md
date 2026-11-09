# ☁️ ScheduleSync - AWS Cloud Deployment Guide

This guide details how to deploy **ScheduleSync** onto Amazon Web Services (AWS) using either the **AWS Free Tier** or **AWS Lightsail**, including AWS RDS (Relational Database Service), S3 (Simple Storage Service), and EC2 (Elastic Compute Cloud).

---

## 1. Cloud Architecture Overview

```
                          ┌──────────────────────────┐
                          │       Student User       │
                          └─────────────┬────────────┘
                                        │ (HTTPS: 443)
                                        ▼
                          ┌──────────────────────────┐
                          │   Nginx Reverse Proxy    │
                          └─────────────┬────────────┘
                                        │
                                        ▼
   ┌────────────────────────────────────────────────────────────────────────┐
   │                   AWS EC2 / Lightsail Instance                         │
   │                                                                        │
   │   ┌───────────────────────────────────────────────────────────────┐    │
   │   │                      FastAPI Application                      │    │
   │   │   • Auth (JWT / Bcrypt)      • Group Heatmap Engine           │    │
   │   │   • Timetable Slot Matrix    • Free Time Analyzer              │    │
   │   └──────────────┬───────────────────────────────┬────────────────┘    │
   └──────────────────┼───────────────────────────────┼─────────────────────┘
                      │ (PostgreSQL / MySQL Protocol) │ (boto3 SDK)
                      ▼                               ▼
       ┌────────────────────────────┐   ┌───────────────────────────┐
       │   AWS RDS Database         │   │   AWS S3 Bucket           │
       │   (db.t3.micro / t4g.micro)│   │   (Screenshot Storage)    │
       │   • 3NF Schema             │   │   • Raw Timetable JPEGs   │
       │   • Views & Triggers       │   │   • Free Tier: 5 GB       │
       └────────────────────────────┘   └───────────────────────────┘
```

---

## 2. AWS Free Tier vs. Lightsail Cost Breakdown

| Service | AWS Free Tier (First 12 Months) | Expected Monthly Cost |
| :--- | :--- | :--- |
| **AWS RDS (PostgreSQL / MySQL)** | 750 hours/month of `db.t3.micro` or `db.t4g.micro` + 20 GB SSD storage | **\$0.00** |
| **AWS EC2 (Web Host)** | 750 hours/month of `t2.micro` or `t3.micro` | **\$0.00** |
| **AWS S3 (Image Storage)** | 5 GB standard storage, 20,000 GET requests | **<\$0.05** |
| **AWS Lightsail (All-in-One Alternative)** | Free for first 1–3 months, then **\$3.50/month flat** | **\$3.50** |

> [!IMPORTANT]
> **Free Tier Safety Checklist:**
> 1. Set up an **AWS Billing Alarm** at \$1.00 in AWS CloudWatch to receive email alerts if any billable charge begins.
> 2. Ensure RDS database Multi-AZ deployment is set to **Single-AZ** (Multi-AZ is not covered in Free Tier).
> 3. Do not provision an AWS NAT Gateway (which costs ~\$30/mo); place EC2 in the public subnet with an Elastic IP.
> 4. Delete or snapshot & terminate RDS when your semester grade is posted.

---

## 3. Step-by-Step Deployment on AWS EC2 / Lightsail

### Step 1: Launch Ubuntu Instance
1. Log in to AWS Console → **EC2** → **Launch Instance**.
2. Select **Ubuntu 24.04 LTS (x86_64)**.
3. Instance Type: `t3.micro` (or `t2.micro`).
4. Key Pair: Create or select your `.pem` key.
5. Network Settings: Allow **SSH (Port 22)**, **HTTP (Port 80)**, and **HTTPS (Port 443)**.

### Step 2: Connect and Install Dependencies
Connect via SSH:
```bash
ssh -i your-key.pem ubuntu@your-ec2-ip
```

Update system and install Python + Tesseract + Nginx:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv git tesseract-ocr nginx
```

### Step 3: Clone Repository & Setup Virtual Environment
```bash
git clone https://github.com/your-username/ScheduleSync.git
cd ScheduleSync

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 4: Configure Database
- **Option A (Local SQLite - Recommended for Zero Extra AWS RDS Cost):**
  ```bash
  python database/seed_data.py
  ```
- **Option B (AWS RDS PostgreSQL):**
  Create an RDS PostgreSQL instance in AWS Console, set security group inbound rule to allow port 5432 from your EC2 security group, and export:
  ```bash
  export DATABASE_URL="postgresql://dbuser:dbpassword@your-rds-endpoint.amazonaws.com:5432/schedulesync"
  ```

### Step 5: Configure Systemd Service (Auto-Restart)
Create `/etc/systemd/system/schedulesync.service`:
```ini
[Unit]
Description=ScheduleSync FastAPI Service
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/ScheduleSync
ExecStart=/home/ubuntu/ScheduleSync/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable schedulesync
sudo systemctl start schedulesync
```

### Step 6: Configure Nginx as Reverse Proxy
Edit `/etc/nginx/sites-available/default`:
```nginx
server {
    listen 80;
    server_name your-domain-or-ec2-ip;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Restart Nginx:
```bash
sudo systemctl restart nginx
```

🎉 ScheduleSync is now live on AWS!
