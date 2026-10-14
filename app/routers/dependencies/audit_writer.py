from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from sqlmodel import Session

from app.adapters.audit_repository_adapter import AuditRepositoryAdapter
from app.db import get_session
from app.models.audit.enums import AuditType
from app.ports.create_audit_event_port import AuditPort
from app.routers.dependencies.entra_auth import (
    EntraAuthPort,
    HTTPAuthorizationCredentials,
    HTTPBearer,
    get_entra_auth_port,
)
from app.use_cases.audit_report_download import AuditReportDownloadUseCase

_http_bearer = HTTPBearer(auto_error=False)


def get_audit_repository_adapter(
    session: Session = Depends(get_session),
) -> AuditRepositoryAdapter:
    return AuditRepositoryAdapter(session=session)


def get_audit_report_download_use_case(
    audit_port: Annotated[AuditPort, Depends(get_audit_repository_adapter)],
) -> AuditReportDownloadUseCase:
    return AuditReportDownloadUseCase(audit_port=audit_port)


def get_audit_report_download_factory(
    session: Annotated[Session, Depends(get_session)],
) -> Callable[[], AuditReportDownloadUseCase]:
    def create_audit_use_case() -> AuditReportDownloadUseCase:
        return get_audit_report_download_use_case(
            audit_port=get_audit_repository_adapter(session=session)
        )

    return create_audit_use_case


@dataclass(frozen=True)
class ReportAuditPreparationFailure:
    error: Exception


def prepare_report_audit(
    factory: Annotated[
        Callable[[], AuditReportDownloadUseCase],
        Depends(get_audit_report_download_factory),
    ],
) -> AuditReportDownloadUseCase | ReportAuditPreparationFailure:
    try:
        return factory()
    except Exception as exc:  # noqa: BLE001 - Re-raised and logged by the permission guard.
        # Defer the error so the endpoint's permission policy determines 403 or 500.
        return ReportAuditPreparationFailure(error=exc)


class AuditWriter:
    def __init__(
        self,
        report_type: AuditType,
    ) -> None:
        self.report_type = report_type

    async def __call__(
        self,
        credentials: Annotated[
            HTTPAuthorizationCredentials | None, Depends(_http_bearer)
        ],
        entra_auth_port: Annotated[EntraAuthPort, Depends(get_entra_auth_port)],
        use_case: Annotated[
            AuditReportDownloadUseCase, Depends(get_audit_report_download_use_case)
        ],
        request: Request,
    ) -> None:
        if credentials is None:
            raise HTTPException(
                status_code=401,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_email_address = await run_in_threadpool(
            entra_auth_port.get_email_address, credentials.credentials
        )
        await run_in_threadpool(
            use_case.execute,
            user_email_address=user_email_address,
            report_type=self.report_type,
            parameters=dict(request.query_params)
            if self.report_type == AuditType.REPORTS_PAYMENT_EXTRACT
            else None,
        )
