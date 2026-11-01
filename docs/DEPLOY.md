# Deploying the Sports Venue Booking System

The app is a Flask 3 + SQLite app. The recommended modern, free, persistent host is
**Render** (free tier, persistent disk, auto-deploy from GitHub).

## Render (recommended)

1. Push this repo to GitHub (already done).
2. Go to https://render.com → **New → Blueprint** and select this repository.
   Render reads `render.yaml` and creates the web service + persistent disk automatically.
3. Build command (from `render.yaml`): `pip install -r requirements.txt && python src/init_db.py`
   creates `data/venues.db` with the 24 seeded venues.
4. Start command: `gunicorn --chdir src "app:create_app()" --bind 0.0.0.0:$PORT`
5. Set env vars (Render generates `SECRET_KEY`; others come from `render.yaml`):
   - `SECRET_KEY` (auto)
   - `SHOW_VERIFICATION_LINK=1`
   - `DATABASE_PATH=data/venues.db`
6. The persistent disk is mounted at `data/`, so SQLite + uploaded photos survive redeploys.

Open the service URL → `/search`. Test accounts password `sanbong1` (see README).

## Local production-like run

```bash
pip install -r requirements.txt
python src/init_db.py
gunicorn --chdir src "app:create_app()" --bind 0.0.0.0:5000 --workers 2
```

## Vercel Serverless Production Deployment

**Live Vercel Production URL:** 🌐 **[https://g9-venue-booking-demo.vercel.app](https://g9-venue-booking-demo.vercel.app)**  
**Health Check:** `https://g9-venue-booking-demo.vercel.app/health`

The application supports serverless hosting on Vercel by decoupling storage:
- **Database:** Uses PostgreSQL via `DATABASE_URL` and `src/db_compat.py` (`CompatConnection`), supporting Vercel Postgres, Supabase, or Neon.
- **Photos:** Persistent storage backed by Cloudinary via `CLOUDINARY_URL` and `src/storage.py`.
- **Serverless Entrypoint:** `api/index.py` with `vercel.json` configuration.

See [`docs/VERCEL_DEPLOYMENT.md`](VERCEL_DEPLOYMENT.md) for step-by-step Vercel configuration.