# Project Structure Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor `system-one` structure to match `helpdesk-ai-fastapi` (`app/` layout with `core`, `api`, `dto`, `services`, `main.py`, UV config).

**Architecture:** Transition from flat `src/` to modular `app/` directory. Move configuration to `app/core/config.py` using `pydantic-settings`, server setup and lifespan to `app/core/server.py`, schemas to `app/dto/systemone_dto.py`, business logic to `app/services/laya_service.py`, and endpoints to `app/api/`. Update `pyproject.toml` to UV application format with entrypoint `app.main:app`.

**Tech Stack:** FastAPI, Pydantic v2, Pydantic Settings, UV, Pytest, HTTPX.

---

### Task 1: Update Project Configuration & Dependencies

**Files:**
- Modify: `pyproject.toml`
- Create: `.env.example`
- Create: `pyrightconfig.json`

- [ ] **Step 1: Update pyproject.toml to match helpdesk-ai-fastapi configuration**

Replace build-backend and `src` references with `app.main:app` and `[tool.uv] package = false`.

```toml
[project]
name = "system-one"
version = "0.1.0"
description = "System One Model API for Laya compatible with TypeSafe Jev"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "fastapi[standard]>=0.141.1",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
]

[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "httpx>=0.27.0",
]

[tool.uv]
package = false

[tool.fastapi]
entrypoint = "app.main:app"

[tool.pytest.ini_options]
asyncio_mode = "auto"
pythonpath = ["."]
```

- [ ] **Step 2: Create .env.example**

Create `.env.example` defining environment variables:

```bash
# Application Settings
APP_NAME="System One (Laya) API"
ENVIRONMENT=development
VERSION=0.1.0
PORT=8000
HOST=0.0.0.0

# Security & CORS
ALLOWED_ORIGINS=["*"]
ALLOWED_HOSTS=["*"]
LAYA_API_KEY=""

# Laya Model Settings
LAYA_DEVICE="auto"
LAYA_PRELOAD=true
LAYA_MOCK_ROUTER=false

# Logging
LOG_LEVEL="INFO"
```

- [ ] **Step 3: Create pyrightconfig.json**

Create `pyrightconfig.json` matching `helpdesk-ai-fastapi`:

```json
{
    "reportMissingImports": "none",
    "reportMissingModuleSource": "none",
    "reportAttributeAccessIssue": "none",
    "reportCallIssue": "none",
    "reportUnknownMemberType": "none",
    "reportUnknownVariableType": "none",
    "reportUnknownArgumentType": "none",
    "reportUnknownParameterType": "none",
    "reportMissingParameterType": "none",
    "reportAny": "none"
}
```

- [ ] **Step 4: Verify uv sync succeeds**

Run: `uv sync`
Expected: Resolved packages and sync completed without build errors.

---

### Task 2: Core Module Implementation (`app/core/`)

**Files:**
- Create: `app/__init__.py`
- Create: `app/core/__init__.py`
- Create: `app/core/config.py`
- Create: `app/core/schema.py`
- Create: `app/core/security.py`

- [ ] **Step 1: Create app/__init__.py and app/core/__init__.py**

Create empty files `app/__init__.py` and `app/core/__init__.py`.

- [ ] **Step 2: Implement app/core/config.py**

Create `app/core/config.py` using `pydantic_settings.BaseSettings`:

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

- [ ] **Step 3: Implement app/core/schema.py**

Create `app/core/schema.py` for standard API responses:

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

- [ ] **Step 4: Implement app/core/security.py**

Create `app/core/security.py`:

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

- [ ] **Step 5: Run quick unit check for config and security**

Run: `uv run python -c "from app.core.config import settings; from app.core.security import verify_api_key; print('core ok')"`
Expected: Output `core ok`.

---

### Task 3: DTO Module Implementation (`app/dto/`)

**Files:**
- Create: `app/dto/__init__.py`
- Create: `app/dto/systemone_dto.py`

- [ ] **Step 1: Create app/dto/__init__.py**

Create `app/dto/__init__.py` exporting all DTOs:

```python
from app.dto.systemone_dto import (
    Answer,
    ChoiceAnswer,
    ChoiceQuestion,
    NoulAnswer,
    NoulQuestion,
    Question,
    ScoreAnswer,
    ScoreQuestion,
    SystemOneRequest,
    SystemOneResponse,
    Usage,
)

__all__ = [
    "Answer",
    "ChoiceAnswer",
    "ChoiceQuestion",
    "NoulAnswer",
    "NoulQuestion",
    "Question",
    "ScoreAnswer",
    "ScoreQuestion",
    "SystemOneRequest",
    "SystemOneResponse",
    "Usage",
]
```

