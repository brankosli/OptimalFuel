"""Auth routes — Polar and Strava OAuth flows."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/polar")
async def polar_auth_start():
    """Redirect user to Polar OAuth consent screen."""
    from app.core.config import settings
    polar_auth_url = (
        "https://flow.polar.com/oauth2/authorization"
        f"?response_type=code"
        f"&client_id={settings.polar_client_id}"
        f"&redirect_uri={settings.polar_redirect_uri}"
        f"&scope=accesslink.read_all"
    )
    return {"url": polar_auth_url}   # Frontend handles the redirect


@router.get("/polar/callback")
async def polar_callback(code: str):
    """Exchange Polar auth code for access token."""
    # TODO: implement token exchange + store in DB
    return {"message": "Polar OAuth callback — implement token exchange here", "code": code}


@router.get("/strava")
async def strava_auth_start():
    """Redirect user to Strava OAuth consent screen."""
    from app.core.config import settings
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
    """Exchange Strava auth code for access + refresh tokens."""
    # TODO: implement token exchange + store in DB
    return {"message": "Strava OAuth callback — implement token exchange here", "code": code}


@router.get("/status")
async def auth_status():
    """Check which integrations are connected."""
    # TODO: check DB for valid tokens
    return {
        "polar": {"connected": False},
        "strava": {"connected": False},
    }
