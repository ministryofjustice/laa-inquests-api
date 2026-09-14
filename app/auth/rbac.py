from enum import Enum
from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.ports.entra_auth_port import AuthenticatedUser
from app.routers.dependencies import verify_entra_token


class Permission(str, Enum):
    APPLICATION_READ = "application:read"
    APPLICATION_CREATE = "application:create"
    APPLICATION_SEARCH = "application:search"

    CLAIM_READ = "claim:read"
    CLAIM_CREATE = "claim:create"
    CLAIM_DELETE = "claim:delete"
    CLAIM_EVIDENCE_UPLOAD = "claim-evidence:upload"

    CORONERS_LETTER_UPLOAD = "coroners-letter:upload"
    CORONERS_LETTER_DELETE = "coroners-letter:delete"

    PROVIDER_OFFICES_READ = "provider-offices:read"


ROLE_PERMISSIONS_MAP: dict[str, set[Permission]] = {
    "Inquests - Provider Application User": {
        Permission.APPLICATION_CREATE,
        Permission.CORONERS_LETTER_UPLOAD,
        Permission.CORONERS_LETTER_DELETE,
        Permission.PROVIDER_OFFICES_READ,
    },
    "Inquests - Provider Claims User": {
        Permission.APPLICATION_SEARCH,
        Permission.CLAIM_CREATE,
        Permission.CLAIM_DELETE,
        Permission.CLAIM_EVIDENCE_UPLOAD,
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
