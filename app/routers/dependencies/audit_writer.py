from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Request
from fastapi.concurrency import run_in_threadpool
from sqlmodel import Session

from app.adapters.audit_repository_adapter import AuditRepositoryAdapter
from app.db import get_session
from app.models.audit.enums import ReportType
from app.ports.audit_port import AuditPort
from app.use_cases.audit.report_audit import ReportAuditUseCase


def get_audit_repository_adapter(
    session: Session = Depends(get_session),
) -> AuditRepositoryAdapter:
    return AuditRepositoryAdapter(session=session)


def get_audit_report_use_case(
    audit_port: Annotated[AuditPort, Depends(get_audit_repository_adapter)],
) -> ReportAuditUseCase:
    return ReportAuditUseCase(audit_port=audit_port)


def report_audit_use_case_factory(
    session: Annotated[Session, Depends(get_session)],
) -> Callable[[], ReportAuditUseCase]:
    """Return a callable that builds the audit use case on the request's session.

    Tests override this dependency to inject audit setup failures.
    """

    def create_audit_use_case() -> ReportAuditUseCase:
        return get_audit_report_use_case(
            audit_port=get_audit_repository_adapter(session=session)
        )

    return create_audit_use_case


class ReportAuditWriter:
    """Records a report audit event for a specific report type."""

    def __init__(
        self,
        report_type: ReportType,
    ) -> None:
        self.report_type = report_type

    async def __call__(
        self,
        user_email_address: str,
        use_case: ReportAuditUseCase,
        request: Request,
    ) -> None:
        # The use case performs blocking database I/O, so keep it off the event loop.
        await run_in_threadpool(
            use_case.execute,
            user_email_address=user_email_address,
            report_type=self.report_type,
            # Only the payment extract is filtered by user-supplied query parameters.
            parameters=dict(request.query_params)
            if self.report_type == ReportType.PAYMENT_EXTRACT
            else None,
        )
