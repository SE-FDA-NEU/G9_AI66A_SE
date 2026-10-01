# Setup - run the Sports Venue Booking System on a new machine

Follow the steps **in order**, word for word. Expected time: about 10 minutes, most of
it downloading Python packages. Every command is run from a terminal (Windows:
**PowerShell**; macOS: **Terminal**; Linux: any shell).

## 1. Prerequisites

Nothing is assumed to be installed already.

| Tool | Version | How to check | Where to get it |
|------|---------|--------------|-----------------|
| Python | **3.11 or newer** (tested on 3.11 and 3.12) | `python --version` (macOS/Linux: `python3 --version`) | https://www.python.org/downloads/ - on Windows tick **"Add python.exe to PATH"** in the installer |
| Git | 2.30 or newer | `git --version` | https://git-scm.com/downloads |
| A web browser | any recent Chrome, Edge, Firefox or Safari | - | - |

No database server, Docker or Node.js is needed: the database is a SQLite file that
Python creates itself.

## 2. Get the code and install

Commands that differ between systems are shown twice. Run **only** the line for your
system.

```bash
git clone https://github.com/SE-FDA-NEU/G9_AI66A_SE.git
cd G9_AI66A_SE
```

Create and activate a virtual environment:

```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

```powershell
# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Your prompt now starts with `(.venv)`. Install the packages:

```bash
pip install -r requirements.txt
```

## 3. Configuration

```bash
# macOS / Linux
cp .env.example .env
```

```powershell
# Windows (PowerShell)
copy .env.example .env
```

`.env` holds three values. The defaults work as they are; change them only if a step
below tells you to.

| Variable | Default | What to put in it |
|----------|---------|-------------------|
| `PORT` | `5000` | The port the app listens on. **macOS:** use `5001` (port 5000 is taken by AirPlay Receiver). |
| `DATABASE_PATH` | `data/venues.db` | Where the SQLite file is created. Leave as is. |
| `SECRET_KEY` | `change-me-to-a-long-random-string` | Any long random text. It signs the session cookie. |

`.env` is in `.gitignore` and is never committed.

## 4. Create and seed the database

One command:

```bash
python src/init_db.py
```

Expected output - **24 venues**, 50 rows in total:

```
Created data/venues.db
  user            6 rows
  venue          24 rows
  pricing_rule    4 rows
  blocked_slot    2 rows
  booking         5 rows
  booking_slot    8 rows
  review          1 rows
```

Running it again deletes everything and recreates the same data, so it is safe to repeat.

## 5. Start the app

```bash
python src/app.py
```

Leave this terminal open. The last line printed is
`Running on http://127.0.0.1:5000` (or `:5001` if you changed `PORT`).

## 6. How to know it worked

Open **http://localhost:5000/search** (macOS with `PORT=5001`:
http://localhost:5001/search).

You should see:

- the heading **"Sports Venue Booking · Find a venue"**,
- the line **"24 venue(s) found"** and a table of 24 venues across 7 Hanoi districts
  (Cau Giay, Dong Da, Ha Dong, Hai Ba Trung, Long Bien, Nam Tu Liem, Thanh Xuan),
- at the bottom: *"Data source: table venue in SQLite (24 rows)."*

Then choose **Football** and **Cau Giay** and press **Search**: exactly **2** venues
(Nghia Tan Football Pitch, Thong Nhat Football Pitch). Choose **Tennis** and **Ha Dong**: the page
says **"No venues found"**.

Quick check without a browser: http://localhost:5000/health returns
`{"status": "ok", "venues": 24}`.

**Proof the data comes from the database, not the code:** stop the app (Ctrl+C), open
`data/venues.csv` in any text editor, delete the line that starts with
`lan.owner@example.com,Ha Dong Football Pitch`, save, then run

```bash
python src/init_db.py        # now prints: venue 23 rows
python src/app.py
```

Reload the page: **23 venue(s) found**. Put the line back (or run
`git checkout data/venues.csv`) and run `python src/init_db.py` again to return to 24.

Optional - run the automated tests: `pytest` → `15 passed`.

## 7. Troubleshooting

| What you see | Why | Fix |
|--------------|-----|-----|
| `ModuleNotFoundError: No module named 'flask'` (or `dotenv`) | The virtual environment is not active, or `pip install` was run outside it | Run the activate line from step 2 again (prompt must show `(.venv)`), then `pip install -r requirements.txt` |
| `Address already in use` / `Port 5000 is in use by another program` | Another program holds port 5000 - on macOS this is AirPlay Receiver | Set `PORT=5001` in `.env`, run `python src/app.py` again, open http://localhost:5001/search |
| Windows: `Activate.ps1 cannot be loaded because running scripts is disabled on this system` | PowerShell's default execution policy blocks scripts | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, answer `Y`, then activate again. Or use Command Prompt: `.venv\Scripts\activate.bat` |
| `'python' is not recognized` (Windows) or `command not found: python` (macOS) | Python not on PATH, or macOS only has `python3` | Windows: re-run the installer, choose *Modify*, tick *Add Python to environment variables*. macOS/Linux: use `python3` in every command |
| `sqlite3.OperationalError: no such table: venue` | The app was started before the database was created, or from another folder | Run `python src/init_db.py` from the repository root (the folder that contains `README.md`) |

## 8. Tested by

| Who | Machine (not the author's) | Date | Time taken | Result |
|-----|----------------------------|------|------------|--------|
| @\<github-username\> (Team \<NN\>) | \<Windows 11 / macOS 14 / Ubuntu 24.04\>, Python \<3.x\> | \<dd/mm/2026\> | \<n\> minutes | \<passed / what went wrong\> |
