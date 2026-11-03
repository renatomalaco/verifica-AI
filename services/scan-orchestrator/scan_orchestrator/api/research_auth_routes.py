"""Sign-in endpoints of the research area (R5a). Error bodies carry codes; the front end words them."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse

from contracts import AcceptInviteRequest, LoginRequest, ResearchUser
from scan_orchestrator.api.dependencies import get_research_auth, get_settings
from scan_orchestrator.api.research_guard import (
    ACCESS_COOKIE,
    REFRESH_COOKIE,
    current_principal,
    require_same_origin,
)
from scan_orchestrator.application.research_auth import (
    REFRESH_TTL,
    InvalidCredentialsError,
    InviteInvalidError,
    ResearchAuth,
    SessionRejectedError,
    SignedIn,
)
from scan_orchestrator.domain.research_access import Account, Principal, TooManyAttemptsError, WeakPasswordError
from scan_orchestrator.infrastructure.access_tokens import ACCESS_TOKEN_TTL
from scan_orchestrator.settings import Settings

REFRESH_PATH = "/api/v1/auth/refresh"

router = APIRouter(prefix="/api/v1/auth", dependencies=[Depends(require_same_origin)])


def _user(account: Account) -> ResearchUser:
    return ResearchUser(email=account.email, role=account.role, expires_at=account.expires_at)


def _signed_in_response(signed_in: SignedIn, settings: Settings) -> JSONResponse:
    response = JSONResponse(_user(signed_in.account).model_dump(mode="json"))
    cookie = {"httponly": True, "secure": settings.AUTH_COOKIE_SECURE, "samesite": "strict"}
    response.set_cookie(
        ACCESS_COOKIE, signed_in.access_token, max_age=int(ACCESS_TOKEN_TTL.total_seconds()), path="/", **cookie
    )
    # The refresh token only travels to the refresh endpoint, never to the rest of the API.
    response.set_cookie(
        REFRESH_COOKIE, signed_in.refresh_token, max_age=int(REFRESH_TTL.total_seconds()), path=REFRESH_PATH, **cookie
    )
    return response


def _clear_cookies(response: Response, settings: Settings) -> None:
    cookie = {"httponly": True, "secure": settings.AUTH_COOKIE_SECURE, "samesite": "strict"}
    response.delete_cookie(ACCESS_COOKIE, path="/", **cookie)
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_PATH, **cookie)


@router.post("/login", response_model=ResearchUser)
async def login(
    body: LoginRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
    auth: ResearchAuth = Depends(get_research_auth),
) -> JSONResponse:
    ip = request.client.host if request.client else "unknown"
    try:
        signed_in = await auth.login(body.email, body.password, ip=ip)
    except TooManyAttemptsError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="too_many_attempts",
            headers={"Retry-After": str(exc.retry_after_seconds)},
        )
    except InvalidCredentialsError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_credentials")
    return _signed_in_response(signed_in, settings)


@router.post("/refresh", response_model=ResearchUser)
async def refresh(
    request: Request,
    settings: Settings = Depends(get_settings),
    auth: ResearchAuth = Depends(get_research_auth),
) -> JSONResponse:
    try:
        signed_in = await auth.refresh(request.cookies.get(REFRESH_COOKIE, ""))
    except SessionRejectedError:
        response = JSONResponse({"detail": "session_expired"}, status_code=status.HTTP_401_UNAUTHORIZED)
        _clear_cookies(response, settings)
        return response
    return _signed_in_response(signed_in, settings)


@router.delete("/refresh", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    settings: Settings = Depends(get_settings),
    auth: ResearchAuth = Depends(get_research_auth),
) -> Response:
    await auth.logout(request.cookies.get(REFRESH_COOKIE, ""))
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    _clear_cookies(response, settings)
    return response


@router.get("/me", response_model=ResearchUser)
async def me(
    principal: Principal = Depends(current_principal),
    auth: ResearchAuth = Depends(get_research_auth),
) -> ResearchUser:
    account = await auth.current_account(principal.account_id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not_signed_in")
    return _user(account)


@router.post("/invites/accept", status_code=status.HTTP_204_NO_CONTENT)
async def accept_invite(body: AcceptInviteRequest, auth: ResearchAuth = Depends(get_research_auth)) -> Response:
    try:
        await auth.accept_invite(body.token, body.password)
    except InviteInvalidError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invite_invalid")
    except WeakPasswordError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="password_too_short")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
