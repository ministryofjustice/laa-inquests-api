from enum import Enum
from typing import Annotated, Iterable

from fastapi import Depends, HTTPException, status

from app.ports.entra_auth_port import AuthenticatedUser
from app.routers.dependencies import verify_entra_token


class Permission(str, Enum):
    APPLICATION_CREATE = "application:create"
    APPLICATION_READ = "application:read"
    APPLICATION_MANAGE = "application:manage"
    APPLICATION_SEARCH = "application:search"

    CLAIM_CREATE = "claim:create"
    CLAIM_READ = "claim:read"
    CLAIM_MANAGE = "claim:manage"
    CLAIM_DELETE = "claim:delete"

    CASE_NOTE_CREATE = "case-note:create"
    HISTORY_READ = "history:read"

    CERTIFICATE_READ = "certificate:read"

    PROVIDER_OFFICES_READ = "provider-offices:read"

    REPORTS_MI_READ = "reports-mi:read"
    REPORTS_PAYMENT_READ = "reports-payment:read"
    REPORTS_APPLICATION_WORKFLOW_READ = "reports-application-workflow:read"
    REPORTS_CLAIM_WORKFLOW_READ = "reports-claim-workflow:read"


class Role(str, Enum):
    PROVIDER_APPLICATION_USER = "Inquests - Provider Application User"
    PROVIDER_CLAIMS_USER = "Inquests - Provider Claims User"
    APPLICATIONS_CASEWORKER = "Inquests - Applications caseworker"
    CLAIMS_CASEWORKER = "Inquests - Claims caseworker"
    CUSTOMER_SERVICE_AGENT = "Inquests - Customer service agent"
    ASSURANCE = "Inquests - Assurance"
    APPLICATION_WORKFLOW_REPORTING = "Inquests - Application workflow reporting"
    CLAIM_WORKFLOW_REPORTING = "Inquests - Claim workflow reporting"
    POLICY = "Inquests - Policy"
    FINANCE = "Inquests - Finance"


ROLE_PERMISSIONS_MAP: dict[Role, set[Permission]] = {
    Role.PROVIDER_APPLICATION_USER: {
        Permission.APPLICATION_CREATE,
        Permission.PROVIDER_OFFICES_READ,
    },
    Role.PROVIDER_CLAIMS_USER: {
        Permission.APPLICATION_SEARCH,
        Permission.CLAIM_CREATE,
        Permission.CLAIM_DELETE,
        Permission.PROVIDER_OFFICES_READ,
    },
    Role.APPLICATIONS_CASEWORKER: {
        Permission.APPLICATION_READ,
        Permission.APPLICATION_MANAGE,
        Permission.CERTIFICATE_READ,
        Permission.HISTORY_READ,
        Permission.CASE_NOTE_CREATE,
    },
    Role.CLAIMS_CASEWORKER: {
        Permission.APPLICATION_READ,
        Permission.CLAIM_READ,
        Permission.CLAIM_MANAGE,
        Permission.CERTIFICATE_READ,
        Permission.HISTORY_READ,
        Permission.CASE_NOTE_CREATE,
    },
    Role.CUSTOMER_SERVICE_AGENT: {
        Permission.APPLICATION_READ,
        Permission.CLAIM_READ,
        Permission.CERTIFICATE_READ,
        Permission.CASE_NOTE_CREATE,
        Permission.HISTORY_READ,
    },
    Role.ASSURANCE: {
        Permission.APPLICATION_READ,
        Permission.CLAIM_READ,
        Permission.CERTIFICATE_READ,
        Permission.CASE_NOTE_CREATE,
        Permission.HISTORY_READ,
        Permission.REPORTS_MI_READ,
        Permission.REPORTS_PAYMENT_READ,
    },
    Role.APPLICATION_WORKFLOW_REPORTING: {
        Permission.REPORTS_APPLICATION_WORKFLOW_READ,
    },
    Role.CLAIM_WORKFLOW_REPORTING: {
        Permission.REPORTS_CLAIM_WORKFLOW_READ,
    },
    Role.POLICY: {
        Permission.REPORTS_MI_READ,
    },
    Role.FINANCE: {
        Permission.REPORTS_MI_READ,
        Permission.REPORTS_PAYMENT_READ,
    },
}


def get_current_user_permissions(
    user: Annotated[AuthenticatedUser, Depends(verify_entra_token)],
) -> set[Permission]:
    permissions: set[Permission] = set()
    for role in user.app_roles:
        permissions.update(ROLE_PERMISSIONS_MAP.get(role, set()))
    return permissions


class PermissionChecker:
    def __init__(self, possible_permissions: Iterable[Permission] | Permission) -> None:
        if isinstance(possible_permissions, Permission):
            self.possible_permissions = [possible_permissions]
        else:
            self.possible_permissions = possible_permissions

    def __call__(
        self,
        permissions: Annotated[
            set[Permission],
            Depends(get_current_user_permissions),
        ],
    ) -> None:
        if not any(
            permission in permissions for permission in self.possible_permissions
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=("Forbidden: Missing required permission"),
            )


def require_permission_from(
    possible_permissions: Iterable[Permission] | Permission,
) -> PermissionChecker:
    return PermissionChecker(possible_permissions)
