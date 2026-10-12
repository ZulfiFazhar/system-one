import logging
import time
from fastapi import Request, Response
from fastapi.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.db import record_request_log

logger = logging.getLogger(__name__)


class DashboardLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start_time = time.perf_counter()
        response = None
        try:
            response = await call_next(request)
            return response
        finally:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            status_code = response.status_code if response is not None else 500
            client_ip = request.client.host if request.client else "127.0.0.1"
            api_key_id = getattr(request.state, "api_key_id", None)
            usage = getattr(request.state, "usage", None)
            input_tokens = getattr(usage, "input_tokens", 0) if usage else 0
            output_tokens = getattr(usage, "output_tokens", 0) if usage else 0

            # Skip static assets
            if request.url.path.startswith("/public/"):
                pass
            else:
                # ponytail: run_in_threadpool offloads DB I/O from event loop; upgrade to batch queue if write volume exceeds SQLite WAL.
                try:
                    await run_in_threadpool(
                        record_request_log,
                        endpoint=request.url.path,
                        method=request.method,
                        status_code=status_code,
                        latency_ms=latency_ms,
                        ip_address=client_ip,
                        api_key_id=api_key_id,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                    )
                except Exception as exc:
                    logger.warning("Failed to record request log: %s", exc)
