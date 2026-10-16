import logging
from collections.abc import Generator, Iterable
from contextlib import contextmanager
from typing import Annotated, Any, Protocol

from fastapi import Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from app.adapters.audit_repository_adapter import AuditRepositoryAdapter
from app.auth.rbac import Permission, PermissionChecker, get_current_user_permissions
from app.db import get_session
from app.logging_utils import build_log_extra
from app.ports.audit_port import AuditPort
from app.ports.entra_auth_port import EntraAuthPort
from app.routers.dependencies.entra_auth import get_entra_auth_port

logger = logging.getLogger(__name__)
_http_bearer = HTTPBearer(auto_error=False)


class AuditUseCase(Protocol):
    def __init__(self, audit_port: AuditPort) -> None: ...


class AuditWriter(Protocol):
    """Maps the request onto the arguments of one kind of audit use case."""

    async def __call__(
        self, user_email_address: str, use_case: Any, request: Request
    ) -> None: ...


class ReportAuditFailureHandler:
    """Translates any audit failure into the HTTP error the caller should see."""

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
            # Users without permission get a 403 so a broken audit never reveals the report exists.
            try:
                self.permission_checker(permissions)
            except HTTPException as permission_denied:
                failure = permission_denied

            logger.error(
                "Report request audit failed",
                extra=build_log_extra(
                    event="report_audit_failed",
                    route=request.url.path,
                    method=request.method,
                    status_code=failure.status_code,
                    error_type=type(exc).__name__,
                ),
            )
            raise failure from exc


class ReportAuditerPermissionChecker:
    """Route dependency that audits a request, then enforces permission.

    The audit is written for every authenticated request, including those that
    are denied. A failed audit blocks the request in all cases. The audit event
    type is decided by the use case and writer the route passes in.
    """

    def __init__(
        self,
        possible_permissions: Iterable[Permission] | Permission,
        audit_use_case_type: type[AuditUseCase],
        audit_writer: AuditWriter,
    ) -> None:
        self.permission_checker = PermissionChecker(
            possible_permissions
            if isinstance(possible_permissions, Permission)
            else tuple(possible_permissions)
        )
        self.failure_handler = ReportAuditFailureHandler(self.permission_checker)
        self.audit_use_case_type = audit_use_case_type
        self.audit_writer = audit_writer

    async def __call__(
        self,
        permissions: Annotated[set[Permission], Depends(get_current_user_permissions)],
        credentials: Annotated[
            HTTPAuthorizationCredentials | None, Depends(_http_bearer)
        ],
        entra_auth_port: Annotated[EntraAuthPort, Depends(get_entra_auth_port)],
        session: Annotated[Session, Depends(get_session)],
        request: Request,
    ) -> None:
        with self.failure_handler.handle_failure(permissions, request):
            if credentials is None:
                raise HTTPException(
                    status_code=401,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            user_email_address = await run_in_threadpool(
                entra_auth_port.get_user_email_address, credentials.credentials
            )
            # Built here, not as a dependency, so setup errors go through handle_failure.
            use_case = self.audit_use_case_type(
                audit_port=AuditRepositoryAdapter(session=session)
            )
            await self.audit_writer(
                user_email_address=user_email_address,
                use_case=use_case,
                request=request,
            )
        # Runs after the audit so a denied request is still recorded before the 403.
        self.permission_checker(permissions)


def audit_report_and_require_permission(
    possible_permissions: Iterable[Permission] | Permission,
    audit_use_case_type: type[AuditUseCase],
    audit_writer: AuditWriter,
) -> ReportAuditerPermissionChecker:
    """Audit every authenticated attempt, with permission denial taking precedence."""
    return ReportAuditerPermissionChecker(
        possible_permissions=possible_permissions,
        audit_use_case_type=audit_use_case_type,
        audit_writer=audit_writer,
    )
