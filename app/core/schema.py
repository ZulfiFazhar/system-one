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
