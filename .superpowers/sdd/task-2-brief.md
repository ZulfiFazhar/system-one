# Task 2 Brief: Core Module Implementation

**Files:**
- Create: `D:\Zulfi\Programming\FastAPI\system-one\app\__init__.py`
- Create: `D:\Zulfi\Programming\FastAPI\system-one\app\core\__init__.py`
- Create: `D:\Zulfi\Programming\FastAPI\system-one\app\core\config.py`
- Create: `D:\Zulfi\Programming\FastAPI\system-one\app\core\schema.py`
- Create: `D:\Zulfi\Programming\FastAPI\system-one\app\core\security.py`

### Requirements
1. Create empty `app/__init__.py` and `app/core/__init__.py`.
2. Implement `app/core/config.py`:
```python
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
    laya_device: str = "auto"
    laya_preload: bool = True
    laya_mock_router: bool = False

    log_level: str = "INFO"
    log_format: str = "%(levelname)s - %(asctime)s - %(message)s"

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def is_development(self) -> bool:
        return self.environment.lower() == "development"


settings = Settings()
```

3. Implement `app/core/schema.py`:
```python
from enum import Enum
from typing import Any, Optional


class StatusEnum(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    ERROR = "error"
    WARNING = "warning"


class BaseResponse(dict):
    """Simple dict-like response wrapper for compatibility."""
    pass


def create_success_response(message: str = "Success", data: Any = None) -> dict[str, Any]:
    return {"status": StatusEnum.SUCCESS.value, "message": message, "data": data}


def create_error_response(message: str = "An error occurred", data: Any = None) -> dict[str, Any]:
    return {"status": StatusEnum.FAILED.value, "message": message, "data": data}
```

4. Implement `app/core/security.py`:
```python
import secrets
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

bearer_scheme = HTTPBearer(auto_error=False)


def verify_api_key(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> None:
    if not settings.laya_api_key or not settings.laya_api_key.get_secret_value():
        return

    expected_key = settings.laya_api_key.get_secret_value()
    if not credentials or not secrets.compare_digest(credentials.credentials, expected_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key",
        )
```

5. Verification:
Run: `uv run python -c "from app.core.config import settings; from app.core.security import verify_api_key; print('core ok')"`
Expected: Output `core ok`.

6. Commit:
`git add app/__init__.py app/core && git commit -m "feat: implement app.core config, schema, and security"`
