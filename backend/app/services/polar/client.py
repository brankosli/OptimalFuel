"""
Polar Accesslink API client — built from official API docs.
https://www.polar.com/accesslink-api/

Key notes:
- Exercises: new non-deprecated endpoint GET /v3/exercises (no transaction, no user-id in path)
- Sleep: GET /v3/users/{user-id}/sleep returns last 28 nights, then fetch each by ID
- Daily activity: GET /v3/users/activities (no user-id in path)
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
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{POLAR_API_BASE}/users/{self._user_id}",
                headers=self._headers(),
            )
            r.raise_for_status()
            return r.json()

    # ─── Exercises (NEW non-deprecated endpoint) ──────────────────────────────

    async def list_exercises(self) -> list[dict]:
        """
        List exercises from the NEW non-transaction endpoint.
        GET /v3/exercises — returns last 30 days, no user-id in path.
        Only exercises uploaded AFTER the user registered with this client are returned.
        """
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{POLAR_API_BASE}/exercises",
                headers=self._headers(),
                params={"samples": "false", "zones": "false", "route": "false"},
            )
            if r.status_code == 204:
                logger.info("Polar: no exercises available")
                return []
            r.raise_for_status()
            data = r.json()
            # Response is a list directly
            exercises = data if isinstance(data, list) else []
            logger.info(f"Polar: fetched {len(exercises)} exercises")
            return exercises

    # ─── Daily Activity ───────────────────────────────────────────────────────

    async def get_daily_activity(self, days_back: int = 28) -> list[dict]:
        """
        List daily activities for the past 28 days.
        GET /v3/users/activities — no user-id in path, returns last 28 days.
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

    # ─── Sleep ────────────────────────────────────────────────────────────────

    async def get_sleep(self) -> list[dict]:
        """
        Fetch sleep data. Two-step process per the API docs:
        1. GET /v3/users/{user-id}/sleep → list of nights with sleep IDs
        2. GET /v3/users/{user-id}/sleep/{sleep-id} → full detail for each night

        Returns last 28 nights.
        """
        async with httpx.AsyncClient() as client:
            # Step 1 — get list of available sleep records
            r = await client.get(
                f"{POLAR_API_BASE}/users/{self._user_id}/sleep",
                headers=self._headers(),
            )
            if r.status_code == 204:
                logger.info("Polar: no sleep data available")
                return []
            if r.status_code == 404:
                logger.warning("Polar: sleep endpoint 404 — make sure device has synced to Polar Flow app recently")
                return []
            r.raise_for_status()

            data = r.json()
            logger.debug(f"Polar sleep list response: {data}")

            # Response can be a list directly or {"nights": [...]}
            if isinstance(data, list):
                nights_list = data
            elif isinstance(data, dict):
                nights_list = data.get("nights", [])
            else:
                nights_list = []

            if not nights_list:
                logger.info("Polar: sleep list returned 0 nights")
                return []

            logger.info(f"Polar: {len(nights_list)} sleep records in list, fetching details...")

            # Step 2 — fetch full detail for each night
            results = []
            for night in nights_list:
                # Each night has an "id" field
                sleep_id = night.get("id") if isinstance(night, dict) else night
                if not sleep_id:
                    results.append(night)  # already detailed
                    continue

                detail_r = await client.get(
                    f"{POLAR_API_BASE}/users/{self._user_id}/sleep/{sleep_id}",
                    headers=self._headers(),
                )
                if detail_r.status_code == 200:
                    results.append(detail_r.json())
                else:
                    logger.warning(f"Polar: failed to fetch sleep {sleep_id}: {detail_r.status_code}")
                    results.append(night)  # fall back to summary

            logger.info(f"Polar: fetched {len(results)} sleep records with details")
            return results

    # ─── Nightly Recharge ─────────────────────────────────────────────────────

    async def get_nightly_recharge(self, date: str) -> Optional[dict]:
        """
        Get Nightly Recharge for a specific date (YYYY-MM-DD).
        Combines ANS charge + sleep charge into a recovery score.
        GET /v3/users/{user-id}/nightly-recharge/{date}
        """
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{POLAR_API_BASE}/users/{self._user_id}/nightly-recharge/{date}",
                headers=self._headers(),
            )
            if r.status_code == 200:
                return r.json()
            return None

    async def list_nightly_recharges(self) -> list[dict]:
        """
        List all Nightly Recharge records (last 28 days).
        GET /v3/users/{user-id}/nightly-recharge
        """
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{POLAR_API_BASE}/users/{self._user_id}/nightly-recharge",
                headers=self._headers(),
            )
            if r.status_code == 204:
                return []
            if r.status_code == 404:
                return []
            r.raise_for_status()
            data = r.json()
            return data.get("recharges", data if isinstance(data, list) else [])


# Singleton — one instance shared across the app
polar_client = PolarClient()