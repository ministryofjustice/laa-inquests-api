from abc import ABC, abstractmethod

from app.models.audit.enums import AuditType
from app.models.audit.index import ReportDownloadAudit


class AuditPort(ABC):
    @abstractmethod
    def audit_report_download(
        self,
        user_email_address: str,
        report_type: AuditType,
        parameters: dict | None = None,
    ) -> ReportDownloadAudit: ...

    @abstractmethod
    def commit(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...
