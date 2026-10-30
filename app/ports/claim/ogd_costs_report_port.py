from abc import ABC, abstractmethod
from collections.abc import Iterator
from datetime import datetime

from app.domain.ogd_costs_report import OgdCostsReportSourceLine
from app.models.application.enums import PublicBodyId


class OgdCostsReportPort(ABC):
    @abstractmethod
    def get_ogd_public_bodies_by_application(
        self, decided_from: datetime, decided_before: datetime
    ) -> dict[int, list[PublicBodyId]]: ...

    @abstractmethod
    def iter_ogd_costs_report_lines(
        self, decided_from: datetime, decided_before: datetime
    ) -> Iterator[OgdCostsReportSourceLine]: ...
