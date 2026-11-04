from abc import ABC, abstractmethod
from collections.abc import Iterator
from datetime import date

from app.domain.cost_limit_forecast_report import CostLimitForecastCandidate


class CostLimitForecastReportPort(ABC):
    @abstractmethod
    def iter_forecast_candidates(
        self, effective_from: date, effective_to: date
    ) -> Iterator[CostLimitForecastCandidate]:
        """Yield certificates with an effective date in the inclusive range, with
        their claims and public bodies, ordered by effective date then reference."""
        ...
