"""FastAPI guards for the research area.

The research-runner imports them too, with only the public key."""

from fastapi import Depends, HTTPException, Request, status

from scan_orchestrator.api.dependencies import get_access_verifier, get_settings
from contracts import ResearchPermission
from scan_orchestrator.domain.research_access import Principal
from scan_orchestrator.infrastructure.access_tokens import AccessTokenVerifier
from scan_orchestrator.settings import Settings

ACCESS_COOKIE = "va_access"
REFRESH_COOKIE = "va_refresh"
SAFE_METHODS = ("GET", "HEAD", "OPTIONS")


def require_same_origin(request: Request, settings: Settings = Depends(get_settings)) -> None:
    """CSRF defence on top of SameSite=Strict: state-changing calls must come from the app
    itself."""
    if request.method in SAFE_METHODS:
        return
    if request.headers.get("origin") not in settings.AUTH_ALLOWED_ORIGINS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="origin_not_allowed")


def current_principal(
    request: Request, verifier: AccessTokenVerifier = Depends(get_access_verifier)
) -> Principal:
    principal = verifier.verify(request.cookies.get(ACCESS_COOKIE))
    if principal is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not_signed_in")
    return principal


def require_research_reader(principal: Principal = Depends(current_principal)) -> Principal:
    if not principal.can(ResearchPermission.VIEW_STUDY):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not_allowed")
    return principal


def optional_principal(
    request: Request, verifier: AccessTokenVerifier = Depends(get_access_verifier)
) -> Principal | None:
    """Public routes: a signed-in account may get more, an anonymous visitor still works."""
    return verifier.verify(request.cookies.get(ACCESS_COOKIE))


def require_study_runner(
    principal: Principal = Depends(current_principal), _: None = Depends(require_same_origin)
) -> Principal:
    if not principal.can(ResearchPermission.RUN_STUDY):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin_only")
    return principal


def require_account_manager(principal: Principal = Depends(current_principal)) -> Principal:
    if not principal.can(ResearchPermission.MANAGE_ACCESS):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin_only")
    return principal
