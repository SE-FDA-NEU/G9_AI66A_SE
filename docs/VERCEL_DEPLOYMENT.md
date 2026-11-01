# Vercel Deployment Guide

This guide explains how to deploy the Sports Venue Booking System to [Vercel](https://vercel.com) using **Vercel Postgres** for the database and **Cloudinary** for persistent photo storage.

> **Note:** This document covers the application changes and project configuration required for Vercel. It does **not** perform the actual deployment, because that requires creating a Vercel project and adding secrets that only the account owner can provide.

## What changes for Vercel?

| Local development | Vercel / serverless |
|---|---|
| SQLite file (`data/venues.db`) | **Vercel Postgres** via `DATABASE_URL` |
| Local uploads (`data/uploads/`) | **Cloudinary** via `CLOUDINARY_URL` |
| `python src/app.py` | Serverless Function entry point: `api/index.py` |
| Schema created by `python src/init_db.py` (destructive reseed) | Schema created automatically on cold start, **without** dropping or reseeding data |

Local SQLite + local uploads continue to work exactly as before when `DATABASE_URL` and `CLOUDINARY_URL` are unset.

## Prerequisites

- A [Vercel](https://vercel.com) account
- A [Vercel Postgres](https://vercel.com/docs/storage/vercel-postgres) database created in your project
- A [Cloudinary](https://cloudinary.com) account with an upload preset (optional; the default unsigned upload works)

## Environment variables

Add these in the Vercel dashboard under **Project Settings → Environment Variables**:

| Variable | Value / source | Required? |
|---|---|---|
| `DATABASE_URL` | Copy the connection string from Vercel Postgres → `.env.local` | Yes |
| `SECRET_KEY` | A long random string (generate with `openssl rand -hex 32`) | Yes |
| `CLOUDINARY_URL` | `cloudinary://<api_key>:<api_secret>@<cloud_name>` | Yes, for persistent photos |
| `SHOW_VERIFICATION_LINK` | `0` (recommended for production) | No |

The variables are also documented in `.env.example`.

## Project configuration

`vercel.json` is already configured at the repository root:

```json
{
  "version": 2,
  "builds": [
    { "src": "api/index.py", "use": "@vercel/python" }
  ],
  "routes": [
    { "src": "/static/(.*)", "dest": "/src/static/$1" },
    { "src": "/(.*)", "dest": "api/index.py" }
  ],
  "env": {
    "PYTHONPATH": "src"
  }
}
```

This tells Vercel to:

- Build the Python function at `api/index.py`.
- Serve static assets from `src/static/`.
- Route every other request to the Flask app.

## How the backend switches

`src/db.py` checks for `DATABASE_URL`:

- **Unset** → uses SQLite (`data/venues.db` or `DATABASE_PATH`).
- **Set** → uses `psycopg2` and wraps the connection in `src/db_compat.py` so existing `?` placeholders, `:name` placeholders, and SQLite function calls work on Postgres.

`src/storage.py` checks for Cloudinary credentials:

- **Unset** → writes files to `UPLOAD_DIR` (`data/uploads/`).
- **Set** → uploads to Cloudinary and stores the `public_id` in the `venue_photo` table.

## Safe schema initialization

`src/app.py` calls `_ensure_schema()` when the app starts:

- On Postgres it runs the idempotent DDL in `src/pg_schema.py` (`CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`, etc.). Existing data is never dropped or reseeded.
- On SQLite it creates the schema only when the database file does not yet exist.

The old `python src/init_db.py` command is still available for local development and still drops + reseeds the SQLite database; it is **not** used on Vercel.

## Deploy

1. Push the repository to GitHub.
2. Import the project in the Vercel dashboard.
3. Add the environment variables above.
4. Deploy.

After deployment, visit `https://<your-project>.vercel.app/health` to confirm the app can reach the database.

## Local verification

You can verify the deployment code paths locally without real external services by running the new tests:

```bash
pytest tests/test_deployment.py
```

To verify that local SQLite behavior is unchanged, run the full test suite:

```bash
pytest
```

## Files changed / added for Vercel support

- `api/index.py` — serverless entry point (already existed, unchanged).
- `vercel.json` — Vercel routing (already existed, unchanged).
- `src/db.py` — SQLite / Postgres backend selection.
- `src/db_compat.py` — SQL translation layer for Postgres compatibility.
- `src/pg_schema.py` — idempotent Postgres DDL.
- `src/storage.py` — local disk / Cloudinary storage abstraction.
- `src/venues.py` — uses `storage.save_photo()`.
- `src/routes/venues.py` — serves local files or redirects to Cloudinary URLs.
- `src/app.py` — safe, non-destructive schema initialization on startup.
- `requirements.txt` — adds `psycopg2-binary` and `cloudinary`.
- `.env.example` — documents new environment variables.
- `tests/test_deployment.py` — tests for backend and storage selection.
- `docs/VERCEL_DEPLOYMENT.md` — this guide.
