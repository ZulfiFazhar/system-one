# Task 3 Brief: DTO Module Implementation

**Files:**
- Create: `D:\Zulfi\Programming\FastAPI\system-one\app\dto\__init__.py`
- Create: `D:\Zulfi\Programming\FastAPI\system-one\app\dto\systemone_dto.py`

### Requirements
1. Create `app/dto/systemone_dto.py`:
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

2. Create `app/dto/__init__.py`:
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

3. Verification:
Run: `uv run python -c "from app.dto import SystemOneRequest, SystemOneResponse; print('dto ok')"`
Expected: Output `dto ok`.

4. Commit:
`git add app/dto && git commit -m "feat: implement app.dto systemone_dto and exports"`