- [ ] **Step 2: Create app/dto/systemone_dto.py**

Port schemas from `src/schemas.py`:

```python
from typing import Annotated, Any, Literal, Union
from pydantic import BaseModel, Field


class NoulQuestion(BaseModel):
    type: Literal["noul"] = "noul"
    instructions: str | dict[str, Any] | list[Any]
    criteria: dict[str, Any] | None = None


class ChoiceQuestion(BaseModel):
    type: Literal["choice"] = "choice"
    instructions: str | dict[str, Any] | list[Any]
    criteria: dict[str, Any]


class ScoreQuestion(BaseModel):
    type: Literal["score"] = "score"
    instructions: str | dict[str, Any] | list[Any]
    criteria: Annotated[list[Any], Field(min_length=2, max_length=10)]


Question = Annotated[
    Union[NoulQuestion, ChoiceQuestion, ScoreQuestion],
    Field(discriminator="type"),
]


class SystemOneRequest(BaseModel):
    state: str | dict[str, Any] | list[Any]
    model: str = "laya"
    questions: dict[str, Question] = Field(min_length=1)


class NoulAnswer(BaseModel):
    type: Literal["noul"] = "noul"
    noul: float


class ChoiceAnswer(BaseModel):
    type: Literal["choice"] = "choice"
    choice: str
    probabilities: dict[str, float]
    confidence: float


class ScoreAnswer(BaseModel):
    type: Literal["score"] = "score"
    score: float
    legend: dict[str, str]
    probabilities: dict[str, float]
    confidence: float


Answer = Annotated[
    Union[NoulAnswer, ChoiceAnswer, ScoreAnswer],
    Field(discriminator="type"),
]


class Usage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0


class SystemOneResponse(BaseModel):
    model: str
    answers: dict[str, Answer]
    usage: Usage
```

- [ ] **Step 3: Run quick import check for DTOs**

Run: `uv run python -c "from app.dto import SystemOneRequest, SystemOneResponse; print('dto ok')"`
Expected: Output `dto ok`.

---

### Task 4: Services Implementation (`app/services/`)

**Files:**
- Create: `app/services/__init__.py`
- Create: `app/services/laya_service.py`
- Create: `app/services/health.py`

- [ ] **Step 1: Create app/services/__init__.py**

Create empty `app/services/__init__.py`.

- [ ] **Step 2: Implement app/services/laya_service.py**

Port `MockRouter`, `estimate_usage`, and `format_jev_response`:

