from abc import ABC, abstractmethod
from datetime import datetime

from app.domain.decisions_report import DecisionsReportSourceRecord


class DecisionsReportPort(ABC):
    @abstractmethod
    def get_decisions_report_records(
        self, decided_from: datetime, decided_before: datetime
    ) -> list[DecisionsReportSourceRecord]:
        """Return decision events in [decided_from, decided_before), oldest first."""
        ...
