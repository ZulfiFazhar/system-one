from typing import ClassVar

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "System One (Laya) API"
    environment: str = "development"
    version: str = "0.1.0"

    allowed_origins: list[str] = ["*"]
    allowed_hosts: list[str] = ["*"]

    default_model: str = "laya"
    preload_models: list[str] = ["laya", "d3-lite", "kev"]

    # Laya
    laya_api_key: SecretStr | None = None
    laya_model_id: str = "convaiinnovations/laya-multilingual"
    laya_model_path: str = "models/laya-multilingual"
    laya_device: str = "auto"
    laya_preload: bool = True
    laya_lazy_load: bool = False

    # D3-Lite
    d3_lite_model_id: str = "vllm-sr/d3-lite"
    d3_lite_model_path: str = "models/d3-lite"
    d3_lite_device: str = "auto"
    d3_lite_trust_remote_code: bool = True

    # Kev
    kev_model_id: str = "jaredpalmer/kev-0.8b"
    kev_model_path: str = "models/kev-0.8b"
    kev_device: str = "auto"

    # Public Rate Limiting (when no API key is provided)
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 10
    rate_limit_window_seconds: int = 60

    # Dashboard & Admin
    admin_username: str = "admin"
    admin_password: str = "changeme"
    admin_session_secret: str = ""
    database_path: str = "data/dashboard.db"

    log_level: str = "INFO"
    log_format: str = " ▕  %(levelname)s - %(asctime)s - %(message)s"

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def is_development(self) -> bool:
        return self.environment.lower() == "development"


settings = Settings()
