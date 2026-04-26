# 🚀 Lead Engine — Executive Business Development Agent

Lead Engine is an automated executive lead-generation agent designed for business development teams. It identifies mid-sized companies hiring for leadership roles (CFO, CTO, VP, etc.) using real-time scraping and provides a premium dashboard for tracking leads.

## ✨ Features
- **Real-time Discovery**: Scrapes Indeed, LinkedIn, and Google Jobs using `jobspy`.
- **Multi-User Support**: Secure login/signup system with personalized lead tracking.
- **Dynamic Scheduling**: Users can set their own daily scan time (IST).
- **Premium Dashboard**: Dark-mode React interface with toast notifications and deduplicated results.
- **Production Ready**: Support for PostgreSQL and Docker-based deployment.

## 🛠 Tech Stack
- **Backend**: FastAPI (Python 3.11)
- **Frontend**: React + Vite (Tailwind-like Vanilla CSS)
- **Database**: SQLite (Local) / PostgreSQL (Cloud)
- **Scraper**: JobSpy

## 🚀 Local Setup

### 1. Backend
```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8001
```

### 2. Frontend
```bash
cd frontend
npm install
npm run dev
```

## 🌍 Deployment
See [deployment_plan.md](./deployment_plan.md) for full instructions on deploying to Render + Vercel + Supabase.

## 📝 License
MIT
