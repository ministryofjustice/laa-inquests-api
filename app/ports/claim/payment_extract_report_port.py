from abc import ABC, abstractmethod
from collections.abc import Iterator
from datetime import datetime

from app.domain.payment_extract_report import (
    PaymentExtractReportSourceLine,
    PaymentLineType,
)


class PaymentExtractReportPort(ABC):
    @abstractmethod
    def get_payment_extract_firm_codes(
        self, created_from: datetime, created_before: datetime
    ) -> list[str]: ...

    @abstractmethod
    def get_payment_extract_line_types(
        self, created_from: datetime, created_before: datetime
    ) -> list[PaymentLineType]: ...

    @abstractmethod
    def iter_payment_extract_report_lines(
        self, created_from: datetime, created_before: datetime
    ) -> Iterator[PaymentExtractReportSourceLine]: ...
