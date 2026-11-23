from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="F5_", env_file=".env", extra="ignore")
    base_url: str = "https://us1.calypsoai.app"
    token: SecretStr = Field(default=SecretStr(""), exclude=True, repr=False)
    project: str = ""
    timeout: float = Field(default=30, gt=0, le=300, allow_inf_nan=False)
    concurrency: int = Field(default=5, ge=1, le=50)
    retries: int = Field(default=2, ge=0, le=5)
    retry_scan_responses: bool = False
    flag_only: bool = False
    result_dir: Path = Path("results")
    persist: bool = False
    max_file_bytes: int = Field(default=10 * 1024 * 1024, ge=1, le=100 * 1024 * 1024)

    @field_validator("base_url")
    @classmethod
    def valid_origin(cls, value):
        p = urlsplit(value.strip())
        if p.scheme != "https" and not (
            p.scheme == "http" and p.hostname in ("localhost", "127.0.0.1", "::1")
        ):
            raise ValueError("Use HTTPS (HTTP is permitted only for localhost)")
        if not p.hostname or p.username or p.password or p.query or p.fragment:
            raise ValueError("Tenant URL must not contain credentials, query or fragment")
        path = p.path.rstrip("/")
        if not path.endswith("/backend/v1"):
            path += "/backend/v1"
        return urlunsplit((p.scheme, p.netloc, path, "", ""))

    def snapshot(self):
        return self.model_dump(mode="json")
