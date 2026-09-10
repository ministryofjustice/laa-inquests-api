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

    PROVIDER_OFFICES_READ = "provider-offices:read"


ROLE_PERMISSIONS_MAP: dict[str, set[Permission]] = {
    "Inquests - Provider Application User": {
        Permission.APPLICATION_CREATE,
        Permission.CORONERS_LETTER_UPLOAD,
        Permission.PROVIDER_OFFICES_READ,
    },
    "Inquests - Provider Claims User": {
        Permission.CLAIM_CREATE,
        Permission.PROVIDER_OFFICES_READ,
    },
}


def get_current_user_permissions(
    user: Annotated[AuthenticatedUser, Depends(verify_entra_token)],
) -> set[Permission]:
    permissions: set[Permission] = set()
    for role in user.app_roles:
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
