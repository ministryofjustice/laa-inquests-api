from abc import ABC, abstractmethod

from app.models.audit.enums import ReportType
from app.models.audit.index import ReportAudit


class AuditPort(ABC):
    @abstractmethod
    def audit_report(
        self,
        user_email_address: str,
        report_type: ReportType,
        parameters: dict | None = None,
    ) -> ReportAudit: ...

    @abstractmethod
    def commit(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...
