import hashlib
import os
import secrets
import sqlite3
import time

from app.core.config import settings


def get_db_connection(db_path: str | None = None) -> sqlite3.Connection:
    target_path = db_path if db_path is not None else settings.database_path
    if target_path != ":memory:":
        dirname = os.path.dirname(target_path)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
    conn = sqlite3.connect(target_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db(db_path: str | None = None) -> None:
    conn = get_db_connection(db_path)
    with conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_hash TEXT UNIQUE NOT NULL,
                key_prefix TEXT NOT NULL,
                name TEXT NOT NULL,
                rate_limit INTEGER DEFAULT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now')),
                last_used_at TEXT DEFAULT NULL
            );

            CREATE TABLE IF NOT EXISTS request_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                endpoint TEXT NOT NULL,
                method TEXT NOT NULL,
                status_code INTEGER NOT NULL,
                latency_ms REAL NOT NULL,
                ip_address TEXT NOT NULL,
                api_key_id INTEGER DEFAULT NULL REFERENCES api_keys(id) ON DELETE SET NULL,
                input_tokens INTEGER DEFAULT 0,
                output_tokens INTEGER DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON request_logs(timestamp DESC);
            CREATE INDEX IF NOT EXISTS idx_logs_status ON request_logs(status_code);
            CREATE INDEX IF NOT EXISTS idx_logs_ip ON request_logs(ip_address);
            CREATE INDEX IF NOT EXISTS idx_logs_key_timestamp ON request_logs(api_key_id, timestamp DESC);

            CREATE TABLE IF NOT EXISTS ip_blocklist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT UNIQUE NOT NULL,
                reason TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            INSERT OR IGNORE INTO system_settings (key, value) VALUES ('public_rate_limit_requests', '10');
            INSERT OR IGNORE INTO system_settings (key, value) VALUES ('public_rate_limit_window_seconds', '60');
            """
        )
    conn.close()


def hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def create_api_key(
    name: str, rate_limit: int | None = None, db_path: str | None = None
) -> tuple[int, str, str]:
    raw_key = f"sk_live_{secrets.token_hex(16)}"
    prefix = raw_key[:16]
    key_h = hash_key(raw_key)

    conn = get_db_connection(db_path)
    with conn:
        cur = conn.execute(
            """
            INSERT INTO api_keys (key_hash, key_prefix, name, rate_limit)
            VALUES (?, ?, ?, ?)
            """,
            (key_h, prefix, name, rate_limit),
        )
        key_id = cur.lastrowid
    conn.close()
    return key_id, raw_key, prefix


def list_api_keys(db_path: str | None = None) -> list[dict]:
    conn = get_db_connection(db_path)
    try:
        rows = conn.execute(
            """
            SELECT 
                k.id, k.key_prefix, k.name, k.rate_limit, k.is_active, k.created_at, k.last_used_at,
                COUNT(l.id) AS total_requests,
                COALESCE(SUM(l.input_tokens), 0) AS total_input_tokens,
                COALESCE(SUM(l.output_tokens), 0) AS total_output_tokens
            FROM api_keys k
            LEFT JOIN request_logs l ON k.id = l.api_key_id
            GROUP BY k.id
            ORDER BY k.id DESC
            """
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_api_key_by_hash(key_hash: str, db_path: str | None = None) -> dict | None:
    conn = get_db_connection(db_path)
    try:
        row = conn.execute(
            """
            SELECT id, key_hash, key_prefix, name, rate_limit, is_active, created_at, last_used_at
            FROM api_keys
            WHERE key_hash = ?
            """,
            (key_hash,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_api_key_by_id(key_id: int, db_path: str | None = None) -> dict | None:
    conn = get_db_connection(db_path)
    try:
        row = conn.execute(
            """
            SELECT id, key_prefix, name, rate_limit, is_active, created_at, last_used_at
            FROM api_keys
            WHERE id = ?
            """,
            (key_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


_UNSET = object()


def update_api_key(
    key_id: int,
    is_active: bool | None = None,
    rate_limit: int | None | object = _UNSET,
    db_path: str | None = None,
) -> bool:
    conn = get_db_connection(db_path)
    try:
        fields = []
        params = []
        if is_active is not None:
            fields.append("is_active = ?")
            params.append(1 if is_active else 0)
        if rate_limit is not _UNSET:
            fields.append("rate_limit = ?")
            params.append(rate_limit)

        if not fields:
            row = conn.execute("SELECT id FROM api_keys WHERE id = ?", (key_id,)).fetchone()
            return row is not None

        params.append(key_id)
        with conn:
            cur = conn.execute(
                f"UPDATE api_keys SET {', '.join(fields)} WHERE id = ?", params
            )
            return cur.rowcount > 0
    finally:
        conn.close()


def delete_api_key(key_id: int, db_path: str | None = None) -> bool:
    conn = get_db_connection(db_path)
    with conn:
        cur = conn.execute("DELETE FROM api_keys WHERE id = ?", (key_id,))
        rowcount = cur.rowcount
    conn.close()
    return rowcount > 0


def record_request_log(
    endpoint: str,
    method: str,
    status_code: int,
    latency_ms: float,
    ip_address: str,
    api_key_id: int | None = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    db_path: str | None = None,
) -> None:
    now = time.time()
    conn = get_db_connection(db_path)
    with conn:
        conn.execute(
            """
            INSERT INTO request_logs (
                timestamp, endpoint, method, status_code, latency_ms,
                ip_address, api_key_id, input_tokens, output_tokens
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                now,
                endpoint,
                method,
                status_code,
                latency_ms,
                ip_address,
                api_key_id,
                input_tokens,
                output_tokens,
            ),
        )
        if api_key_id is not None:
            conn.execute(
                "UPDATE api_keys SET last_used_at = datetime('now') WHERE id = ?",
                (api_key_id,),
            )
    conn.close()


