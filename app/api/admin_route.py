import math
import os
import time
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.core.config import settings
from app.core import db
from app.core.security import refresh_security_caches, verify_admin_credentials
from app.dto.admin_dto import (
    BlocklistActionResponseDTO,
    BlocklistCreateDTO,
    BlocklistItemDTO,
    DeleteResponseDTO,
    HealthDTO,
    HourlyBucketDTO,
    KeyActionResponseDTO,
    KeyActivityResponseDTO,
    KeyCreateDTO,
    KeyCreateResponseDTO,
    KeyResponseDTO,
    KeyUpdateDTO,
    LogsResponseDTO,
    OverviewDTO,
    SettingsUpdateDTO,
)

router = APIRouter(dependencies=[Depends(verify_admin_credentials)])
_MODULE_START_TIME = time.time()


def _get_memory_rss_mb() -> float:
    # ponytail: process RSS via ctypes/resource/psutil fallback covers Windows/Unix without mandatory heavy deps.
    try:
        import psutil
        return round(psutil.Process().memory_info().rss / (1024 * 1024), 2)
    except Exception:
        pass

    try:
        import ctypes
        from ctypes import wintypes

        class PMC(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        c = PMC()
        c.cb = ctypes.sizeof(PMC)
        fn = ctypes.windll.psapi.GetProcessMemoryInfo
        fn.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
        if fn(ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(c), c.cb):
            return round(c.WorkingSetSize / (1024 * 1024), 2)
    except Exception:
        pass

    try:
        import resource
        import sys

        rusage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return round(rusage / (1024 * 1024) if sys.platform == "darwin" else rusage / 1024, 2)
    except Exception:
        pass

    return 0.0


def _get_overview_hourly_buckets() -> list[HourlyBucketDTO]:
    now = time.time()
    cutoff_24h = now - (24 * 3600)
    conn = db.get_db_connection()
    try:
        rows_24h = conn.execute(
            """
            SELECT timestamp, input_tokens, output_tokens, status_code
            FROM request_logs
            WHERE timestamp >= ?
            """,
            (cutoff_24h,),
        ).fetchall()
    finally:
        conn.close()

    current_hour_epoch = int(now // 3600) * 3600
    buckets: list[dict] = []
    bucket_map: dict[int, dict] = {}
    for i in range(23, -1, -1):
        bucket_ts = current_hour_epoch - (i * 3600)
        hour_label = time.strftime("%Y-%m-%d %H:00", time.gmtime(bucket_ts))
        b = {
            "hour": hour_label,
            "timestamp": bucket_ts,
            "requests": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "errors": 0,
        }
        buckets.append(b)
        bucket_map[bucket_ts] = b

    for r in rows_24h:
        ts = r["timestamp"]
        bucket_ts = int(ts // 3600) * 3600
        if bucket_ts in bucket_map:
            b = bucket_map[bucket_ts]
            b["requests"] += 1
            b["input_tokens"] += r["input_tokens"] or 0
            b["output_tokens"] += r["output_tokens"] or 0
            if r["status_code"] >= 400:
                b["errors"] += 1

    return [HourlyBucketDTO(**b) for b in buckets]


@router.get("/overview", response_model=OverviewDTO)
def get_overview() -> OverviewDTO:
    metrics = db.get_overview_metrics()
    metrics["timeseries_24h"] = _get_overview_hourly_buckets()
    return OverviewDTO(**metrics)


@router.get("/health", response_model=HealthDTO)
def get_health(request: Request) -> HealthDTO:
    model_loaded = (
        hasattr(request.app.state, "router")
        and request.app.state.router is not None
    )
    start_time = getattr(request.app.state, "start_time", None) or _MODULE_START_TIME
    uptime = max(0.0, round(time.time() - start_time, 2))
    db_size = (
        os.path.getsize(settings.database_path)
        if os.path.exists(settings.database_path)
        else 0
    )

    return HealthDTO(
        model_loaded=model_loaded,
        model_id=settings.laya_model_id,
        device=settings.laya_device,
        memory_rss_mb=_get_memory_rss_mb(),
        uptime_seconds=uptime,
        database_size_bytes=db_size,
    )


@router.get("/keys", response_model=list[KeyResponseDTO])
def list_keys() -> list[KeyResponseDTO]:
    keys = db.list_api_keys()
    return [KeyResponseDTO(**k) for k in keys]


@router.post("/keys", response_model=KeyCreateResponseDTO, status_code=status.HTTP_201_CREATED)
def create_key(body: KeyCreateDTO) -> KeyCreateResponseDTO:
    key_id, raw_key, prefix = db.create_api_key(body.name, body.rate_limit)
    conn = db.get_db_connection()
    try:
        row = conn.execute(
            """
            SELECT id, key_prefix, name, rate_limit, is_active, created_at, last_used_at
            FROM api_keys WHERE id = ?
            """,
            (key_id,),
        ).fetchone()
        row_dict = dict(row)
        row_dict["raw_key"] = raw_key
        return KeyCreateResponseDTO(**row_dict)
    finally:
        conn.close()


@router.patch("/keys/{key_id}", response_model=KeyActionResponseDTO)
def patch_key(key_id: int, body: KeyUpdateDTO) -> KeyActionResponseDTO:
    fields = body.model_dump(exclude_unset=True)
    kwargs = {}
    if "is_active" in fields:
        kwargs["is_active"] = fields["is_active"]
    if "rate_limit" in fields:
        kwargs["rate_limit"] = fields["rate_limit"]

    updated = db.update_api_key(key_id, **kwargs)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )
    refresh_security_caches()
    return KeyActionResponseDTO(success=True, key_id=key_id)


@router.delete("/keys/{key_id}", response_model=DeleteResponseDTO)
def delete_key(key_id: int) -> DeleteResponseDTO:
    deleted = db.delete_api_key(key_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )
    refresh_security_caches()
    return DeleteResponseDTO(success=True)


@router.get("/keys/{key_id}/activity", response_model=KeyActivityResponseDTO)
def get_key_activity(key_id: int) -> KeyActivityResponseDTO:
    activity = db.get_key_activity(key_id)
    if activity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )
    return KeyActivityResponseDTO(**activity)


@router.get("/logs", response_model=LogsResponseDTO)
def get_logs(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=500),
    status_code: int | None = None,
    ip: str | None = None,
    api_key_id: int | None = None,
) -> LogsResponseDTO:
    items, total = db.get_request_logs(
        page=page,
        limit=limit,
        status_code=status_code,
        ip_address=ip,
        api_key_id=api_key_id,
    )
    pages = math.ceil(total / limit) if total > 0 else 0
    return LogsResponseDTO(
        items=items,
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )


