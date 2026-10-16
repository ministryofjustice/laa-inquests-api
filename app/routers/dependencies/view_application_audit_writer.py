from collections.abc import Callable
from typing import Annotated

from fastapi import Depends
from fastapi.concurrency import run_in_threadpool
from sqlmodel import Session

from app.adapters.audit_repository_adapter import AuditRepositoryAdapter
from app.use_cases.audit.view_application_audit import ViewApplicationAuditUseCase
from app.db import get_session
from app.ports.audit_port import AuditPort


def get_audit_repository_adapter(
    session: Session = Depends(get_session),
) -> AuditRepositoryAdapter:
    return AuditRepositoryAdapter(session=session)


def get_view_application_audit_use_case(
    audit_port: Annotated[AuditPort, Depends(get_audit_repository_adapter)],
) -> ViewApplicationAuditUseCase:
    return ViewApplicationAuditUseCase(audit_port=audit_port)


def view_application_audit_use_case_factory(
    session: Annotated[Session, Depends(get_session)],
) -> Callable[[], ViewApplicationAuditUseCase]:
    """Return a callable that builds the audit use case on the request's session.

    Tests override this dependency to inject audit setup failures.
    """

    def create_audit_use_case() -> ViewApplicationAuditUseCase:
        return get_view_application_audit_use_case(
            audit_port=get_audit_repository_adapter(session=session)
        )

    return create_audit_use_case


class ViewApplicationAuditWriter:
    """Records a view application audit event for a specific page."""

    def __init__(
        self,
        page: str,
    ) -> None:
        self.page = page

    async def __call__(
        self,
        user_email_address: str,
        laa_reference: str,
        use_case: ViewApplicationAuditUseCase,
    ) -> None:
        # The use case performs blocking database I/O, so keep it off the event loop.
        await run_in_threadpool(
            use_case.execute,
            user_email_address=user_email_address,
            laa_reference=laa_reference,
            page=self.page,
        )
