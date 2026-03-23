#!/bin/bash
# scripts/polar_auth.sh
# Run once to complete the Polar OAuth flow and store your tokens.
# Usage: ./scripts/polar_auth.sh

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"
source venv/bin/activate

python3 - << 'EOF'
import webbrowser, httpx
from app.core.config import settings

if not settings.polar_client_id:
    print("❌  POLAR_CLIENT_ID not set in backend/.env")
    exit(1)

auth_url = (
    "https://flow.polar.com/oauth2/authorization"
    f"?response_type=code"
    f"&client_id={settings.polar_client_id}"
    f"&redirect_uri={settings.polar_redirect_uri}"
    f"&scope=accesslink.read_all"
)

print(f"\n🔗 Opening Polar login in your browser...")
print(f"   {auth_url}\n")
webbrowser.open(auth_url)
print("After authorizing, paste the full callback URL here:")
callback_url = input("> ").strip()

# Extract code from URL
from urllib.parse import urlparse, parse_qs
code = parse_qs(urlparse(callback_url).query).get("code", [None])[0]
if not code:
    print("❌ Could not find 'code' in that URL")
    exit(1)

# Exchange for token
r = httpx.post(
    "https://polarremote.com/v2/oauth2/token",
    data={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.polar_redirect_uri,
    },
    auth=(settings.polar_client_id, settings.polar_client_secret),
)
r.raise_for_status()
data = r.json()
print(f"\n✅ Got Polar access token!")
print(f"   User ID:  {data.get('x_user_id')}")
print(f"\nAdd these to backend/.env:")
print(f"POLAR_ACCESS_TOKEN={data['access_token']}")
print(f"POLAR_USER_ID={data.get('x_user_id')}")

# Register user with Accesslink (required first-time step)
reg = httpx.post(
    "https://www.polaraccesslink.com/v3/users",
    json={"member-id": str(data.get("x_user_id"))},
    headers={
        "Authorization": f"Bearer {data['access_token']}",
        "Content-Type": "application/json",
    }
)
if reg.status_code in (200, 409):  # 409 = already registered, fine
    print("\n✅ User registered with Polar Accesslink")
else:
    print(f"\n⚠️  Registration response: {reg.status_code} — {reg.text}")
EOF
