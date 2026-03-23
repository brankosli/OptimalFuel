# OptimalFuel

Personal training analytics and nutrition planning platform.
Integrates Polar Flow and Strava to tailor daily meal plans based on real training load and recovery data.

## Stack

- **Backend:** Python 3.11 + FastAPI + SQLite (via SQLAlchemy)
- **Frontend:** React 18 + TypeScript + Vite
- **Scheduling:** APScheduler (in-process, no Redis needed)
- **Migrations:** Alembic

## Integrations

- **Polar Accesslink API** — sleep, HRV, Nightly Recharge, training load, exercises
- **Strava API** — activities, HR streams, power data

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- A Polar Accesslink app (register at https://admin.polaraccesslink.com)
- A Strava API app (register at https://www.strava.com/settings/api)

### Setup

```bash
# 1. Clone and enter project
cd optimalfuel

# 2. Backend setup
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # Fill in your API credentials
alembic upgrade head            # Run DB migrations

# 3. Frontend setup
cd ../frontend
npm install
cp .env.example .env.local

# 4. Run both (from root)
./scripts/dev.sh
```

### OAuth Setup

#### Polar
1. Go to https://admin.polaraccesslink.com
2. Create a new API client
3. Set redirect URI to `http://localhost:8000/api/v1/auth/polar/callback`
4. Copy Client ID and Secret to backend `.env`
5. Run `./scripts/polar_auth.sh` to complete OAuth flow

#### Strava
1. Go to https://www.strava.com/settings/api
2. Set Authorization Callback Domain to `localhost`
3. Copy Client ID and Secret to backend `.env`
4. Run `./scripts/strava_auth.sh` to complete OAuth flow

## Project Structure

```
optimalfuel/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/   # Route handlers
│   │   ├── core/               # Config, security, scheduler
│   │   ├── db/                 # Database session, base
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── schemas/            # Pydantic schemas
│   │   ├── services/           # Business logic
│   │   │   ├── polar/          # Polar API client + sync
│   │   │   ├── strava/         # Strava API client + sync
│   │   │   ├── analytics/      # ATL/CTL/TSB, recovery scoring
│   │   │   └── nutrition/      # Caloric targets, macro splits
│   │   ├── tasks/              # Scheduled sync jobs
│   │   └── utils/              # Helpers
│   ├── alembic/                # DB migrations
│   └── tests/
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── charts/         # PMC, HR, sleep charts
│       │   ├── layout/         # Shell, nav, sidebar
│       │   ├── nutrition/      # Meal plan UI
│       │   └── training/       # Activity cards, load viz
│       ├── pages/              # Dashboard, Training, Nutrition, Sleep
│       ├── hooks/              # Data fetching hooks
│       ├── store/              # Zustand state
│       └── types/              # Shared TypeScript types
├── docs/                       # API docs, data model diagrams
└── scripts/                    # Dev helpers, auth scripts
```
