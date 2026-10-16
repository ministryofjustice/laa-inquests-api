from abc import ABC, abstractmethod

from app.models.audit.index import BaseAuditEvent


class AuditPort(ABC):
    @abstractmethod
    def audit_event(self, audit_event: BaseAuditEvent) -> BaseAuditEvent: ...

    @abstractmethod
    def commit(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...
