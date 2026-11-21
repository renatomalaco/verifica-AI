"""Roles of the research area: admins name them and choose what each one may do.

Error bodies carry codes; the front end words them."""

from collections.abc import Awaitable

from fastapi import APIRouter, Depends, HTTPException, status

from contracts import ResearchRoleInfo, SaveRoleRequest
from scan_orchestrator.api.dependencies import get_research_roles
from scan_orchestrator.api.research_guard import require_account_manager, require_same_origin
from scan_orchestrator.application.research_auth import role_info
from scan_orchestrator.application.research_roles import (
    ResearchRoles,
    RoleNameTakenError,
    UnknownRoleError,
)
from scan_orchestrator.domain.research_access import ProtectedRoleError, Role

router = APIRouter(
    prefix="/api/v1/auth/roles",
    dependencies=[Depends(require_same_origin), Depends(require_account_manager)],
)


@router.get("", response_model=list[ResearchRoleInfo])
async def list_roles(roles: ResearchRoles = Depends(get_research_roles)) -> list[ResearchRoleInfo]:
    return [role_info(role) for role in await roles.list()]


@router.post("", response_model=ResearchRoleInfo, status_code=status.HTTP_201_CREATED)
async def create_role(
    body: SaveRoleRequest, roles: ResearchRoles = Depends(get_research_roles)
) -> ResearchRoleInfo:
    return await _saved(roles.create(body.name, frozenset(body.permissions)))


@router.put("/{role_id}", response_model=ResearchRoleInfo)
async def update_role(
    role_id: str, body: SaveRoleRequest, roles: ResearchRoles = Depends(get_research_roles)
) -> ResearchRoleInfo:
    return await _saved(roles.update(role_id, body.name, frozenset(body.permissions)))


async def _saved(saving: Awaitable[Role]) -> ResearchRoleInfo:
    try:
        role = await saving
    except RoleNameTakenError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="role_name_taken")
    except ProtectedRoleError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="protected_role")
    except UnknownRoleError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="role_not_found")
    return role_info(role)
