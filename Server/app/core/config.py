"""Application settings, loaded from the environment.

Every secret comes from .env - nothing is hardcoded and nothing has a usable
default. Missing required values raise at import time, so the app fails to start
rather than running insecurely. See docs/SECURITY.md 5.11.
"""
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

SERVER_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=SERVER_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---------------------------------------------------------------- database
    database_url: str = Field(..., description="Owner URL: DDL. Used by init_db.py only.")
    app_database_url: str = ""       # DML-only URL used by the running API

    # ------------------------------------------------------ first admin account
    # Consumed by db/init_db.py only; the API never reads these.
    admin_email: str = ""
    admin_password: str = ""
    admin_first_name: str = "Admin"
    admin_last_name: str = "User"

    # ---------------------------------------------------------------- security
    jwt_secret: str
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    access_token_minutes: int = 60
    challenge_token_minutes: int = 10

    otp_ttl_minutes: int = 10
    otp_max_attempts: int = 5
    reset_token_ttl_minutes: int = 30

    max_failed_logins: int = 5
    lockout_minutes: int = 15
    password_min_length: int = 12

    # -------------------------------------------------------------------- mail
    mail_backend: Literal["console", "gmail"] = "console"
    mail_from: str = ""
    gmail_user: str = ""
    gmail_app_password: str = ""
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587

    # ----------------------------------------------------------------- uploads
    upload_dir: str = "uploads"
    max_upload_bytes: int = 2 * 1024 * 1024
    max_image_pixels: int = 40_000_000

    # --------------------------------------------------------------------- app
    env: Literal["dev", "staging", "production"] = "dev"
    cors_origins: str = "http://localhost:5173"

    # ------------------------------------------------------------- validation
    @field_validator("jwt_secret")
    @classmethod
    def _secret_must_be_strong(cls, v: str) -> str:
        # A short or placeholder secret makes every JWT forgeable. Refuse to boot.
        if len(v) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters")
        if v.lower() in {"changeme", "secret", "dev", "test"}:
            raise ValueError("JWT_SECRET is a placeholder value")
        return v

    @field_validator("password_min_length")
    @classmethod
    def _min_password_floor(cls, v: int) -> int:
        if v < 12:
            raise ValueError("PASSWORD_MIN_LENGTH must be at least 12")
        return v

    # ---------------------------------------------------------------- derived
    @property
    def runtime_database_url(self) -> str:
        """The URL the API connects with. Falls back to the owner URL if the
        restricted role has not been set up - see SECURITY.md 2.6."""
        return self.app_database_url or self.database_url

    @property
    def uses_privileged_db_role(self) -> bool:
        return not self.app_database_url

    @property
    def upload_path(self) -> Path:
        p = Path(self.upload_dir)
        return p if p.is_absolute() else SERVER_DIR / p

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
