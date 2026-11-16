"""Fetch Hanoi sports venues from OpenStreetMap Overpass API and sync into DB.

Falls back to `POPULAR_HANOI_VENUES` when Overpass is unreachable or `--offline`
is passed. Supports `--dry-run` to preview without writing to the database.
"""
import argparse
import http.client
import json
import math
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from app import _migrate_postgres_columns, _migrate_sqlite_columns
from db import _is_postgres, connect
from hanoi_popular_venues import AREA_COORDS, POPULAR_HANOI_VENUES, sync_popular_venues
from venues import AREAS

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
HANOI_BBOX = (20.94, 105.72, 21.10, 105.92)

SPORT_MAP = {
    "soccer": ("Football", 350000),
    "football": ("Football", 350000),
    "futsal": ("Football", 350000),
    "badminton": ("Badminton", 100000),
    "tennis": ("Tennis", 250000),
    "pickleball": ("Pickleball", 180000),
}


def _nearest_area(lat, lng):
    best_area = AREAS[0]
    best_dist = float("inf")
    for area, (clat, clng) in AREA_COORDS.items():
        dist = math.hypot(lat - clat, lng - clng)
        if dist < best_dist:
            best_dist = dist
            best_area = area
    return best_area


def _match_area(tags, lat, lng):
    raw = " ".join(
        str(tags.get(k, "")) for k in ("addr:district", "addr:suburb", "addr:full", "addr:street")
    ).lower()
    for area in AREAS:
        if area.lower() in raw:
            return area
    return _nearest_area(lat, lng)


def fetch_overpass_venues(timeout=15):
    """Query OpenStreetMap Overpass API for Hanoi sports venues."""
    s, w, n, e = HANOI_BBOX
    query = (
        f"[out:json][timeout:{int(timeout)}];"
        "("
        f'  node["leisure"~"^(pitch|sports_centre)$"]["sport"~"^(soccer|football|futsal|badminton|tennis|pickleball)$"]({s},{w},{n},{e});'
        f'  way["leisure"~"^(pitch|sports_centre)$"]["sport"~"^(soccer|football|futsal|badminton|tennis|pickleball)$"]({s},{w},{n},{e});'
        ");"
        "out center tags;"
    )
    data = urllib.parse.urlencode({"data": query}).encode("utf-8")
    req = urllib.request.Request(
        OVERPASS_URL,
        data=data,
        headers={"User-Agent": "G9-AI66A-HanoiVenueCrawler/1.0"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    venues = []
    seen_names = set()
    for el in payload.get("elements", []):
        tags = el.get("tags") or {}
        name = (tags.get("name") or "").strip()
        if not (3 <= len(name) <= 100) or name in seen_names:
            continue

        sport_raw = (tags.get("sport") or "").split(";")[0].strip().lower()
        if sport_raw not in SPORT_MAP:
            continue
        sport, default_price = SPORT_MAP[sport_raw]

        lat = el.get("lat") or (el.get("center") or {}).get("lat")
        lng = el.get("lon") or (el.get("center") or {}).get("lon")
        if lat is None or lng is None:
            continue
        lat, lng = round(float(lat), 6), round(float(lng), 6)

        area = _match_area(tags, lat, lng)
        street = tags.get("addr:street") or ""
        housenumber = tags.get("addr:housenumber") or ""
        address = f"{housenumber} {street}".strip() or tags.get("addr:full") or f"{area}, Hanoi"

        seen_names.add(name)
        venues.append((name, sport, area, address, default_price, 6, 22, lat, lng))

    return venues


def sync_crawled_venues(conn, crawled_venues, dry_run=False):
    """Insert newly crawled venues idempotently after ensuring popular venues exist."""
    if dry_run:
        return {"inserted": 0, "popular_inserted": 0, "backfilled": 0}

    popular_res = sync_popular_venues(conn)
    owner_row = conn.execute(
        'SELECT id FROM "user" WHERE role = \'owner\' ORDER BY id LIMIT 1'
    ).fetchone()
    if owner_row is None:
        owner_row = conn.execute('SELECT id FROM "user" ORDER BY id LIMIT 1').fetchone()
    if owner_row is None:
        return {
            "inserted": 0,
            "popular_inserted": popular_res["inserted"],
            "backfilled": popular_res["updated"],
        }

    owner_id = owner_row[0]
    existing_names = {r[0] for r in conn.execute("SELECT name FROM venue").fetchall()}
    inserted = 0
    for name, sport, area, address, price, open_hour, close_hour, lat, lng in crawled_venues:
        if name in existing_names:
            continue
        conn.execute(
            "INSERT INTO venue (owner_id, name, sport, area, address, hourly_price, "
            "open_hour, close_hour, latitude, longitude) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (owner_id, name, sport, area, address, price, open_hour, close_hour, lat, lng),
        )
        existing_names.add(name)
        inserted += 1

    if inserted:
        conn.commit()
    return {
        "inserted": inserted,
        "popular_inserted": popular_res["inserted"],
        "backfilled": popular_res["updated"],
    }


def main():
    parser = argparse.ArgumentParser(description="Crawl Hanoi sports venues from OpenStreetMap.")
    parser.add_argument("--offline", action="store_true", help="Skip Overpass API and use built-in popular venues.")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and print summary without modifying DB.")
    parser.add_argument("--timeout", type=int, default=15, help="Overpass API timeout in seconds.")
    args = parser.parse_args()

    load_dotenv()
    crawled = []
    if not args.offline:
        try:
            crawled = fetch_overpass_venues(timeout=args.timeout)
            print(f"Fetched {len(crawled)} Hanoi venues from OpenStreetMap Overpass API.")
        except (urllib.error.URLError, http.client.HTTPException, TimeoutError, json.JSONDecodeError, OSError) as exc:
            print(f"Overpass API unavailable ({exc}); falling back to POPULAR_HANOI_VENUES ({len(POPULAR_HANOI_VENUES)}).")
            crawled = list(POPULAR_HANOI_VENUES)
    else:
        print(f"Offline mode: using POPULAR_HANOI_VENUES ({len(POPULAR_HANOI_VENUES)}).")
        crawled = list(POPULAR_HANOI_VENUES)

    if args.dry_run:
        print(f"Dry run complete: {len(crawled)} candidate venues ready.")
        return

    with connect() as conn:
        if _is_postgres():
            _migrate_postgres_columns(conn)
        else:
            _migrate_sqlite_columns(conn)
        res = sync_crawled_venues(conn, crawled, dry_run=args.dry_run)
        print(
            f"DB sync complete: popular_inserted={res['popular_inserted']}, "
            f"crawled_inserted={res['inserted']}, backfilled_coords={res['backfilled']}"
        )


if __name__ == "__main__":
    main()
