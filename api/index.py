import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from app import create_app
from init_db import seed
from db import connect

DB_PATH = "/tmp/venues.db"
os.environ["DATABASE_PATH"] = DB_PATH

if not os.path.exists(DB_PATH):
    with connect(DB_PATH) as conn:
        seed(conn)

app = create_app(database=DB_PATH)
