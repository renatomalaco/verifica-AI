import base64
from typing import AsyncIterator
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import ValidationError
from starlette.datastructures import UploadFile
from sse_starlette.sse import EventSourceResponse

from contracts import ExplainResponse, ExplainScanRequest, Locale, QuotaExceeded, ScanRequest, ScanResponse, StageEvent
from contracts.telemetry import LatencyTracker, TraceContextMiddleware
from scan_orchestrator.api.dependencies import (
    get_analyze_text_use_case,
    get_device_secret,
    get_explain_use_case,
    get_settings,
)
from scan_orchestrator.application.analyze_text import AnalyzeTextUseCase
from scan_orchestrator.application.explain_scan import (
    ExplainScanUseCase,
    ExplanationUnavailableError,
    ScanNotFoundError,
)
from scan_orchestrator.domain.device_token import issue_device_token, verify_device_token
from scan_orchestrator.domain.quota import QuotaExceededError
from scan_orchestrator.domain.scan_input import ScanInput
from scan_orchestrator.settings import Settings

app = FastAPI(title="scan-orchestrator", version="0.1.0")

latency_tracker = LatencyTracker()
app.add_middleware(TraceContextMiddleware, tracker=latency_tracker)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEVICE_COOKIE = "va_device"
DEVICE_COOKIE_MAX_AGE = 365 * 24 * 3600


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics() -> str:
    """Metrics endpoint for Prometheus scraping and P50/P95/P99 computation."""
    return latency_tracker.generate_prometheus_metrics()


@app.get("/health")
async def health():
    return {"status": "ok", "service": "scan-orchestrator"}


def _to_scan_input(request: ScanRequest) -> ScanInput:
    try:
        return ScanInput(content=request.content, image_b64=request.image_b64)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@app.post("/api/v1/scans", response_model=ScanResponse)
async def scan(
    request: ScanRequest,
    use_case: AnalyzeTextUseCase = Depends(get_analyze_text_use_case),
):
    scan_input = _to_scan_input(request)

    response: ScanResponse | None = None
    async for event in use_case.execute(scan_input):
        if isinstance(event, ScanResponse):
            response = event

    if response is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process the scan stream.",
        )

    return response


MAX_UPLOAD_BYTES = 8 * 1024 * 1024  # same limit the image-extractor enforces
FORM_TYPES = ("multipart/form-data", "application/x-www-form-urlencoded")


async def read_scan_request(request: Request) -> ScanRequest:
    """JSON from the web app, or multipart when a phone shares a screenshot as a file (Share Target)."""
    content_type = request.headers.get("content-type", "")
    if not content_type.startswith(FORM_TYPES):
        return _validated(await _json_body(request))
    form = await request.form()
    upload = form.get("image")
    image_b64 = None
    if isinstance(upload, UploadFile):
        raw = await upload.read(MAX_UPLOAD_BYTES + 1)
        if len(raw) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="Image exceeds 8MB.")
        image_b64 = base64.b64encode(raw).decode("ascii")
    return _validated({"content": str(form.get("content") or ""), "image_b64": image_b64})


async def _json_body(request: Request) -> object:
    try:
        return await request.json()
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Body must be JSON or a form.")


def _validated(payload: object) -> ScanRequest:
    try:
        return ScanRequest.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=exc.errors(include_input=False, include_context=False))


@app.post("/api/v1/scans/stream")
async def scan_stream(
    request: ScanRequest = Depends(read_scan_request),
    use_case: AnalyzeTextUseCase = Depends(get_analyze_text_use_case),
):
    scan_input = _to_scan_input(request)

    async def event_generator() -> AsyncIterator[dict]:
        async for item in use_case.execute(scan_input):
            if isinstance(item, StageEvent):
                yield {"event": "stage", "data": item.model_dump_json()}
            elif isinstance(item, ScanResponse):
                yield {"event": "verdict", "data": item.model_dump_json()}

    return EventSourceResponse(event_generator())


# --- "Me explica" with per-device quota (R5b) ---

async def _explain_response(
    use_case: ExplainScanUseCase, scan_id: UUID, device_id: str, ip: str, locale: Locale
) -> JSONResponse:
    try:
        result = await use_case.execute(scan_id, device_id=device_id, ip=ip, locale=locale)
    except ScanNotFoundError:
        return JSONResponse({"detail": "Scan not found."}, status_code=status.HTTP_404_NOT_FOUND)
    except QuotaExceededError as exc:
        return JSONResponse(
            QuotaExceeded(retry_at=exc.retry_at).model_dump(mode="json"),
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )
    except ExplanationUnavailableError:
        return JSONResponse(
            {"detail": "Explanation unavailable right now."},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return JSONResponse(result.model_dump(mode="json"))


def _set_device_cookie(response: JSONResponse, token: str, secure: bool) -> None:
    response.set_cookie(
        DEVICE_COOKIE,
        token,
        max_age=DEVICE_COOKIE_MAX_AGE,
        path="/api",
        httponly=True,
        secure=secure,
        samesite="lax",
    )


@app.post(
    "/api/v1/scans/{scan_id}/explain",
    response_model=ExplainResponse,
    responses={404: {"description": "Scan not found"}, 429: {"model": QuotaExceeded}},
)
async def explain_scan(
    scan_id: UUID,
    request: Request,
    body: ExplainScanRequest | None = None,
    settings: Settings = Depends(get_settings),
    secret: bytes = Depends(get_device_secret),
    use_case: ExplainScanUseCase = Depends(get_explain_use_case),
) -> JSONResponse:
    device_id = verify_device_token(request.cookies.get(DEVICE_COOKIE), secret)
    new_token: str | None = None
    if device_id is None:
        device_id, new_token = issue_device_token(secret)

    ip = request.client.host if request.client else "unknown"
    locale = (body or ExplainScanRequest()).locale
    response = await _explain_response(use_case, scan_id, device_id, ip, locale)

    if new_token is not None:
        _set_device_cookie(response, new_token, secure=settings.DEVICE_COOKIE_SECURE)
    return response
