"""Per-IP flood guard for the public scan endpoints (R7)."""

import logging
import math
from datetime import datetime, timezone

from fastapi import Depends, Request, status
from fastapi.responses import JSONResponse
from redis.exceptions import RedisError

from contracts import ScanRateLimited
from scan_orchestrator.api.dependencies import get_scan_rate_limit
from scan_orchestrator.domain.scan_rate_limit import ScanRateLimit, ScanRateLimitedError

logger = logging.getLogger(__name__)


async def enforce_scan_rate_limit(
    request: Request, limit: ScanRateLimit = Depends(get_scan_rate_limit)
) -> None:
    # The real client IP: uvicorn runs with --proxy-headers behind Caddy.
    ip = request.client.host if request.client else "unknown"
    try:
        await limit.check(ip)
    except RedisError:
        # Fail open: a broken flood guard must never cost anyone the verdict.
        logger.warning("scan rate limit skipped: store unavailable", exc_info=True)


async def scan_rate_limited_response(_: Request, exc: ScanRateLimitedError) -> JSONResponse:
    wait = exc.retry_at - datetime.now(timezone.utc)
    return JSONResponse(
        ScanRateLimited(retry_at=exc.retry_at).model_dump(mode="json"),
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        headers={"Retry-After": str(max(1, math.ceil(wait.total_seconds())))},
    )
