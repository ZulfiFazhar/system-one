import secrets
import sqlite3
import threading
import time
from collections import defaultdict
from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBasic,
    HTTPBasicCredentials,
    HTTPBearer,
)

from app.core.config import settings
from app.core import db

bearer_scheme = HTTPBearer(auto_error=False)
admin_basic_scheme = HTTPBasic(auto_error=False)

# ponytail: in-memory sliding window store works for single process; upgrade to Redis/Dragonfly for distributed horizontal scaling.
_RATE_LIMIT_STORE: dict[str, list[float]] = defaultdict(list)
_KEY_RATE_LIMIT_STORE: dict[int, list[float]] = defaultdict(list)
_RATE_LIMIT_LOCK = threading.Lock()

_BLOCKED_IPS: set[str] = set()
_CACHED_PUBLIC_RATE_LIMIT: int | None = None
_CACHED_PUBLIC_RATE_WINDOW: int | None = None


def reset_rate_limits() -> None:
    """Helper to reset rate limit records (e.g. for testing)."""
    global _CACHED_PUBLIC_RATE_LIMIT, _CACHED_PUBLIC_RATE_WINDOW, _BLOCKED_IPS
    with _RATE_LIMIT_LOCK:
        _RATE_LIMIT_STORE.clear()
        _KEY_RATE_LIMIT_STORE.clear()
        _BLOCKED_IPS = set()
        _CACHED_PUBLIC_RATE_LIMIT = None
        _CACHED_PUBLIC_RATE_WINDOW = None


def refresh_security_caches(db_path: str | None = None) -> None:
    """Refreshes in-memory blocked IPs and public rate limit settings from DB."""
    global _BLOCKED_IPS, _CACHED_PUBLIC_RATE_LIMIT, _CACHED_PUBLIC_RATE_WINDOW
    try:
        blocked = db.get_blocked_ips(db_path)
        _BLOCKED_IPS = {row["ip_address"] for row in blocked}
    except (sqlite3.OperationalError, sqlite3.DatabaseError, ValueError):
        _BLOCKED_IPS = set()

    try:
        sys_settings = db.get_system_settings(db_path)
        if "public_rate_limit_requests" in sys_settings:
            _CACHED_PUBLIC_RATE_LIMIT = int(sys_settings["public_rate_limit_requests"])
        if "public_rate_limit_window_seconds" in sys_settings:
            _CACHED_PUBLIC_RATE_WINDOW = int(sys_settings["public_rate_limit_window_seconds"])
    except (sqlite3.OperationalError, sqlite3.DatabaseError, ValueError):
        pass


def check_ip_blocklist(client_ip: str) -> None:
    if client_ip in _BLOCKED_IPS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: IP address is blocklisted",
        )


def check_key_rate_limit(key_id: int, limit: int, window: int = 60) -> None:
    now = time.time()
    with _RATE_LIMIT_LOCK:
        timestamps = _KEY_RATE_LIMIT_STORE[key_id]
        valid_timestamps = [ts for ts in timestamps if now - ts < window]
        _KEY_RATE_LIMIT_STORE[key_id] = valid_timestamps

        if len(valid_timestamps) >= limit:
            first_ts = valid_timestamps[0] if valid_timestamps else now
            retry_after = int(window - (now - first_ts)) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"API key rate limit exceeded ({limit} requests per {window}s). Retry after {retry_after}s.",
                headers={"Retry-After": str(max(1, retry_after))},
            )

        valid_timestamps.append(now)


def check_rate_limit(client_ip: str) -> None:
    if not settings.rate_limit_enabled:
        return

    now = time.time()
    limit = (
        _CACHED_PUBLIC_RATE_LIMIT
        if _CACHED_PUBLIC_RATE_LIMIT is not None
        else settings.rate_limit_requests
    )
    window = (
        _CACHED_PUBLIC_RATE_WINDOW
        if _CACHED_PUBLIC_RATE_WINDOW is not None
        else settings.rate_limit_window_seconds
    )

    with _RATE_LIMIT_LOCK:
        timestamps = _RATE_LIMIT_STORE[client_ip]
        valid_timestamps = [ts for ts in timestamps if now - ts < window]
        _RATE_LIMIT_STORE[client_ip] = valid_timestamps

        if len(valid_timestamps) >= limit:
            first_ts = valid_timestamps[0] if valid_timestamps else now
            retry_after = int(window - (now - first_ts)) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Public rate limit exceeded ({limit} requests per {window}s). Provide a valid API key for unlimited access, or retry after {retry_after}s.",
                headers={"Retry-After": str(max(1, retry_after))},
            )

        valid_timestamps.append(now)


def verify_admin_credentials(
    credentials: HTTPBasicCredentials | None = Depends(admin_basic_scheme),
) -> str:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin credentials required",
            headers={"WWW-Authenticate": "Basic"},
        )

    is_user_correct = secrets.compare_digest(credentials.username, settings.admin_username)
    is_pass_correct = secrets.compare_digest(credentials.password, settings.admin_password)

    if not (is_user_correct and is_pass_correct):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


def verify_api_key(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> None:
    client_ip = request.client.host if request.client else "127.0.0.1"
    check_ip_blocklist(client_ip)

    # If client provides Bearer token:
    if credentials and credentials.credentials:
        token = credentials.credentials
        h = db.hash_key(token)
        try:
            row = db.get_api_key_by_hash(h)
        except (sqlite3.OperationalError, sqlite3.DatabaseError):
            row = None

        if row is not None:
            if not row["is_active"]:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="API key has been revoked",
                )
            if hasattr(request, "state"):
                request.state.api_key_id = row["id"]
            if row["rate_limit"] is not None:
                check_key_rate_limit(row["id"], limit=row["rate_limit"], window=60)
            return

        has_server_key = bool(settings.laya_api_key and settings.laya_api_key.get_secret_value())
        if has_server_key:
            expected_key = settings.laya_api_key.get_secret_value()
            if secrets.compare_digest(token, expected_key):
                if hasattr(request, "state"):
                    request.state.api_key_id = None
                return

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    # No API key provided: public access, enforce IP rate limiting
    if hasattr(request, "state"):
        request.state.api_key_id = None
    check_rate_limit(client_ip)

