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
