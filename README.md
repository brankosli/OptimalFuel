# OptimalFuel

Personal training analytics and nutrition planning platform.
Integrates **Polar Flow** and **Strava** to tailor daily meal plans based on your real training load, recovery data, and sleep quality.

---

## What It Does

- Pulls your training data from Strava (activities, HR, power)
- Pulls sleep, HRV, and Nightly Recharge from Polar
- Computes ATL / CTL / TSB (Performance Management Chart)
- Generates daily caloric and macro targets using carb periodisation
- Tracks your meals against daily targets
- Shows everything in a clean dashboard

---

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.13 + FastAPI |
| Database | SQLite (single file, no setup needed) |
| Scheduling | APScheduler (no Redis needed) |
| Frontend | React 18 + TypeScript + Vite |

---

## Prerequisites

Before starting, install these two things:

### 1. Python 3.13
Download from **https://python.org/downloads**

> ⚠️ During installation, tick **"Add Python to PATH"** — this is important!

Verify:
```
python --version
```

### 2. Node.js 18+
Download the LTS version from **https://nodejs.org**

> ⚠️ After installing, close and reopen your terminal before running `npm`.

Verify:
```
node --version
npm --version
```

---

## Installation

### Step 1 — Extract the project

Unzip the project to somewhere **outside** of XAMPP's htdocs folder, for example:
```
D:\Projects\optimalfuel\
```

### Step 2 — Backend setup

Open a terminal and run:

```bash
cd D:\Projects\optimalfuel\backend

# Create virtual environment
python -m venv venv

# Activate it
venv\Scripts\activate

# You should see (venv) at the start of your prompt

# Install dependencies
pip install --only-binary=:all: -r requirements.txt

# If greenlet error appears:
pip install greenlet
```

### Step 3 — Configure environment

```bash
# Still in backend folder
copy .env.example .env
```

Open `backend\.env` in any text editor. You'll fill in the API credentials in the next section.

### Step 4 — Frontend setup

Open a **second terminal** and run:

```bash
cd D:\Projects\optimalfuel\frontend

npm install

copy .env.example .env.local
```

The `.env.local` file is fine as-is — it points to `http://localhost:8000`.

---

## API Credentials Setup

You need to register two free API apps — one with Polar, one with Strava.

### Polar Accesslink

1. Go to **https://admin.polaraccesslink.com**
2. Log in with your Polar Flow account
3. Click **Create new API client**
4. Fill in:
   - Name: `OptimalFuel` (or anything you like)
   - Redirect URI: `http://localhost:8000/api/v1/auth/polar/callback`
5. Copy the **Client ID** and **Client Secret**
6. Open `backend\.env` and fill in:
   ```
   POLAR_CLIENT_ID=paste_here
   POLAR_CLIENT_SECRET=paste_here
   ```

### Strava

1. Go to **https://www.strava.com/settings/api**
2. Create an app if you don't have one
3. Set **Authorization Callback Domain** to `localhost`
4. Copy the **Client ID** and **Client Secret**
5. Open `backend\.env` and fill in:
   ```
   STRAVA_CLIENT_ID=paste_here
   STRAVA_CLIENT_SECRET=paste_here
   ```

---

## Running the App

You need **two terminals open at the same time**.

### Terminal 1 — Backend

