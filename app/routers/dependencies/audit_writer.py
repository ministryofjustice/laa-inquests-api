from typing import Annotated
from app.db import get_session
from fastapi.concurrency import run_in_threadpool
from app.models.audit.enums import ReportType
from sqlmodel import Session
from fastapi import Depends

from app.adapters.audit_repository_adapter import AuditRepositoryAdapter
from app.routers.dependencies.entra_auth import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
    EntraAuthPort,
    get_entra_auth_port,
)

_http_bearer = HTTPBearer(auto_error=False)


def get_audit_repository_adapter(
    session: Session = Depends(get_session),
) -> AuditRepositoryAdapter:
    return AuditRepositoryAdapter(session=session)


class AuditWriter:
    def __init__(
        self,
        report_type: ReportType,
    ):
        self.report_type = report_type

    async def __call__(
        self,
        credentials: Annotated[
            HTTPAuthorizationCredentials | None, Depends(_http_bearer)
        ],
        entra_auth_port: Annotated[EntraAuthPort, Depends(get_entra_auth_port)],
        audit_port: Annotated[
            AuditRepositoryAdapter, Depends(get_audit_repository_adapter)
        ],
    ):
        user_email_address = await run_in_threadpool(
            entra_auth_port.get_email_address, credentials.credentials
        )

        audit_port.audit_report_download(
            user_email_address=user_email_address,
            report_type=self.report_type,
        )
