# Task 6 Brief: Refactor Tests to Target app/

**Files:**
- Create: `D:\Zulfi\Programming\FastAPI\system-one\tests\conftest.py`
- Modify: `D:\Zulfi\Programming\FastAPI\system-one\tests\test_api.py`
- Modify: `D:\Zulfi\Programming\FastAPI\system-one\tests\test_schemas.py`
- Modify: `D:\Zulfi\Programming\FastAPI\system-one\tests\test_adapter.py`

### Requirements
1. Create `tests/conftest.py`:
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

2. Update `tests/test_api.py`:
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

3. Update `tests/test_schemas.py`:
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

4. Update `tests/test_adapter.py`:
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

5. Verification:
Run: `uv run pytest`
Expected: All tests pass.

6. Commit:
`git add tests && git commit -m "test: update test suite to import from app package"`
