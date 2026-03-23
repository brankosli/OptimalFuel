"""
Polar Accesslink API client.
Endpoints verified from official Polar example:
https://github.com/polarofficial/accesslink-example-python/blob/master/accesslink/accesslink.py

Correct endpoints:
- Exercises:        GET /v3/exercises
- Sleep:            GET /v3/users/sleep/            (trailing slash, NO user-id)
- Nightly Recharge: GET /v3/users/nightly-recharge/ (trailing slash, NO user-id)
- Daily Activity:   GET /v3/users/activities
- User info:        GET /v3/users/{user-id}         (only this one has user-id)
"""
import httpx
import logging
from datetime import datetime, timezone
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

POLAR_API_BASE = "https://www.polaraccesslink.com/v3"


class PolarClient:
    def __init__(self):
        self._access_token: Optional[str] = settings.polar_access_token
        self._user_id: Optional[str] = settings.polar_user_id

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Accept": "application/json",
        }

    def is_configured(self) -> bool:
        return bool(self._access_token and self._user_id)

    # ─── User ─────────────────────────────────────────────────────────────────

    async def get_user_info(self) -> dict:
        """GET /v3/users/{user-id} — only endpoint that uses user-id in path."""
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{POLAR_API_BASE}/users/{self._user_id}",
                headers=self._headers(),
            )
            r.raise_for_status()
            return r.json()

    # ─── Exercises ────────────────────────────────────────────────────────────

    async def list_exercises(self) -> list[dict]:
        """
        GET /v3/exercises
        No user-id in path. Returns last 30 days.
        Only exercises uploaded AFTER user registered with this client.
        """
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{POLAR_API_BASE}/exercises",
                headers=self._headers(),
            )
            if r.status_code == 204:
                logger.info("Polar: no exercises available")
                return []
            r.raise_for_status()
            data = r.json()
            exercises = data if isinstance(data, list) else []
            logger.info(f"Polar: fetched {len(exercises)} exercises")
            return exercises

    # ─── Sleep ────────────────────────────────────────────────────────────────

    async def get_sleep(self) -> list[dict]:
        """
        GET /v3/users/sleep/
        Trailing slash required. NO user-id in path.
        Returns last 28 nights.
        """
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{POLAR_API_BASE}/users/sleep/",
                headers=self._headers(),
            )
            if r.status_code == 204:
                logger.info("Polar: no sleep data available")
                return []
            if r.status_code == 404:
                logger.warning(f"Polar: sleep 404 — {r.text}")
                return []
            r.raise_for_status()
            data = r.json()
            logger.debug(f"Polar sleep raw response: {data}")

            if isinstance(data, list):
                nights = data
            elif isinstance(data, dict):
                nights = data.get("nights", [])
            else:
                nights = []

            logger.info(f"Polar: fetched {len(nights)} sleep records")
            return nights

    # ─── Nightly Recharge ─────────────────────────────────────────────────────

    async def list_nightly_recharges(self) -> list[dict]:
        """
        GET /v3/users/nightly-recharge/
        Trailing slash required. NO user-id in path.
        Returns last 28 days.
        """
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{POLAR_API_BASE}/users/nightly-recharge/",
                headers=self._headers(),
            )
            if r.status_code == 204:
                return []
            if r.status_code == 404:
                logger.warning(f"Polar: nightly-recharge 404 — {r.text}")
                return []
            r.raise_for_status()
            data = r.json()
            if isinstance(data, list):
                return data
            return data.get("recharges", [])

    async def get_nightly_recharge(self, date: str) -> Optional[dict]:
        """GET /v3/users/nightly-recharge/{date}"""
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{POLAR_API_BASE}/users/nightly-recharge/{date}",
                headers=self._headers(),
            )
            if r.status_code == 200:
                return r.json()
            return None

    # ─── Daily Activity ───────────────────────────────────────────────────────

    async def get_daily_activity(self) -> list[dict]:
        """
        GET /v3/users/activities
        No user-id in path. Returns last 28 days.
        """
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{POLAR_API_BASE}/users/activities",
                headers=self._headers(),
            )
            if r.status_code == 204:
                logger.info("Polar: no daily activity data")
                return []
            r.raise_for_status()
            data = r.json()
            activities = data if isinstance(data, list) else []
            logger.info(f"Polar: fetched {len(activities)} daily activity records")
            return activities


# Singleton — one instance shared across the app
polar_client = PolarClient()