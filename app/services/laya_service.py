import json
from typing import Any
import tiktoken

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

_TIKTOKEN_ENCODER = None


def get_token_encoder():
    global _TIKTOKEN_ENCODER
    if _TIKTOKEN_ENCODER is None:
        try:
            _TIKTOKEN_ENCODER = tiktoken.get_encoding("cl100k_base")
        except Exception:
            _TIKTOKEN_ENCODER = None
    return _TIKTOKEN_ENCODER


def count_tokens(text: str) -> int:
    enc = get_token_encoder()
    if enc is not None:
        return len(enc.encode(text, disallowed_special=()))
    return max(1, len(text) // 4)


def estimate_usage(state: Any, questions: dict[str, Question]) -> Usage:
    state_str = state if isinstance(state, str) else json.dumps(state)
    q_parts: list[str] = []
    for q in questions.values():
        q_parts.append(str(q.instructions))
        if hasattr(q, "criteria") and q.criteria:
            if isinstance(q.criteria, (dict, list)):
                q_parts.append(json.dumps(q.criteria))
            else:
                q_parts.append(str(q.criteria))

    full_input = state_str + " " + " ".join(q_parts)
    in_tokens = max(1, count_tokens(full_input))
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
