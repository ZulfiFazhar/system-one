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
    port: int = 8000
    host: str = "0.0.0.0"

    allowed_origins: list[str] = ["*"]
    allowed_hosts: list[str] = ["*"]

    laya_api_key: SecretStr | None = None
    laya_model_path: str = "models/laya-multilingual"
    laya_device: str = "auto"
    laya_preload: bool = True

    log_level: str = "INFO"
    log_format: str = "%(levelname)s - %(asctime)s - %(message)s"

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def is_development(self) -> bool:
        return self.environment.lower() == "development"


settings = Settings()
