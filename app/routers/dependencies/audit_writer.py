from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Request
from fastapi.concurrency import run_in_threadpool
from sqlmodel import Session

from app.adapters.audit_repository_adapter import AuditRepositoryAdapter
from app.db import get_session
from app.models.audit.enums import AuditType
from app.ports.create_audit_event_port import AuditPort
from app.use_cases.audit_report_download import AuditReportDownloadUseCase


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


class AuditWriter:
    def __init__(
        self,
        report_type: AuditType,
    ) -> None:
        self.report_type = report_type

    async def __call__(
        self,
        user_email_address: str,
        use_case: AuditReportDownloadUseCase,
        request: Request,
    ) -> None:
        await run_in_threadpool(
            use_case.execute,
            user_email_address=user_email_address,
            report_type=self.report_type,
            parameters=dict(request.query_params)
            if self.report_type == AuditType.REPORTS_PAYMENT_EXTRACT
            else None,
        )
