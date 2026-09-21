import secrets
import time
from collections import defaultdict
from fastapi import HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

bearer_scheme = HTTPBearer(auto_error=False)

# In-memory sliding window store: ip -> list of timestamps
_RATE_LIMIT_STORE: dict[str, list[float]] = defaultdict(list)


def reset_rate_limits() -> None:
    """Helper to reset rate limit records (e.g. for testing)."""
    _RATE_LIMIT_STORE.clear()


def check_rate_limit(client_ip: str) -> None:
    if not settings.rate_limit_enabled:
        return

    now = time.time()
    window = settings.rate_limit_window_seconds
    limit = settings.rate_limit_requests

    timestamps = _RATE_LIMIT_STORE[client_ip]
    valid_timestamps = [ts for ts in timestamps if now - ts < window]
    _RATE_LIMIT_STORE[client_ip] = valid_timestamps

    if len(valid_timestamps) >= limit:
        retry_after = int(window - (now - valid_timestamps[0])) + 1
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Public rate limit exceeded ({limit} requests per {window}s). Provide a valid API key for unlimited access, or retry after {retry_after}s.",
            headers={"Retry-After": str(max(1, retry_after))},
        )

    valid_timestamps.append(now)


def verify_api_key(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> None:
    has_server_key = bool(settings.laya_api_key and settings.laya_api_key.get_secret_value())

    # If client provides Bearer token:
    if credentials and credentials.credentials:
        if has_server_key:
            expected_key = settings.laya_api_key.get_secret_value()
            if not secrets.compare_digest(credentials.credentials, expected_key):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid API key",
                )
            # Valid API key: authenticated, bypass rate limit
            return
        return

    # No API key provided: public access, enforce IP rate limiting
    client_ip = request.client.host if request.client else "127.0.0.1"
    check_rate_limit(client_ip)
