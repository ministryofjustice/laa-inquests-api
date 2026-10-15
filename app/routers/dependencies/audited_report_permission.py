import logging
from collections.abc import Callable, Generator, Iterable
from contextlib import contextmanager
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.rbac import Permission, PermissionChecker, get_current_user_permissions
from app.logging_utils import build_log_extra
from app.models.audit.enums import AuditType
from app.ports.entra_auth_port import EntraAuthPort
from app.routers.dependencies.audit_writer import (
    AuditWriter,
    get_audit_report_download_factory,
)
from app.routers.dependencies.entra_auth import get_entra_auth_port
from app.use_cases.audit_report_download import AuditReportDownloadUseCase

logger = logging.getLogger(__name__)
_http_bearer = HTTPBearer(auto_error=False)


class ReportAuditFailureHandler:
    def __init__(self, permission_checker: PermissionChecker) -> None:
        self.permission_checker = permission_checker

    @contextmanager
    def handle_failure(
        self, permissions: set[Permission], request: Request
    ) -> Generator[None, None, None]:
        try:
            yield
        except Exception as exc:
            failure = HTTPException(
                status_code=500, detail="Failed to audit report request"
            )
            try:
                self.permission_checker(permissions)
            except HTTPException as permission_denied:
                failure = permission_denied

            logger.error(
                "Report request audit failed",
                extra=build_log_extra(
                    event="report_download_audit_failed",
                    route=request.url.path,
                    method=request.method,
                    status_code=failure.status_code,
                    error_type=type(exc).__name__,
                ),
            )
            raise failure from exc


class AuditedReportPermission:
    def __init__(
        self,
        possible_permissions: Iterable[Permission] | Permission,
        report_type: AuditType,
    ) -> None:
        self.permission_checker = PermissionChecker(
            possible_permissions
            if isinstance(possible_permissions, Permission)
            else tuple(possible_permissions)
        )
        self.failure_handler = ReportAuditFailureHandler(self.permission_checker)
        self.audit_writer = AuditWriter(report_type=report_type)

    async def __call__(
        self,
        permissions: Annotated[set[Permission], Depends(get_current_user_permissions)],
        credentials: Annotated[
            HTTPAuthorizationCredentials | None, Depends(_http_bearer)
        ],
        entra_auth_port: Annotated[EntraAuthPort, Depends(get_entra_auth_port)],
        create_audit_use_case: Annotated[
            Callable[[], AuditReportDownloadUseCase],
            Depends(get_audit_report_download_factory),
        ],
        request: Request,
    ) -> None:
        # Attempt to write an audit event, otherwise handle_failure will manage any exceptions
        with self.failure_handler.handle_failure(permissions, request):
            if credentials is None:
                raise HTTPException(
                    status_code=401,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            user_email_address = await run_in_threadpool(
                entra_auth_port.get_email_address, credentials.credentials
            )
            await self.audit_writer(
                user_email_address=user_email_address,
                use_case=create_audit_use_case(),
                request=request,
            )
        self.permission_checker(permissions)


def require_audited_report_permission(
    possible_permissions: Iterable[Permission] | Permission,
    report_type: AuditType,
) -> AuditedReportPermission:
    """Audit every authenticated attempt, with permission denial taking precedence."""
    return AuditedReportPermission(
        possible_permissions=possible_permissions, report_type=report_type
    )