def get_request_logs(
    page: int = 1,
    limit: int = 50,
    status_code: int | None = None,
    ip_address: str | None = None,
    api_key_id: int | None = None,
    db_path: str | None = None,
) -> tuple[list[dict], int]:
    conn = get_db_connection(db_path)
    where = []
    params = []
    if status_code is not None:
        where.append("status_code = ?")
        params.append(status_code)
    if ip_address is not None:
        where.append("ip_address = ?")
        params.append(ip_address)
    if api_key_id is not None:
        where.append("api_key_id = ?")
        params.append(api_key_id)

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    count_row = conn.execute(
        f"SELECT COUNT(*) FROM request_logs {where_sql}", params
    ).fetchone()
    total = count_row[0] if count_row else 0

    offset = max(0, (page - 1) * limit)
    query_params = list(params) + [limit, offset]
    rows = conn.execute(
        f"""
        SELECT id, timestamp, endpoint, method, status_code, latency_ms,
               ip_address, api_key_id, input_tokens, output_tokens
        FROM request_logs
        {where_sql}
        ORDER BY timestamp DESC
        LIMIT ? OFFSET ?
        """,
        query_params,
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows], total


def get_overview_metrics(db_path: str | None = None) -> dict:
    conn = get_db_connection(db_path)
    try:
        row = conn.execute(
            """
            SELECT
                COUNT(*) as total_requests,
                COALESCE(SUM(input_tokens), 0) as total_input_tokens,
                COALESCE(SUM(output_tokens), 0) as total_output_tokens,
                COALESCE(AVG(latency_ms), 0.0) as avg_latency_ms,
                COALESCE(SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END), 0) as error_count
            FROM request_logs
            """
        ).fetchone()

        total_requests = row["total_requests"] if row else 0
        total_input_tokens = row["total_input_tokens"] if row else 0
        total_output_tokens = row["total_output_tokens"] if row else 0
        avg_latency_ms = round(float(row["avg_latency_ms"]), 2) if row else 0.0
        error_count = row["error_count"] if row else 0
        error_rate_pct = (
            round((error_count / total_requests) * 100.0, 2) if total_requests > 0 else 0.0
        )

        active_keys_row = conn.execute(
            "SELECT COUNT(*) FROM api_keys WHERE is_active = 1"
        ).fetchone()
        active_keys = active_keys_row[0] if active_keys_row else 0

        blocked_row = conn.execute("SELECT COUNT(*) FROM ip_blocklist").fetchone()
        blocked_ips_count = blocked_row[0] if blocked_row else 0

        return {
            "total_requests": total_requests,
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "avg_latency_ms": avg_latency_ms,
            "error_rate_pct": error_rate_pct,
            "active_keys": active_keys,
            "blocked_ips_count": blocked_ips_count,
        }
    finally:
        conn.close()


def get_overview_hourly_buckets(db_path: str | None = None) -> list[dict]:
    now = time.time()
    cutoff_24h = now - (24 * 3600)
    conn = get_db_connection(db_path)
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

    return buckets


