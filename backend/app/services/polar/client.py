"""
Polar Accesslink API client.
Handles token management and all API calls to the Polar platform.

Docs: https://www.polar.com/accesslink-api/
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

    # ─── Pull Notifications (transaction model) ───────────────────────────────

    async def list_exercises(self) -> list[dict]:
        """
        Polar uses a transaction model — you must:
        1. Create a transaction
        2. List available resources
        3. Fetch each resource
        4. Commit the transaction

        Returns list of exercise summaries.
        """
        async with httpx.AsyncClient() as client:
            # Create transaction
            r = await client.post(
                f"{POLAR_API_BASE}/users/{self._user_id}/exercise-transactions",
                headers=self._headers(),
            )
            if r.status_code == 204:
                logger.info("Polar: no new exercises")
                return []
            r.raise_for_status()
            transaction = r.json()
            transaction_id = transaction["transaction-id"]

            # List exercises in this transaction
            r = await client.get(
                f"{POLAR_API_BASE}/users/{self._user_id}/exercise-transactions/{transaction_id}",
                headers=self._headers(),
            )
            r.raise_for_status()
            exercises_data = r.json()
            exercise_urls = exercises_data.get("exercises", [])

            exercises = []
            for url in exercise_urls:
                ex_r = await client.get(url, headers=self._headers())
                if ex_r.status_code == 200:
                    exercises.append(ex_r.json())

            # Commit transaction (marks data as delivered)
            await client.put(
                f"{POLAR_API_BASE}/users/{self._user_id}/exercise-transactions/{transaction_id}",
                headers=self._headers(),
            )
            logger.info(f"Polar: fetched {len(exercises)} exercises")
            return exercises

    async def get_exercise_heart_rate_zones(self, exercise_id: str, transaction_id: str) -> Optional[dict]:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{POLAR_API_BASE}/users/{self._user_id}/exercise-transactions/{transaction_id}/{exercise_id}/heart-rate-zones",
                headers=self._headers(),
            )
            if r.status_code == 200:
                return r.json()
            return None

    # ─── Physical Info (weight, HR zones) ────────────────────────────────────

    async def get_physical_info(self) -> list[dict]:
        """Fetch latest physical info entries (weight, HR zones, etc.)."""
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{POLAR_API_BASE}/users/{self._user_id}/physical-information-transactions",
                headers=self._headers(),
            )
            if r.status_code == 204:
                return []
            r.raise_for_status()
            transaction = r.json()
            transaction_id = transaction["transaction-id"]

            r = await client.get(
                f"{POLAR_API_BASE}/users/{self._user_id}/physical-information-transactions/{transaction_id}",
                headers=self._headers(),
            )
            r.raise_for_status()
            urls = r.json().get("physical-informations", [])

            results = []
            for url in urls:
                res = await client.get(url, headers=self._headers())
                if res.status_code == 200:
                    results.append(res.json())

            # Commit
            await client.put(
                f"{POLAR_API_BASE}/users/{self._user_id}/physical-information-transactions/{transaction_id}",
                headers=self._headers(),
            )
            return results

    # ─── Daily Activity ───────────────────────────────────────────────────────

    async def get_daily_activity(self) -> list[dict]:
        """Fetch activity summaries (steps, calories, active time)."""
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{POLAR_API_BASE}/users/{self._user_id}/activity-transactions",
                headers=self._headers(),
            )
            if r.status_code == 204:
                return []
            r.raise_for_status()
            transaction_id = r.json()["transaction-id"]

            r = await client.get(
                f"{POLAR_API_BASE}/users/{self._user_id}/activity-transactions/{transaction_id}",
                headers=self._headers(),
            )
            r.raise_for_status()
            urls = r.json().get("activity-log", [])

            results = []
            for url in urls:
                res = await client.get(url, headers=self._headers())
                if res.status_code == 200:
                    results.append(res.json())

            await client.put(
                f"{POLAR_API_BASE}/users/{self._user_id}/activity-transactions/{transaction_id}",
                headers=self._headers(),
            )
            return results

    # ─── Sleep ────────────────────────────────────────────────────────────────

    async def get_sleep(self) -> list[dict]:
        """
        Fetch sleep data including Nightly Recharge.
        Uses the newer /sleep endpoint (not transaction-based).
        """
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{POLAR_API_BASE}/users/{self._user_id}/sleep-transactions",
                headers=self._headers(),
            )
            if r.status_code == 204:
                return []
            r.raise_for_status()
            transaction_id = r.json()["transaction-id"]

            r = await client.get(
                f"{POLAR_API_BASE}/users/{self._user_id}/sleep-transactions/{transaction_id}",
                headers=self._headers(),
            )
            r.raise_for_status()
            urls = r.json().get("nights", [])

            results = []
            for url in urls:
                res = await client.get(url, headers=self._headers())
                if res.status_code == 200:
                    results.append(res.json())

            await client.put(
                f"{POLAR_API_BASE}/users/{self._user_id}/sleep-transactions/{transaction_id}",
                headers=self._headers(),
            )
            logger.info(f"Polar: fetched {len(results)} sleep records")
            return results

    # ─── Nightly Recharge (ANS + Sleep charge) ────────────────────────────────

    async def get_nightly_recharge(self, date: str) -> Optional[dict]:
        """
        Get Nightly Recharge for a specific date (YYYY-MM-DD).
        This is Polar's key recovery metric combining ANS charge + sleep charge.
        """
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{POLAR_API_BASE}/users/{self._user_id}/nightly-recharge/{date}",
                headers=self._headers(),
            )
            if r.status_code == 200:
                return r.json()
            return None


# Singleton — one instance shared across the app
polar_client = PolarClient()
