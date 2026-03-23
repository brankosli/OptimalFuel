#!/bin/bash
# scripts/strava_auth.sh
# Run once to complete the Strava OAuth flow and store your tokens.
# Usage: ./scripts/strava_auth.sh

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"
source venv/bin/activate

python3 - << 'EOF'
import webbrowser, httpx
from app.core.config import settings

if not settings.strava_client_id:
    print("❌  STRAVA_CLIENT_ID not set in backend/.env")
    exit(1)

auth_url = (
    "https://www.strava.com/oauth/authorize"
    f"?client_id={settings.strava_client_id}"
    f"&redirect_uri={settings.strava_redirect_uri}"
    f"&response_type=code"
    f"&scope=read,activity:read_all"
)

print(f"\n🔗 Opening Strava login in your browser...")
print(f"   {auth_url}\n")
webbrowser.open(auth_url)
print("After authorizing, paste the full callback URL here:")
callback_url = input("> ").strip()

from urllib.parse import urlparse, parse_qs
code = parse_qs(urlparse(callback_url).query).get("code", [None])[0]
if not code:
    print("❌ Could not find 'code' in that URL")
    exit(1)

r = httpx.post(
    "https://www.strava.com/oauth/token",
    data={
        "client_id": settings.strava_client_id,
        "client_secret": settings.strava_client_secret,
        "code": code,
        "grant_type": "authorization_code",
    },
)
r.raise_for_status()
data = r.json()

import datetime
expires_at = datetime.datetime.fromtimestamp(data["expires_at"]).isoformat()
athlete = data.get("athlete", {})

print(f"\n✅ Got Strava tokens!")
print(f"   Athlete: {athlete.get('firstname')} {athlete.get('lastname')} (ID: {athlete.get('id')})")
print(f"\nAdd these to backend/.env:")
print(f"STRAVA_ACCESS_TOKEN={data['access_token']}")
print(f"STRAVA_REFRESH_TOKEN={data['refresh_token']}")
print(f"STRAVA_TOKEN_EXPIRES_AT={expires_at}")
print(f"STRAVA_ATHLETE_ID={athlete.get('id')}")
EOF