```python
import json
from typing import Any

from app.dto.systemone_dto import (
    Answer,
    ChoiceAnswer,
    ChoiceQuestion,
    NoulAnswer,
    NoulQuestion,
    Question,
    ScoreAnswer,
    ScoreQuestion,
    SystemOneResponse,
    Usage,
)


class MockRouter:
    def predict(
        self, state: Any, questions: dict[str, Any], model: str | None = None
    ) -> dict[str, Any]:
        answers = {}
        for q_id, q in questions.items():
            q_type = q.type if hasattr(q, "type") else q.get("type")
            if q_type == "noul":
                answers[q_id] = {"noul": 0.85}
            elif q_type == "choice":
                crit = q.criteria if hasattr(q, "criteria") else q.get("criteria", {})
                first_opt = next(iter(crit.keys())) if crit else "default"
                answers[q_id] = {
                    "choice": first_opt,
                    "probabilities": {k: 1.0 / len(crit) for k in crit},
                    "confidence": 0.9,
                }
            elif q_type == "score":
                answers[q_id] = {
                    "score": 1.0,
                    "probabilities": {"0": 0.2, "1": 0.8},
                    "confidence": 0.8,
                }
        return {"answers": answers, "routing": {"model": model or "laya"}}

    def unload(self) -> None:
        pass


def estimate_usage(state: Any, questions: dict[str, Question]) -> Usage:
    # ponytail: naive char-count token estimation (~4 chars/token). upgrade to tiktoken when exact billing needed.
    state_str = state if isinstance(state, str) else json.dumps(state)
    q_str = "".join(str(q.instructions) for q in questions.values())
    in_tokens = max(1, (len(state_str) + len(q_str)) // 4)
    out_tokens = max(1, len(questions) * 4)
    return Usage(input_tokens=in_tokens, output_tokens=out_tokens)


def format_jev_response(
    model_name: str,
    laya_answers: dict[str, Any],
    questions: dict[str, Question],
    state: Any,
) -> SystemOneResponse:
    answers: dict[str, Answer] = {}

    for q_id, q_spec in questions.items():
        ans_raw = laya_answers.get(q_id, {})
        if ans_raw is None:
            ans_raw = {}

        if isinstance(q_spec, NoulQuestion):
            val = ans_raw.get("noul") if isinstance(ans_raw, dict) else ans_raw
            if val is None:
                val = 0.0
            answers[q_id] = NoulAnswer(type="noul", noul=float(val))

        elif isinstance(q_spec, ChoiceQuestion):
            if not isinstance(ans_raw, dict):
                ans_raw = {"choice": str(ans_raw)}
            choice_val = ans_raw.get("choice") or ""
            probs = ans_raw.get("probabilities") or {choice_val: 1.0}
            conf = ans_raw.get("confidence")
            if conf is None:
                conf = max(probs.values()) if probs else 1.0
            answers[q_id] = ChoiceAnswer(
                type="choice",
                choice=choice_val,
                probabilities={str(k): float(v) for k, v in probs.items()},
                confidence=float(conf),
            )

        elif isinstance(q_spec, ScoreQuestion):
            if not isinstance(ans_raw, dict):
                ans_raw = {"score": float(ans_raw)}
            score_val = ans_raw.get("score")
            if score_val is None:
                score_val = 0.0
            legend = {str(idx): str(item) for idx, item in enumerate(q_spec.criteria)}
            probs = ans_raw.get("probabilities") or {}
            if not probs:
                probs = {
                    str(idx): 1.0 / len(q_spec.criteria)
                    for idx in range(len(q_spec.criteria))
                }
            conf = ans_raw.get("confidence")
            if conf is None:
                conf = max(probs.values()) if probs else 1.0
            answers[q_id] = ScoreAnswer(
                type="score",
                score=float(score_val),
                legend=legend,
                probabilities={str(k): float(v) for k, v in probs.items()},
                confidence=float(conf),
            )

    return SystemOneResponse(
        model=model_name,
        answers=answers,
        usage=estimate_usage(state, questions),
    )
```

- [ ] **Step 3: Implement app/services/health.py**

Create `app/services/health.py`:

```python
from typing import Any


def check_health(app_state: Any) -> dict[str, Any]:
    router_ready = hasattr(app_state, "router") and app_state.router is not None
    return {
        "status": "ready" if router_ready else "initializing",
        "model": "laya",
        "preloaded": True,
    }
```

---

### Task 5: API Routes, Server & Main Entrypoint (`app/api/`, `app/core/server.py`, `app/main.py`)

**Files:**
- Create: `app/api/__init__.py`
- Create: `app/api/health_route.py`
- Create: `app/api/systemone_route.py`
- Create: `app/core/server.py`
- Create: `app/main.py`

- [ ] **Step 1: Implement app/api/health_route.py**

Create `app/api/health_route.py`:

```python
from typing import Any
from fastapi import APIRouter, Request
from app.services.health import check_health

router = APIRouter()


@router.get("/healthz")
@router.get("/health")
def health(request: Request) -> dict[str, Any]:
    return check_health(request.app.state)
```

- [ ] **Step 2: Implement app/api/systemone_route.py**

Create `app/api/systemone_route.py`:

```python
from fastapi import APIRouter, Depends, Request
from fastapi.concurrency import run_in_threadpool

from app.core.security import verify_api_key
from app.dto.systemone_dto import SystemOneRequest, SystemOneResponse
from app.services.laya_service import MockRouter, format_jev_response

router = APIRouter()


@router.post(
    "/systemone",
    response_model=SystemOneResponse,
    dependencies=[Depends(verify_api_key)],
)
async def systemone(req: SystemOneRequest, request: Request) -> SystemOneResponse:
    router_instance = getattr(request.app.state, "router", None)
    if router_instance is None:
        router_instance = MockRouter()
        request.app.state.router = router_instance

    questions_dict = {
        k: v.model_dump() if hasattr(v, "model_dump") else v
        for k, v in req.questions.items()
    }
    res = await run_in_threadpool(
        router_instance.predict,
        req.state,
        questions_dict,
        req.model,
    )
    laya_answers = res.get("answers", {})
    return format_jev_response(
        model_name=req.model,
        laya_answers=laya_answers,
        questions=req.questions,
        state=req.state,
    )
```

