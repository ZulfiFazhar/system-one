import pytest
from pydantic import ValidationError
from schemas import (
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
