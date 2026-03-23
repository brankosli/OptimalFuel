"""
Strava API v3 client.
Handles automatic token refresh (Strava tokens expire every 6 hours).

Docs: https://developers.strava.com/docs/reference/
"""
import httpx
import logging
from datetime import datetime, timezone
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

STRAVA_API_BASE = "https://www.strava.com/api/v3"
STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"


class StravaClient:
    def __init__(self):
        self._access_token: Optional[str] = settings.strava_access_token
        self._refresh_token: Optional[str] = settings.strava_refresh_token
        self._expires_at: Optional[datetime] = None
        self._athlete_id: Optional[str] = settings.strava_athlete_id

        if settings.strava_token_expires_at:
            try:
                self._expires_at = datetime.fromisoformat(settings.strava_token_expires_at)
            except ValueError:
                pass

    def is_configured(self) -> bool:
        return bool(self._access_token and self._refresh_token)

    def _is_token_expired(self) -> bool:
        if not self._expires_at:
            return True
        now = datetime.now(tz=timezone.utc)
        expires = self._expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return now.timestamp() > expires.timestamp() - 300   # refresh 5 min early

    async def _refresh_access_token(self):
        """Exchange refresh token for a new access token."""
        async with httpx.AsyncClient() as client:
            r = await client.post(
                STRAVA_TOKEN_URL,
                data={
                    "client_id": settings.strava_client_id,
                    "client_secret": settings.strava_client_secret,
                    "refresh_token": self._refresh_token,
                    "grant_type": "refresh_token",
                },
            )
            r.raise_for_status()
            data = r.json()

        self._access_token = data["access_token"]
        self._refresh_token = data["refresh_token"]
        self._expires_at = datetime.fromtimestamp(data["expires_at"], tz=timezone.utc)

        # Persist to .env so next restart doesn't need re-auth
        # In production, store in DB instead
        logger.info("Strava: tokens refreshed successfully")

    async def _headers(self) -> dict:
        if self._is_token_expired():
            logger.info("Strava: token expired, refreshing...")
            await self._refresh_access_token()
        return {"Authorization": f"Bearer {self._access_token}"}

    # ─── Athlete ──────────────────────────────────────────────────────────────

    async def get_athlete(self) -> dict:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{STRAVA_API_BASE}/athlete",
                headers=await self._headers(),
            )
            r.raise_for_status()
            return r.json()

    # ─── Activities ───────────────────────────────────────────────────────────

    async def list_activities(
        self,
        after: Optional[int] = None,   # Unix timestamp
        before: Optional[int] = None,
        per_page: int = 50,
        page: int = 1,
    ) -> list[dict]:
        """
        List activities. Use `after` to fetch only new ones since last sync.
        Strava paginates at 200 max per page.
        """
        params = {"per_page": min(per_page, 200), "page": page}
        if after:
            params["after"] = after
        if before:
            params["before"] = before

        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{STRAVA_API_BASE}/athlete/activities",
                headers=await self._headers(),
                params=params,
            )
            r.raise_for_status()
            return r.json()

    async def get_activity(self, activity_id: int) -> dict:
        """Get detailed activity including segment efforts and laps."""
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{STRAVA_API_BASE}/activities/{activity_id}",
                headers=await self._headers(),
                params={"include_all_efforts": True},
            )
            r.raise_for_status()
            return r.json()

    async def get_activity_streams(
        self,
        activity_id: int,
        stream_types: list[str] = None,
    ) -> dict:
        """
        Get raw time-series streams for an activity.
        Useful for: heartrate, watts, velocity_smooth, altitude, cadence
        """
        if stream_types is None:
            stream_types = ["heartrate", "watts", "time", "velocity_smooth"]

        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{STRAVA_API_BASE}/activities/{activity_id}/streams",
                headers=await self._headers(),
                params={
                    "keys": ",".join(stream_types),
                    "key_by_type": True,
                },
            )
            if r.status_code == 404:
                return {}   # streams not available for all activity types
            r.raise_for_status()
            return r.json()

    async def list_all_activities_since(self, after_timestamp: int) -> list[dict]:
        """Paginate through all activities since a given timestamp."""
        all_activities = []
        page = 1
        while True:
            batch = await self.list_activities(after=after_timestamp, per_page=50, page=page)
            if not batch:
                break
            all_activities.extend(batch)
            if len(batch) < 50:
                break
            page += 1
        return all_activities


# Singleton
strava_client = StravaClient()