- [ ] **Step 3: Implement app/api/__init__.py**

Create `app/api/__init__.py`:

```python
from fastapi import APIRouter
from app.api.health_route import router as health_router
from app.api.systemone_route import router as systemone_router

router = APIRouter()

router.include_router(health_router, tags=["health"])
router.include_router(systemone_router, prefix="/v1", tags=["systemone"])
```

- [ ] **Step 4: Implement app/core/server.py**

Create `app/core/server.py` with logging, middlewares, lifespan, and `create_application`:

```python
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.api import router as api_router
from app.api.health_route import router as root_health_router
from app.core.config import settings
from app.services.laya_service import MockRouter

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    logging.basicConfig(level=settings.log_level.upper(), format=settings.log_format)


def setup_middlewares(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    if settings.is_production:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not hasattr(app.state, "router"):
        if settings.laya_mock_router:
            app.state.router = MockRouter()
        else:
            try:
                import laya

                app.state.router = laya.Router(
                    preload=settings.laya_preload,
                    device=settings.laya_device,
                )
            except Exception:
                app.state.router = MockRouter()
    yield
    if hasattr(app.state, "router") and hasattr(app.state.router, "unload"):
        app.state.router.unload()


def create_application(mock_router: bool = False) -> FastAPI:
    setup_logging()

    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        lifespan=lifespan,
    )

    setup_middlewares(app)

    if mock_router or settings.laya_mock_router:
        app.state.router = MockRouter()

    # Mount health directly at root (/healthz) for backward compatibility
    app.include_router(root_health_router)
    # Mount api routes
    app.include_router(api_router)

    return app
```

- [ ] **Step 5: Implement app/main.py**

Create `app/main.py`:

```python
from app.core.server import create_application

app = create_application()

__all__ = ["app"]
```

---

### Task 6: Refactor Tests to Target `app/`

**Files:**
- Create: `tests/conftest.py`
- Modify: `tests/test_api.py`
- Modify: `tests/test_schemas.py`
- Modify: `tests/test_adapter.py`

- [ ] **Step 1: Create tests/conftest.py**

Create `tests/conftest.py` with test client fixtures:

```python
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.config import settings
from app.core.server import create_application


@pytest.fixture
def client_no_auth(monkeypatch):
    monkeypatch.setattr(settings, "laya_api_key", None)
    monkeypatch.setattr(settings, "laya_mock_router", True)
    app = create_application(mock_router=True)
    return TestClient(app)


@pytest.fixture
def client_with_auth(monkeypatch):
    monkeypatch.setattr(settings, "laya_api_key", SecretStr("secret-token-123"))
    monkeypatch.setattr(settings, "laya_mock_router", True)
    app = create_application(mock_router=True)
    return TestClient(app)
```

- [ ] **Step 2: Update tests/test_api.py**

Update imports in `tests/test_api.py` to use `app.core.server.create_application` and `app.core.security.verify_api_key`:

