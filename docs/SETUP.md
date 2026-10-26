# Setup - run the Sports Venue Booking System on a new machine

Follow the steps **in order**, word for word. Expected time: about 10 minutes, most of
it downloading Python packages. Every command is run from a terminal (Windows:
**PowerShell**; macOS: **Terminal**; Linux: any shell).

## 1. Prerequisites

Nothing is assumed to be installed already.

| Tool          | Version                                     | How to check                                          | Where to get it                                                                                   |
| ------------- | ------------------------------------------- | ----------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| Python        | **3.11 or newer** (tested on 3.11 and 3.12) | `python --version` (macOS/Linux: `python3 --version`) | https://www.python.org/downloads/ - on Windows tick **"Add python.exe to PATH"** in the installer |
| Git           | 2.30 or newer                               | `git --version`                                       | https://git-scm.com/downloads                                                                     |
| A web browser | any recent Chrome, Edge, Firefox or Safari  | -                                                     | -                                                                                                 |

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

`.env` holds configuration values. The defaults work as they are; change them only if a step
below tells you to.

| Variable                 | Default                             | What to put in it                                                                            |
| ------------------------ | ----------------------------------- | -------------------------------------------------------------------------------------------- |
| `PORT`                   | `5000`                              | The port the app listens on. **macOS:** use `5001` (port 5000 is taken by AirPlay Receiver). |
| `DATABASE_PATH`          | `data/venues.db`                    | Where the SQLite file is created. Leave as is.                                               |
| `SECRET_KEY`             | `change-me-to-a-long-random-string` | Any long random text. It signs the session cookie.                                           |
| `SHOW_VERIFICATION_LINK` | `1`                                 | `1` prints the verification link in the console and displays it on `/login` (BR4 without SMTP). |

`.env` is in `.gitignore` and is never committed.

## 4. Create and seed the database

One command:

```bash
python src/init_db.py
```

Expected output - **8 tables**, **24 venues**, 51 rows in total:

```
Created data/venues.db
  user            7 rows
  venue          24 rows
  venue_photo     0 rows
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
- at the bottom: _"Data source: table venue in SQLite (24 rows)."_

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

## 6. Run the automated test suite (Milestone 4)

Milestone 4 introduces automated tests for every P0 story. You do **not** need to run the Flask web server or open a browser to run the tests; tests execute against an isolated temporary database fixture in seconds.

```bash
# Run all tests with standard summary
python -m pytest

# Or run with verbose test case names (as shown in docs/testing.md)
python -m pytest -v
```

Expected output:
```text
============================= 89 passed in ~22s =============================
```

## 7. Test accounts & short P0 walk-through

### Test accounts

All seeded test accounts use the test password **`sanbong1`** (no real passwords).

| Role | Email | Name | Notes |
|---|---|---|---|
| Customer (verified) | `minh@example.com` | Pham Duc Minh | Verified customer; holds bookings `BK-000101`, `BK-000103`. Ready to book. |
| Customer (verified) | `trang@example.com` | Do Thu Trang | Verified customer; holds bookings `BK-000102`, `BK-000104`. |
| Customer (unverified) | `khoa@example.com` | Vu Minh Khoa | Unverified customer (`email_verified_at` NULL); verifies BR4 booking refusal. |
| Venue owner | `lan.owner@example.com` | Nguyen Thi Lan | Owns *Thong Nhat Football Pitch*, *Lan Anh Badminton Court*. Lands on `/owner/venues`. |
| Venue owner | `hung.owner@example.com` | Tran Van Hung | Owns *My Dinh Football Pitch*. |
| Venue owner | `son.owner@example.com` | Le Hoang Son | Owns *Chua Boc Badminton Court*. |
| Administrator | `admin@example.com` | Admin | Administrative account (`admin`). |

### Short P0 walk-through (5 minutes)

Follow these steps in order to test the P0 stories through the interface:

1. **US03 - Search for venues**: Open http://localhost:5000/search. Select Sport: **Football**, Area: **Cau Giay** and click **Search** to see 2 matching venues. Type in the text box to narrow down results.
2. **US04 - View venue details & availability**: Click on **Thong Nhat Football Pitch** (or open http://localhost:5000/venues/1) to see venue information, photos, and the hourly availability grid for today.
3. **US01 - Customer registration**: Go to http://localhost:5000/register. Create an account with a 10-digit phone number starting with 0 (e.g. `0988776655`) and password `sanbong1`. Since `SHOW_VERIFICATION_LINK=1`, the verification link is displayed on the login page banner and printed in the server terminal. Click it to verify your account (BR4).
4. **US02 - User login**: Go to http://localhost:5000/login. Sign in with `minh@example.com` and password `sanbong1`. You are redirected to `/dashboard` (BR7) and your name is displayed in the navigation header.
5. **US05 - Book a venue**: From `/venues/1` or `/search`, choose a date and click **Book now** on an available slot (or visit http://localhost:5000/booking/1). Review the segmented price breakdown and confirm. You are taken to `/bookings/BK-XXXXXX` displaying your booking confirmation.
6. **US06 - Owner venue management**: Click **Sign out** (US02 logout), then sign in as owner `lan.owner@example.com` (`sanbong1`). You are redirected to `/owner/venues` (BR7). Click **Add venue** (http://localhost:5000/owner/venues/new) to create a new pitch.

## 8. Troubleshooting

| What you see                                                                                | Why                                                                         | Fix                                                                                                                                             |
| ------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `ModuleNotFoundError: No module named 'flask'` (or `dotenv`)                                | The virtual environment is not active, or `pip install` was run outside it  | Run the activate line from step 2 again (prompt must show `(.venv)`), then `pip install -r requirements.txt`                                    |
| `Address already in use` / `Port 5000 is in use by another program`                         | Another program holds port 5000 - on macOS this is AirPlay Receiver         | Set `PORT=5001` in `.env`, run `python src/app.py` again, open http://localhost:5001/search                                                     |
| Windows: `Activate.ps1 cannot be loaded because running scripts is disabled on this system` | PowerShell's default execution policy blocks scripts                        | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, answer `Y`, then activate again. Or use Command Prompt: `.venv\Scripts\activate.bat` |
| `'python' is not recognized` (Windows) or `command not found: python` (macOS)               | Python not on PATH, or macOS only has `python3`                             | Windows: re-run the installer, choose _Modify_, tick _Add Python to environment variables_. macOS/Linux: use `python3` in every command         |
| `sqlite3.OperationalError: no such table: venue`                                            | The app was started before the database was created, or from another folder | Run `python src/init_db.py` from the repository root (the folder that contains `README.md`)                                                     |
| No verification email received / Cannot book: *"Please verify your email before booking"* (BR4) | Local development runs without an SMTP server. When `SHOW_VERIFICATION_LINK=1`, the link is printed in the terminal and displayed on `/login` | Click the verification link shown on `/login` or printed in the terminal console. Alternatively, sign in using an already-verified test account (`minh@example.com`). |
| *"Account temporarily locked. Try again in 15 minutes"* (BR5)                               | An account had 5 consecutive incorrect login attempts (BR5 brute-force lock) | Wait 15 minutes, log in with another test account, or run `python src/init_db.py` to reset the database and lock counters.                     |

## 9. Tested by

| Who           | Machine (not the author's)     | Date       | Time taken | Result |
| ------------- | ------------------------------ | ---------- | ---------- | ------ |
| @PhunghoaAI   | Windows 11, Python 3.13        | 02/10/2026 | 10 minutes | passed |
| @hoanglong-dev| macOS Sonoma 14.5, Python 3.11 | 16/10/2026 | 8 minutes  | passed |
