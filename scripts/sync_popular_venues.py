"""Sync the 22 real popular Hanoi venues and backfill coordinates into the configured DB."""
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from app import _migrate_postgres_columns, _migrate_sqlite_columns
from db import _is_postgres, connect
from hanoi_popular_venues import sync_popular_venues


def main():
    load_dotenv()
    with connect() as conn:
        if _is_postgres():
            _migrate_postgres_columns(conn)
        else:
            _migrate_sqlite_columns(conn)
        result = sync_popular_venues(conn)
        print(
            f"Synced popular Hanoi venues: inserted={result['inserted']}, "
            f"backfilled_coords={result['updated']}"
        )


if __name__ == "__main__":
    main()