```python
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from app.core.server import create_application


def test_healthz(client_no_auth):
    resp = client_no_auth.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"


def test_systemone_unauthorized(client_with_auth):
    resp = client_with_auth.post("/v1/systemone", json={
        "state": "test",
        "questions": {"q": {"type": "noul", "instructions": "test"}}
    })
    assert resp.status_code == 401


def test_systemone_authorized_mock(client_with_auth):
    resp = client_with_auth.post(
        "/v1/systemone",
        headers={"Authorization": "Bearer secret-token-123"},
        json={
            "state": "test duplicate charge",
            "questions": {
                "is_refund": {
                    "type": "noul",
                    "instructions": "Is refund requested?"
                }
            }
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["model"] == "laya"
    assert "is_refund" in data["answers"]
    assert data["answers"]["is_refund"]["type"] == "noul"


def test_systemone_invalid_schema(client_no_auth):
    resp = client_no_auth.post("/v1/systemone", json={
        "state": "test",
        "questions": {
            "invalid_score": {
                "type": "score",
                "instructions": "rate",
                "criteria": ["only one"]
            }
        }
    })
    assert resp.status_code == 422


def test_systemone_wrong_token(client_with_auth):
    resp = client_with_auth.post(
        "/v1/systemone",
        headers={"Authorization": "Bearer wrong-token"},
        json={
            "state": "test",
            "questions": {"q": {"type": "noul", "instructions": "test"}}
        }
    )
    assert resp.status_code == 401


def test_systemone_multi_question(client_no_auth):
    resp = client_no_auth.post(
        "/v1/systemone",
        json={
            "state": "urgent billing issue",
            "model": "laya",
            "questions": {
                "urgent": {"type": "noul", "instructions": "Is urgent?"},
                "category": {
                    "type": "choice",
                    "instructions": "Category?",
                    "criteria": {"billing": "Billing", "tech": "Tech"}
                },
                "frustration": {
                    "type": "score",
                    "instructions": "Rate frustration",
                    "criteria": ["Low", "High"]
                }
            }
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["model"] == "laya"
    assert data["answers"]["urgent"]["type"] == "noul"
    assert data["answers"]["category"]["type"] == "choice"
    assert data["answers"]["frustration"]["type"] == "score"
    assert "usage" in data


def test_lifespan_lifecycle():
    app = create_application(mock_router=True)
    with TestClient(app) as client:
        resp = client.get("/healthz")
        assert resp.status_code == 200
        assert hasattr(app.state, "router")


def test_verify_api_key_constant_time(monkeypatch):
    import secrets
    from unittest.mock import patch
    from fastapi import HTTPException
    from fastapi.security import HTTPAuthorizationCredentials
    from app.core.config import settings
    from app.core.security import verify_api_key

    monkeypatch.setattr(settings, "laya_api_key", SecretStr("secret-val"))
    with patch("secrets.compare_digest", wraps=secrets.compare_digest) as mock_compare:
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="secret-val")
        verify_api_key(creds)
        mock_compare.assert_called_with("secret-val", "secret-val")

        mock_compare.reset_mock()
        with pytest.raises(HTTPException) as exc_info:
            bad_creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="wrong-val")
            verify_api_key(bad_creds)
        assert exc_info.value.status_code == 401
        mock_compare.assert_called_with("wrong-val", "secret-val")
```

- [ ] **Step 3: Update tests/test_schemas.py**

Update imports to `from app.dto import ...`:

```python
import pytest
from pydantic import ValidationError
from app.dto import (
    ChoiceAnswer,
    ChoiceQuestion,
    NoulAnswer,
    NoulQuestion,
    ScoreAnswer,
    ScoreQuestion,
    SystemOneRequest,
    SystemOneResponse,
    Usage,
)


def test_valid_request_schema():
    data = {
        "state": "User requested refund for duplicate billing.",
        "model": "laya",
        "questions": {
            "urgent": {
                "type": "noul",
                "instructions": "Is this urgent?",
                "criteria": {"true": "Urgent", "false": "Not urgent"},
            },
            "dept": {
                "type": "choice",
                "instructions": "Which dept?",
                "criteria": {"billing": "Billing", "support": "Support"},
            },
            "sentiment": {
                "type": "score",
                "instructions": "Rate sentiment",
                "criteria": ["Negative", "Neutral", "Positive"],
            },
        },
    }
    req = SystemOneRequest.model_validate(data)
    assert req.state == "User requested refund for duplicate billing."
    assert req.model == "laya"
    assert len(req.questions) == 3


def test_score_requires_at_least_two_levels():
    with pytest.raises(ValidationError):
        ScoreQuestion(
            type="score",
            instructions="Invalid score",
            criteria=["Only One"],
        )


def test_valid_response_schema():
    resp_data = {
        "model": "laya",
        "answers": {
            "urgent": {"type": "noul", "noul": 0.85},
            "dept": {
                "type": "choice",
                "choice": "billing",
                "probabilities": {"billing": 0.9, "support": 0.1},
                "confidence": 0.88,
            },
            "sentiment": {
                "type": "score",
                "score": 1.2,
                "legend": {"0": "Negative", "1": "Neutral", "2": "Positive"},
                "probabilities": {"0": 0.1, "1": 0.7, "2": 0.2},
                "confidence": 0.75,
            },
        },
        "usage": {"input_tokens": 100, "output_tokens": 15},
    }
    resp = SystemOneResponse.model_validate(resp_data)
    assert resp.model == "laya"
    assert resp.answers["urgent"].type == "noul"
```

- [ ] **Step 4: Update tests/test_adapter.py**

Update imports to `from app.dto import ...` and `from app.services.laya_service import ...`:

