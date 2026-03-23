from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "OptimalFuel"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    secret_key: str = "change-me"

    # Database
    database_url: str = "sqlite+aiosqlite:///./optimalfuel.db"
    db_echo: bool = False

    # Polar
    polar_client_id: str = ""
    polar_client_secret: str = ""
    polar_redirect_uri: str = "http://localhost:8000/api/v1/auth/polar/callback"
    polar_access_token: Optional[str] = None
    polar_token_expires_at: Optional[str] = None
    polar_user_id: Optional[str] = None

    # Strava
    strava_client_id: str = ""
    strava_client_secret: str = ""
    strava_redirect_uri: str = "http://localhost:8000/api/v1/auth/strava/callback"
    strava_access_token: Optional[str] = None
    strava_refresh_token: Optional[str] = None
    strava_token_expires_at: Optional[str] = None
    strava_athlete_id: Optional[str] = None

    # Nutrition (optional)
    edamam_app_id: Optional[str] = None
    edamam_app_key: Optional[str] = None

    # Scheduler
    sync_interval_minutes: int = 30

    # CORS
    frontend_url: str = "http://localhost:5173"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


settings = Settings()