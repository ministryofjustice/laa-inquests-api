from abc import ABC, abstractmethod
from collections.abc import Iterator

from app.domain.cost_limit_forecast_report import CostLimitForecastCandidate


class CostLimitForecastReportPort(ABC):
    @abstractmethod
    def iter_forecast_candidates(self) -> Iterator[CostLimitForecastCandidate]:
        """Yield every certificate that has an effective date, with its claims and
        public bodies, ordered by effective date then reference."""
        ...
