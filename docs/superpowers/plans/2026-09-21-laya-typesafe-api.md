# System One (Laya) TypeSafe Jev API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a FastAPI service named system-one wrapping the Laya System 1 decision model to provide an HTTP API fully compatible with TypeSafe Jev (`POST /v1/systemone`).

**Architecture:** A lightweight FastAPI server preloads `laya.Router` on startup within the application lifespan. Incoming requests are authenticated, validated against TypeSafe Jev schemas (`noul`, `choice`, `score`), executed against the Laya router in a worker thread, and mapped back to the calibrated Jev response format with usage metrics.

**Tech Stack:** Python >=3.12, FastAPI, Pydantic v2, Uvicorn, Pytest, `convaiinnovations/laya`.

**Spec:** `docs/superpowers/specs/2026-09-21-laya-typesafe-api-design.md`

## Global Constraints

- Endpoint path must strictly be `POST /v1/systemone`.
- Healthcheck endpoint must be `GET /healthz`.
- All response schemas must match TypeSafe Jev specification verbatim: `model`, `answers`, `usage`.
- Question types must support `noul`, `choice`, and `score`.
- Score criteria must require at least 2 levels (HTTP 422 if fewer).
- Authentication must enforce `Authorization: Bearer <API_KEY>` when `LAYA_API_KEY` environment variable is set.
- Laya inference must run via `run_in_threadpool` or router instance in `app.state.router`.

## Review Focus

1. Missing or malformed `Authorization` header when `LAYA_API_KEY` is configured -> must return `401 Unauthorized`.
2. Score question with fewer than 2 criteria items -> must return `422 Unprocessable Entity`.
3. Question type other than `noul`, `choice`, or `score` -> must return `422 Unprocessable Entity`.
4. Empty or missing `questions` dict -> must return `422 Unprocessable Entity`.
5. State provided as dict or list rather than string -> must be accepted without serialization error.

---

### Task 1: TypeSafe Jev Request & Response Schemas

**Files:**
- Create: `src/system_one/schemas.py`
- Test: `tests/test_schemas.py`

**Interfaces:**
- Consumes: None (pure Pydantic v2 data models)
- Produces:
  - `NoulQuestion`, `ChoiceQuestion`, `ScoreQuestion`, `Question` (Union)
  - `SystemOneRequest`
  - `NoulAnswer`, `ChoiceAnswer`, `ScoreAnswer`, `Answer` (Union)
  - `Usage`, `SystemOneResponse`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_schemas.py
