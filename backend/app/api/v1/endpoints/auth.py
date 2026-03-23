"""Auth routes — Polar and Strava OAuth flows."""
import httpx
import os
import re
from datetime import datetime, timezone
from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()


def _env_path() -> str:
    """Locate the backend .env file."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.env"))


def _update_env(updates: dict):
    """Write key=value pairs back into the .env file."""
    env_path = _env_path()
    with open(env_path, "r") as f:
        content = f.read()
    for key, value in updates.items():
        content = re.sub(rf'{key}=.*', f'{key}="{value}"', content)
    with open(env_path, "w") as f:
        f.write(content)


# ─── Polar ────────────────────────────────────────────────────────────────────

@router.get("/polar")
async def polar_auth_start():
    """Return Polar OAuth consent URL."""
    polar_auth_url = (
        "https://flow.polar.com/oauth2/authorization"
        f"?response_type=code"
        f"&client_id={settings.polar_client_id}"
        f"&redirect_uri={settings.polar_redirect_uri}"
        f"&scope=accesslink.read_all"
    )
    return {"url": polar_auth_url}


@router.get("/polar/callback")
async def polar_callback(code: str):
    """Exchange Polar auth code for access token and save to .env."""

    # Exchange code for access token
    async with httpx.AsyncClient() as client:
        r = await client.post(
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

    access_token = data["access_token"]
    user_id = str(data.get("x_user_id", ""))

    # Register user with Accesslink (required first time, 409 = already done)
    async with httpx.AsyncClient() as client:
        reg = await client.post(
            "https://www.polaraccesslink.com/v3/users",
            json={"member-id": user_id},
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
        )
        if reg.status_code not in (200, 201, 409):
            print(f"Polar registration warning: {reg.status_code} {reg.text}")

    # Persist to .env
    _update_env({
        "POLAR_ACCESS_TOKEN": access_token,
        "POLAR_USER_ID": user_id,
    })

    # Update running config so no restart needed
    settings.polar_access_token = access_token
    settings.polar_user_id = user_id

    return {
        "message": "✅ Polar connected successfully! You can close this tab.",
        "user_id": user_id,
    }


# ─── Strava ───────────────────────────────────────────────────────────────────

@router.get("/strava")
async def strava_auth_start():
    """Return Strava OAuth consent URL."""
    strava_auth_url = (
        "https://www.strava.com/oauth/authorize"
        f"?client_id={settings.strava_client_id}"
        f"&redirect_uri={settings.strava_redirect_uri}"
        f"&response_type=code"
        f"&scope=read,activity:read_all"
    )
    return {"url": strava_auth_url}


@router.get("/strava/callback")
async def strava_callback(code: str, scope: str = ""):
    """Exchange Strava auth code for access + refresh tokens and save to .env."""

    async with httpx.AsyncClient() as client:
        r = await client.post(
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

    access_token  = data["access_token"]
    refresh_token = data["refresh_token"]
    expires_at    = datetime.fromtimestamp(data["expires_at"], tz=timezone.utc).isoformat()
    athlete       = data.get("athlete", {})
    athlete_id    = str(athlete.get("id", ""))

    # Persist to .env
    _update_env({
        "STRAVA_ACCESS_TOKEN":    access_token,
        "STRAVA_REFRESH_TOKEN":   refresh_token,
        "STRAVA_TOKEN_EXPIRES_AT": expires_at,
        "STRAVA_ATHLETE_ID":      athlete_id,
    })

    # Update running config so no restart needed
    settings.strava_access_token  = access_token
    settings.strava_refresh_token = refresh_token
    settings.strava_token_expires_at = expires_at
    settings.strava_athlete_id    = athlete_id

    return {
        "message": "✅ Strava connected successfully! You can close this tab.",
        "athlete": f"{athlete.get('firstname')} {athlete.get('lastname')}",
        "athlete_id": athlete_id,
    }


# ─── Status ───────────────────────────────────────────────────────────────────

@router.get("/status")
async def auth_status():
    """Check which integrations are connected."""

    polar_connected  = bool(settings.polar_access_token and settings.polar_user_id)
    strava_connected = bool(settings.strava_access_token and settings.strava_refresh_token)

    strava_expired = False
    if strava_connected and settings.strava_token_expires_at:
        try:
            expires = datetime.fromisoformat(settings.strava_token_expires_at)
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            strava_expired = datetime.now(timezone.utc) > expires
        except ValueError:
            pass

    return {
        "polar": {
            "connected": polar_connected,
            "user_id": settings.polar_user_id if polar_connected else None,
        },
        "strava": {
            "connected": strava_connected,
            "athlete_id": settings.strava_athlete_id if strava_connected else None,
            "token_expired": strava_expired,
        },
    }