```python
from app.dto import (
    ChoiceQuestion,
    NoulQuestion,
    ScoreQuestion,
    SystemOneResponse,
)
from app.services.laya_service import estimate_usage, format_jev_response


def test_format_jev_response_mapping():
    questions = {
        "q_noul": NoulQuestion(instructions="Is this a bug?"),
        "q_choice": ChoiceQuestion(
            instructions="Category?",
            criteria={"billing": "Billing", "tech": "Tech"},
        ),
        "q_score": ScoreQuestion(
            instructions="Severity",
            criteria=["Low", "Medium", "High"],
        ),
    }
    laya_answers = {
        "q_noul": {"noul": 0.88},
        "q_choice": {
            "choice": "billing",
            "probabilities": {"billing": 0.85, "tech": 0.15},
            "confidence": 0.82,
        },
        "q_score": {
            "score": 1.4,
            "probabilities": {"0": 0.1, "1": 0.8, "2": 0.1},
            "confidence": 0.79,
        },
    }

    res = format_jev_response(
        model_name="laya",
        laya_answers=laya_answers,
        questions=questions,
        state="I found a billing bug.",
    )

    assert isinstance(res, SystemOneResponse)
    assert res.model == "laya"
    assert res.answers["q_noul"].type == "noul"
    assert res.answers["q_noul"].noul == 0.88
    assert res.answers["q_choice"].type == "choice"
    assert res.answers["q_choice"].choice == "billing"
    assert res.answers["q_score"].type == "score"
    assert res.answers["q_score"].legend == {"0": "Low", "1": "Medium", "2": "High"}
    assert res.usage.input_tokens > 0


def test_estimate_usage():
    questions = {"q1": NoulQuestion(instructions="Test?")}
    usage = estimate_usage("Short text state", questions)
    assert usage.input_tokens > 0
    assert usage.output_tokens > 0


def test_format_jev_response_defaults_and_edge_cases():
    questions = {
        "q_noul_scalar": NoulQuestion(instructions="Bug?"),
        "q_noul_empty": NoulQuestion(instructions="Empty?"),
        "q_choice_empty": ChoiceQuestion(instructions="Pick", criteria={"a": "A"}),
        "q_score_empty": ScoreQuestion(instructions="Rate", criteria=["One", "Two"]),
    }
    laya_answers = {
        "q_noul_scalar": 0.75,
    }

    res = format_jev_response(
        model_name="laya",
        laya_answers=laya_answers,
        questions=questions,
        state={"key": "value"},
    )

    assert res.answers["q_noul_scalar"].noul == 0.75
    assert res.answers["q_noul_empty"].noul == 0.0
    assert res.answers["q_choice_empty"].choice == ""
    assert res.answers["q_score_empty"].score == 0.0
    assert res.answers["q_score_empty"].legend == {"0": "One", "1": "Two"}
    assert res.usage.input_tokens > 0


def test_format_jev_response_explicit_none():
    questions = {
        "q_noul": NoulQuestion(instructions="Bug?"),
        "q_choice": ChoiceQuestion(instructions="Pick", criteria={"a": "A"}),
        "q_score": ScoreQuestion(instructions="Rate", criteria=["One", "Two"]),
    }
    laya_answers = {
        "q_noul": {"noul": None},
        "q_choice": {"choice": None, "probabilities": None, "confidence": None},
        "q_score": {"score": None, "probabilities": None, "confidence": None},
    }
    res = format_jev_response(
        model_name="laya",
        laya_answers=laya_answers,
        questions=questions,
        state="test",
    )
    assert res.answers["q_noul"].noul == 0.0
    assert res.answers["q_choice"].choice == ""
    assert res.answers["q_choice"].confidence == 1.0
    assert res.answers["q_score"].score == 0.0
    assert res.answers["q_score"].confidence == 0.5
```

---

### Task 7: Verification & Cleanup

**Files:**
- Delete: `src/` directory
- Modify: `README.md`

- [ ] **Step 1: Run all tests via uv**

Run: `uv run pytest`
Expected: All tests pass.

- [ ] **Step 2: Remove legacy src/ directory**

Run: `Remove-Item -Recurse -Force src`

- [ ] **Step 3: Update README.md**

Document the new directory structure, running instructions (`fastapi run app/main.py`), and environment configuration.

- [ ] **Step 4: Final verification test run**

Run: `uv run pytest`
Expected: All tests pass cleanly without `src/`.
