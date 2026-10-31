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

## Why not Vercel?

Vercel's filesystem is read-only and ephemeral, so SQLite + photo uploads would be wiped
on every cold start. The previous Vercel link in README was a Sprint 2 static mock-up only.
For a real, modern, persistent deploy, use Render (above) or Railway/Fly.io with the same
Procfile/gunicorn setup.