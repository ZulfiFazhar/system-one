from typing import Any, Protocol


class BaseModelAdapter(Protocol):
    name: str

    def load(self) -> None: ...

    def predict(self, state: Any, questions: dict[str, Any]) -> dict[str, Any]: ...

    def unload(self) -> None: ...
