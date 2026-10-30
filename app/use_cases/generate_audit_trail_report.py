import csv
import heapq
import io
import logging
from datetime import UTC, date, datetime

from app.domain.audit_event_catalogue import EventDescriptionError, describe_event
from app.domain.audit_trail import AuditTrailEvent, csv_safe
from app.domain.constants.report_csv_headers import AUDIT_TRAIL_REPORT_HEADERS
from app.logging_utils import build_log_extra
from app.ports.audit_trail_report_port import AuditTrailReportPort
from app.ports.provider_details_port import ProviderDetailsPort
from app.use_cases.exceptions import ReportGenerationError
from app.use_cases.report_date_range import resolve_report_window

logger = logging.getLogger(__name__)

MAX_REPORT_RANGE_DAYS = 30


class GenerateAuditTrailReportUseCase:
    def __init__(
        self,
        audit_trail_report_port: AuditTrailReportPort,
        provider_details_port: ProviderDetailsPort,
    ) -> None:
        self.audit_trail_report_port = audit_trail_report_port
        self.provider_details_port = provider_details_port

    def execute(self, from_date: date, to_date: date) -> str:
        """Build the whole CSV before returning, so a failure never yields partial output."""
        from_inclusive, before_exclusive = resolve_report_window(
            from_date, to_date, MAX_REPORT_RANGE_DAYS
        )

        try:
            events = self._read_events(from_inclusive, before_exclusive)
            firm_names = self._build_firm_name_lookup(events)
            content = self._build_csv(events, firm_names)
        except Exception:
            logger.exception(
                "Audit trail report generation failed",
                extra=build_log_extra(
                    event="audit_trail_report_generation_failed",
                    from_date=from_date.isoformat(),
                    to_date=to_date.isoformat(),
                ),
            )
            raise

        logger.info(
            "Audit trail report generated",
            extra=build_log_extra(
                event="audit_trail_report_generated", row_count=len(events)
            ),
        )
        return content

    def _read_events(
        self, from_inclusive: datetime, before_exclusive: datetime
    ) -> list[AuditTrailEvent]:
        port = self.audit_trail_report_port
        return list(
            heapq.merge(
                port.iter_history_events(from_inclusive, before_exclusive),
                port.iter_application_view_events(from_inclusive, before_exclusive),
                port.iter_report_events(from_inclusive, before_exclusive),
                key=lambda event: _as_utc(event.occurred_at),
            )
        )

    def _build_firm_name_lookup(self, events: list[AuditTrailEvent]) -> dict[str, str]:
        firm_codes = sorted({e.firm_code for e in events if e.firm_code})
        if not firm_codes:
            return {}

        firms = self.provider_details_port.get_firms_by_ids(firm_codes)
        firm_names = {firm["firmNumber"]: firm["firmName"] for firm in firms}
        for firm_code in firm_codes:
            if firm_names.get(firm_code) is None:
                raise ReportGenerationError(
                    f"Firm name not found for firm code {firm_code}"
                )
        return firm_names

    def _build_csv(
        self, events: list[AuditTrailEvent], firm_names: dict[str, str]
    ) -> str:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(AUDIT_TRAIL_REPORT_HEADERS)
        for event in events:
            writer.writerow(self._build_row(event, firm_names))
        return buffer.getvalue()

    @staticmethod
    def _build_row(event: AuditTrailEvent, firm_names: dict[str, str]) -> list[str]:
        try:
            described = describe_event(event.event_reference, event.event_data)
        except EventDescriptionError as exc:
            raise ReportGenerationError(str(exc)) from exc

        occurred_at = _as_utc(event.occurred_at)
        return [
            csv_safe(value)
            for value in (
                described.title,
                described.description,
                occurred_at.strftime("%Y-%m-%d"),
                occurred_at.strftime("%H:%M:%S"),
                event.username,
                event.laa_reference or "",
                firm_names.get(event.firm_code, "") if event.firm_code else "",
                event.office_id or "",
            )
        ]


def _as_utc(value: datetime) -> datetime:
    return value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)
