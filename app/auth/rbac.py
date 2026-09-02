from enum import Enum
from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.ports.entra_auth_port import AuthenticatedUser
from app.routers.dependencies import verify_entra_token


class Permission(str, Enum):
    APPLICATION_READ = "application:read"
    APPLICATION_CREATE = "application:create"

    CLAIM_READ = "claim:read"
    CLAIM_CREATE = "claim:create"

    CORONERS_LETTER_UPLOAD = "coroners-letter:upload"


ROLE_PERMISSIONS_MAP: dict[str, set[Permission]] = {
    "Provider.ApplicationUser": {
        Permission.APPLICATION_READ,
        Permission.APPLICATION_CREATE,
        Permission.CORONERS_LETTER_UPLOAD,
    },
    "Provider.ClaimsUser": {
        Permission.CLAIM_READ,
        Permission.CLAIM_CREATE,
    },
}


def get_current_user_permissions(
    user: Annotated[AuthenticatedUser, Depends(verify_entra_token)],
) -> set[Permission]:
    permissions: set[Permission] = set()
    for role in user.scopes:
        permissions.update(ROLE_PERMISSIONS_MAP.get(role, set()))
    return permissions


def require_permission(required_permission: Permission):
    def permission_checker(
        permissions: Annotated[set[Permission], Depends(get_current_user_permissions)],
    ) -> None:
        if required_permission not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Missing required permission '{required_permission.value}'",
            )

    return permission_checker
