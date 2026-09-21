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
