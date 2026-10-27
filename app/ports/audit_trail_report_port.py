from abc import ABC, abstractmethod
from collections.abc import Iterator
from datetime import datetime

from app.domain.audit_trail import AuditTrailEvent


class AuditTrailReportPort(ABC):
    """Each method yields the events in [from_inclusive, before_exclusive), oldest first."""

    @abstractmethod
    def iter_history_events(
        self, from_inclusive: datetime, before_exclusive: datetime
    ) -> Iterator[AuditTrailEvent]: ...

    @abstractmethod
    def iter_application_view_events(
        self, from_inclusive: datetime, before_exclusive: datetime
    ) -> Iterator[AuditTrailEvent]: ...

    @abstractmethod
    def iter_report_events(
        self, from_inclusive: datetime, before_exclusive: datetime
    ) -> Iterator[AuditTrailEvent]: ...