```bash
cd D:\Projects\optimalfuel\backend
venv\Scripts\activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

You should see:
```
🚀 Starting OptimalFuel...
✅ Database ready
⏰ Sync scheduler started
```

### Terminal 2 — Frontend

```bash
cd D:\Projects\optimalfuel\frontend
npm run dev
```

You should see:
```
VITE v5.x  ready in xxx ms
➜  Local:   http://localhost:5173/
```

### Open the app

- **Dashboard:** http://localhost:5173
- **API Explorer:** http://localhost:8000/api/docs

---

## Connecting Your Accounts (One-Time Setup)

This only needs to be done once. Make sure the backend is running.

### Connect Polar

1. Open: **http://localhost:8000/api/v1/auth/polar**
2. Copy the URL from the response
3. Paste it in your browser
4. Log in to Polar Flow and click **Allow**
5. You should see: `✅ Polar connected successfully!`

### Connect Strava

1. Open: **http://localhost:8000/api/v1/auth/strava**
2. Copy the URL from the response
3. Paste it in your browser
4. Log in to Strava and click **Authorize**
5. You should see: `✅ Strava connected successfully!`

After connecting both, the status dots in the sidebar should turn green.

---

## First Sync

Once both accounts are connected, pull your data:

1. Go to **http://localhost:8000/api/docs**
2. Find `POST /api/v1/analytics/sync`
3. Click **Try it out** → **Execute**
4. Wait for `{"message": "Sync complete"}`

Or click the **↻ Sync now** button on the dashboard.

The sync pulls:
- Last 30 days of Strava activities
- Last 28 nights of Polar sleep data
- Last 28 days of Polar Nightly Recharge
- Recomputes all ATL/CTL/TSB analytics

---

## Setting Up Your Profile

Go to **http://localhost:5173/settings** and fill in:

| Field | Why it matters |
|---|---|
| Weight, Height, Age, Sex | Used for BMR calculation |
| LTHR (Lactate Threshold HR) | Used for hrTSS calculation when no power meter |
| FTP (Functional Threshold Power) | Used for power-based TSS (cyclists) |
| Protein target (g/kg) | Default 1.8g/kg, adjust to preference |

Without the body metrics, caloric and macro targets won't be calculated.

---

## Daily Use

Each day the app automatically syncs every 30 minutes. You can also sync manually.

- **Dashboard** — today's readiness score, fuel target, PMC chart
- **Training** — weekly TSS chart, all activities
- **Sleep** — sleep score, HRV, Nightly Recharge trends
- **Nutrition** — today's macro targets + meal logging

---

## Environment Variables Reference

All settings live in `backend\.env`:

```env
# App
APP_ENV=development
DB_ECHO=false               # Set to true to log SQL queries

# Polar (filled automatically after OAuth)
POLAR_CLIENT_ID=
POLAR_CLIENT_SECRET=
POLAR_ACCESS_TOKEN=         # Set automatically after connecting
POLAR_USER_ID=              # Set automatically after connecting

# Strava (filled automatically after OAuth)
STRAVA_CLIENT_ID=
STRAVA_CLIENT_SECRET=
STRAVA_ACCESS_TOKEN=        # Set automatically after connecting
STRAVA_REFRESH_TOKEN=       # Set automatically after connecting
STRAVA_TOKEN_EXPIRES_AT=    # Set automatically after connecting
STRAVA_ATHLETE_ID=          # Set automatically after connecting

# Scheduler
SYNC_INTERVAL_MINUTES=30    # How often to auto-sync
```

---

## Common Issues

### `npm` not recognised after installing Node
Close the terminal completely and open a new one. If still not working, add `C:\Program Files\nodejs\` to your PATH manually via System Properties → Environment Variables.

### `pip install` fails with pandas/numpy errors
Use the binary-only flag:
```bash
pip install --only-binary=:all: -r requirements.txt
```

### `greenlet` error on startup
```bash
pip install greenlet
```

### Polar sleep returns 404
- Make sure your Polar device has synced to the Polar Flow mobile app recently
- Open the Polar Flow app on your phone and let it sync
- The Accesslink API only returns data uploaded after you registered the app

### Port 8000 already in use
Change the port in the uvicorn command:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```
And update `frontend\.env.local`:
```
VITE_API_URL=http://localhost:8001
```

### Strava token expired
Strava tokens expire every 6 hours. The app refreshes them automatically. If you see auth errors, restart the backend — it will refresh on the next sync.

---

## Project Structure

```
optimalfuel/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/     # Route handlers
│   │   ├── core/                 # Config (config.py)
│   │   ├── db/                   # Database session
│   │   ├── models/               # SQLAlchemy models
│   │   ├── services/
│   │   │   ├── polar/            # Polar API client + sync
│   │   │   ├── strava/           # Strava API client + sync
│   │   │   ├── analytics/        # PMC engine (ATL/CTL/TSB)
│   │   │   └── nutrition/        # Macro calculation
│   │   └── tasks/                # APScheduler sync jobs
│   ├── .env                      # Your credentials (never commit this)
│   ├── .env.example              # Template
│   ├── requirements.txt
│   └── optimalfuel.db            # SQLite database (auto-created)
├── frontend/
│   └── src/
│       ├── pages/                # Dashboard, Training, Sleep, Nutrition, Settings
│       ├── components/           # Charts, MacroRing, Layout
│       ├── hooks/                # Data fetching (useData.ts)
│       └── utils/                # API client, formatters
└── scripts/
    └── dev.sh                    # Start both servers (Linux/Mac only)
```

---

## Stopping the App

In each terminal press `Ctrl+C`.

---

## GitHub

Repository: **https://github.com/brankosli/OptimalFuel**