def get_key_activity(key_id: int, db_path: str | None = None) -> dict | None:
    conn = get_db_connection(db_path)
    try:
        key_row = conn.execute(
            "SELECT id, name, key_prefix, is_active FROM api_keys WHERE id = ?", (key_id,)
        ).fetchone()
        if not key_row:
            return None

        row = conn.execute(
            """
            SELECT
                COUNT(*) as total_requests,
                COALESCE(SUM(input_tokens), 0) as total_input_tokens,
                COALESCE(SUM(output_tokens), 0) as total_output_tokens,
                COALESCE(AVG(latency_ms), 0.0) as avg_latency_ms,
                COALESCE(SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END), 0) as error_count
            FROM request_logs
            WHERE api_key_id = ?
            """,
            (key_id,),
        ).fetchone()

        total_requests = row["total_requests"] if row else 0
        total_input_tokens = row["total_input_tokens"] if row else 0
        total_output_tokens = row["total_output_tokens"] if row else 0
        avg_latency_ms = round(float(row["avg_latency_ms"]), 2) if row else 0.0
        error_count = row["error_count"] if row else 0
        error_rate_pct = (
            round((error_count / total_requests) * 100.0, 2) if total_requests > 0 else 0.0
        )

        now = time.time()
        cutoff_24h = now - (24 * 3600)
        rows_24h = conn.execute(
            """
            SELECT timestamp, input_tokens, output_tokens, status_code
            FROM request_logs
            WHERE api_key_id = ? AND timestamp >= ?
            """,
            (key_id, cutoff_24h),
        ).fetchall()

        recent_rows = conn.execute(
            """
            SELECT id, timestamp, endpoint, method, status_code, latency_ms,
                   ip_address, api_key_id, input_tokens, output_tokens
            FROM request_logs
            WHERE api_key_id = ?
            ORDER BY timestamp DESC
            LIMIT 50
            """,
            (key_id,),
        ).fetchall()

        # ponytail: in-memory 24h hourly bucketing handles single-node scale; upgrade to TimescaleDB or ClickHouse if logs exceed millions/day.
        current_hour_epoch = int(now // 3600) * 3600
        buckets = []
        bucket_map = {}
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

        return {
            "key_id": key_row["id"],
            "name": key_row["name"],
            "key_prefix": key_row["key_prefix"],
            "is_active": bool(key_row["is_active"]),
            "total_requests": total_requests,
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "avg_latency_ms": avg_latency_ms,
            "error_rate_pct": error_rate_pct,
            "timeseries_24h": buckets,
            "recent_logs": [dict(r) for r in recent_rows],
        }
    finally:
        conn.close()


def get_system_settings(db_path: str | None = None) -> dict[str, str]:
    conn = get_db_connection(db_path)
    rows = conn.execute("SELECT key, value FROM system_settings").fetchall()
    conn.close()
    return {r["key"]: r["value"] for r in rows}


def update_system_settings(
    settings_dict: dict[str, str], db_path: str | None = None
) -> None:
    conn = get_db_connection(db_path)
    with conn:
        for k, v in settings_dict.items():
            conn.execute(
                """
                INSERT INTO system_settings (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (str(k), str(v)),
            )
    conn.close()


def get_blocked_ips(db_path: str | None = None) -> list[dict]:
    conn = get_db_connection(db_path)
    rows = conn.execute(
        "SELECT id, ip_address, reason, created_at FROM ip_blocklist ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_blocked_ip(
    ip_address: str, reason: str = "", db_path: str | None = None
) -> bool:
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute(
                "INSERT INTO ip_blocklist (ip_address, reason) VALUES (?, ?)",
                (ip_address, reason),
            )
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False


def remove_blocked_ip(ip_address: str, db_path: str | None = None) -> bool:
    conn = get_db_connection(db_path)
    with conn:
        cur = conn.execute(
            "DELETE FROM ip_blocklist WHERE ip_address = ?", (ip_address,)
        )
        rowcount = cur.rowcount
    conn.close()
    return rowcount > 0


def prune_old_logs(days: int = 30, db_path: str | None = None) -> int:
    conn = get_db_connection(db_path)
    cutoff = time.time() - (days * 86400)
    with conn:
        cur = conn.execute("DELETE FROM request_logs WHERE timestamp < ?", (cutoff,))
        rowcount = cur.rowcount
    conn.close()
    return rowcount
