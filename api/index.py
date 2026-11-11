"""Vercel serverless entry point for the Sports Venue Booking System."""
import os
import shutil
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT, ".env"))
load_dotenv(os.path.join(ROOT, ".env.local"))

# On serverless environments (read-only filesystem in /var/task),
# if external DATABASE_URL is not provided, copy seeded SQLite DB to writable /tmp
if not os.environ.get("DATABASE_URL"):
    tmp_db = "/tmp/venues.db"
    bundled_db = os.path.join(ROOT, "data", "venues.db")
    if os.path.exists(bundled_db) and not os.path.exists(tmp_db):
        shutil.copy2(bundled_db, tmp_db)
    os.environ["DATABASE_PATH"] = tmp_db

if "UPLOAD_DIR" not in os.environ:
    tmp_uploads = "/tmp/uploads"
    os.makedirs(tmp_uploads, exist_ok=True)
    os.environ["UPLOAD_DIR"] = tmp_uploads

from app import create_app

app = create_app()