@router.get("/settings", response_model=dict[str, str])
def get_settings() -> dict[str, str]:
    return db.get_system_settings()


@router.put("/settings", response_model=dict[str, str])
def update_settings(body: SettingsUpdateDTO) -> dict[str, str]:
    db.update_system_settings(
        {
            "public_rate_limit_requests": str(body.rate_limit_requests),
            "public_rate_limit_window_seconds": str(body.rate_limit_window_seconds),
        }
    )
    refresh_security_caches()
    return db.get_system_settings()


@router.get("/blocklist", response_model=list[BlocklistItemDTO])
def get_blocklist() -> list[BlocklistItemDTO]:
    blocked = db.get_blocked_ips()
    return [BlocklistItemDTO(**b) for b in blocked]


@router.post("/blocklist", response_model=BlocklistActionResponseDTO, status_code=status.HTTP_201_CREATED)
def add_blocked_ip(body: BlocklistCreateDTO) -> BlocklistActionResponseDTO:
    added = db.add_blocked_ip(body.ip_address, body.reason)
    if not added:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="IP address already blocked",
        )
    refresh_security_caches()
    return BlocklistActionResponseDTO(success=True, ip_address=body.ip_address)


@router.delete("/blocklist/{ip_address}", response_model=DeleteResponseDTO)
def remove_blocked_ip(ip_address: str) -> DeleteResponseDTO:
    removed = db.remove_blocked_ip(ip_address)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="IP address not found in blocklist",
        )
    refresh_security_caches()
    return DeleteResponseDTO(success=True)