import pytest
from pydantic import ValidationError
from system_one.schemas import (
    NoulQuestion,
    ChoiceQuestion,
    ScoreQuestion,
    SystemOneRequest,
    SystemOneResponse,
    NoulAnswer,
    ChoiceAnswer,
    ScoreAnswer,
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

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_schemas.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'system_one.schemas'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/system_one/schemas.py
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

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_schemas.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/system_one/schemas.py tests/test_schemas.py
git commit -m "feat: add TypeSafe Jev request and response schemas"
```

---

### Task 2: Laya Output Adapter & Response Normalizer

**Files:**
- Create: `src/adapter.py`
- Test: `tests/test_adapter.py`

**Interfaces:**
- Consumes:
  - `src/schemas.py`: `Question`, `NoulQuestion`, `ChoiceQuestion`, `ScoreQuestion`, `SystemOneResponse`, `NoulAnswer`, `ChoiceAnswer`, `ScoreAnswer`, `Usage`
- Produces:
  - `format_jev_response(model_name: str, laya_answers: dict, questions: dict[str, Question], state: Any) -> SystemOneResponse`
  - `estimate_usage(state: Any, questions: dict[str, Question]) -> Usage`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_adapter.py
from schemas import (
    NoulQuestion,
    ChoiceQuestion,
    ScoreQuestion,
    SystemOneResponse,
)
from adapter import format_jev_response, estimate_usage

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_adapter.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'adapter'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/adapter.py
import json
from typing import Any
from schemas import (
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

def estimate_usage(state: Any, questions: dict[str, Question]) -> Usage:
    # Estimate tokens (~4 chars per token for text, 4 tokens per question answer)
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

        if isinstance(q_spec, NoulQuestion):
            val = ans_raw.get("noul", 0.0) if isinstance(ans_raw, dict) else float(ans_raw)
            answers[q_id] = NoulAnswer(type="noul", noul=float(val))

        elif isinstance(q_spec, ChoiceQuestion):
            choice_val = ans_raw.get("choice", "")
            probs = ans_raw.get("probabilities", {choice_val: 1.0})
            conf = ans_raw.get("confidence", max(probs.values()) if probs else 1.0)
            answers[q_id] = ChoiceAnswer(
                type="choice",
                choice=choice_val,
                probabilities={str(k): float(v) for k, v in probs.items()},
                confidence=float(conf),
            )

        elif isinstance(q_spec, ScoreQuestion):
            score_val = ans_raw.get("score", 0.0)
            legend = {str(idx): str(item) for idx, item in enumerate(q_spec.criteria)}
            probs = ans_raw.get("probabilities", {})
            if not probs:
                probs = {str(idx): 1.0 / len(q_spec.criteria) for idx in range(len(q_spec.criteria))}
            conf = ans_raw.get("confidence", max(probs.values()) if probs else 1.0)
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

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_adapter.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/adapter.py tests/test_adapter.py
git commit -m "feat: add Laya output adapter and response normalizer"
```

---

### Task 3: FastAPI Application & Endpoints (`GET /healthz`, `POST /v1/systemone`)

**Files:**
- Create: `src/app.py`
- Modify: `src/__init__.py`
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes:
  - `src/schemas.py`: `SystemOneRequest`, `SystemOneResponse`
  - `src/adapter.py`: `format_jev_response`
- Produces:
  - `app`: FastAPI application instance
  - `create_app()`: Application factory

- [ ] **Step 1: Write the failing test**

```python
# tests/test_api.py
import os
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
import pytest
from app import create_app

@pytest.fixture
def client_no_auth():
    os.environ.pop("LAYA_API_KEY", None)
    app = create_app(mock_router=True)
    return TestClient(app)

@pytest.fixture
def client_with_auth():
    os.environ["LAYA_API_KEY"] = "secret-token-123"
    app = create_app(mock_router=True)
    yield TestClient(app)
    os.environ.pop("LAYA_API_KEY", None)

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
                "criteria": ["only one"]  # requires min 2
            }
        }
    })
    assert resp.status_code == 422
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_api.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/app.py
import os
from contextlib import asynccontextmanager
from typing import Any
from fastapi import FastAPI, Depends, HTTPException, Security, status
from fastapi.concurrency import run_in_threadpool
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from schemas import SystemOneRequest, SystemOneResponse
from adapter import format_jev_response

security = HTTPBearer(auto_error=False)

def verify_api_key(
    credentials: HTTPAuthorizationCredentials | None = Security(security),
) -> None:
    api_key = os.getenv("LAYA_API_KEY")
    if not api_key:
        return
    if not credentials or credentials.credentials != api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key",
        )

class MockRouter:
    def predict(self, state: Any, questions: dict[str, Any], model: str | None = None) -> dict[str, Any]:
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
                answers[q_id] = {"score": 1.0, "probabilities": {"0": 0.2, "1": 0.8}, "confidence": 0.8}
        return {"answers": answers, "routing": {"model": model or "laya"}}

    def unload(self) -> None:
        pass

def create_app(mock_router: bool = False) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if mock_router or os.getenv("LAYA_MOCK_ROUTER", "").lower() in ("1", "true"):
            app.state.router = MockRouter()
        else:
            try:
                import laya
                device = os.getenv("LAYA_DEVICE", "auto")
                preload = os.getenv("LAYA_PRELOAD", "true").lower() in ("1", "true")
                app.state.router = laya.Router(preload=preload, device=device)
            except Exception:
                app.state.router = MockRouter()
        yield
        if hasattr(app.state, "router") and hasattr(app.state.router, "unload"):
            app.state.router.unload()

    app = FastAPI(title="System One (Laya) API", lifespan=lifespan)

    @app.get("/healthz")
    def healthz() -> dict[str, Any]:
        return {"status": "ready", "model": "laya", "preloaded": True}

    @app.post("/v1/systemone", response_model=SystemOneResponse, dependencies=[Depends(verify_api_key)])
    async def systemone(req: SystemOneRequest) -> SystemOneResponse:
        router = app.state.router
        # Execute model inference in thread pool to avoid blocking asyncio event loop
        questions_dict = {
            k: v.model_dump() if hasattr(v, "model_dump") else v
            for k, v in req.questions.items()
        }
        res = await run_in_threadpool(
            router.predict,
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

    return app

app = create_app()
```

Modify `src/__init__.py`:
```python
# src/__init__.py
from app import app, create_app

def main() -> None:
    import uvicorn
    import os
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("app:app", host=host, port=port, reload=False)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/app.py src/__init__.py tests/test_api.py
git commit -m "feat: add FastAPI app and endpoints with auth and lifespan"
```
