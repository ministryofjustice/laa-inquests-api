import logging
from datetime import UTC, date, datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from app.domain.audit_trail import AuditTrailEvent
from app.use_cases.exceptions import (
    InvalidDateRangeError,
    ProviderDetailsRetrievalError,
    ReportGenerationError,
)
from app.use_cases.generate_audit_trail_report import (
    GenerateAuditTrailReportUseCase,
)
from tests.helpers.csv_helpers import parse_csv_fieldnames, parse_csv_rows

FROM_DATE = date(2025, 3, 1)
TO_DATE = date(2025, 3, 30)
AUDIT_TRAIL_REPORT_HEADERS = [
    "Event title",
    "Event description",
    "Event date",
    "Event time",
    "Username",
    "Case reference",
    "Firm name",
    "Office account number",
]


def _at(hour: int, minute: int = 0, second: int = 0) -> datetime:
    return datetime(2025, 3, 15, hour, minute, second, tzinfo=UTC)


def _history(
    occurred_at: datetime | None = None,
    event_reference: str = "EVT-BUS-APP-001",
    username: str = "provider@example.com",
    firm_code: str | None = "0A123B",
    office_id: str | None = "0U651L",
    event_data: dict | None = None,
) -> AuditTrailEvent:
    return AuditTrailEvent(
        occurred_at=occurred_at or _at(12),
        event_reference=event_reference,
        username=username,
        laa_reference="INQ-123-456",
        firm_code=firm_code,
        office_id=office_id,
        event_data=event_data,
    )


def _view(occurred_at: datetime | None = None) -> AuditTrailEvent:
    return AuditTrailEvent(
        occurred_at=occurred_at or _at(12),
        event_reference="EVT-AUD-001",
        username="caseworker@example.com",
        laa_reference="INQ-123-456",
    )


def _report(occurred_at: datetime | None = None) -> AuditTrailEvent:
    return AuditTrailEvent(
        occurred_at=occurred_at or _at(12),
        event_reference="EVT-AUD-003",
        username="assurance@example.com",
        event_data={"report_name": "Payment Extract"},
    )


def _logged_events(caplog, event: str) -> list[dict]:
    return [
        record.extra
        for record in caplog.records
        if getattr(record, "extra", {}).get("event") == event
    ]


def _failure_records(caplog) -> list[logging.LogRecord]:
    return [
        record
        for record in caplog.records
        if getattr(record, "extra", {}).get("event")
        == "audit_trail_report_generation_failed"
    ]


def _build_use_case(
    history: list[AuditTrailEvent] | None = None,
    views: list[AuditTrailEvent] | None = None,
    reports: list[AuditTrailEvent] | None = None,
    firms: list[dict] | None = None,
) -> tuple[GenerateAuditTrailReportUseCase, MagicMock, MagicMock]:
    report_port = MagicMock()
    report_port.iter_history_events.side_effect = lambda *_: iter(history or [])
    report_port.iter_application_view_events.side_effect = lambda *_: iter(views or [])
    report_port.iter_report_events.side_effect = lambda *_: iter(reports or [])

    provider_details_port = MagicMock()
    provider_details_port.get_firms_by_ids.return_value = (
        [{"firmNumber": "0A123B", "firmName": "Test Firm"}] if firms is None else firms
    )
    use_case = GenerateAuditTrailReportUseCase(
        audit_trail_report_port=report_port,
        provider_details_port=provider_details_port,
    )
    return use_case, report_port, provider_details_port


class TestDateRange:
    def test_queries_each_source_from_midnight_to_the_start_of_the_day_after_to_date(
        self,
    ):
        use_case, report_port, _ = _build_use_case()

        use_case.execute(FROM_DATE, TO_DATE)

        bounds = (
            datetime(2025, 3, 1, 0, 0, 0, tzinfo=UTC),
            datetime(2025, 3, 31, 0, 0, 0, tzinfo=UTC),
        )
        report_port.iter_history_events.assert_called_once_with(*bounds)
        report_port.iter_application_view_events.assert_called_once_with(*bounds)
        report_port.iter_report_events.assert_called_once_with(*bounds)

    def test_accepts_a_single_day_and_exactly_30_days(self):
        use_case, _, _ = _build_use_case()

        use_case.execute(date(2025, 3, 1), date(2025, 3, 1))
        use_case.execute(date(2025, 3, 1), date(2025, 3, 30))

    def test_rejects_from_date_after_to_date(self):
        use_case, report_port, _ = _build_use_case()

        with pytest.raises(InvalidDateRangeError, match="on or before"):
            use_case.execute(date(2025, 4, 1), date(2025, 3, 31))

        report_port.iter_history_events.assert_not_called()

    def test_rejects_ranges_over_30_days(self):
        use_case, report_port, _ = _build_use_case()

        with pytest.raises(InvalidDateRangeError, match="30 days"):
            use_case.execute(date(2025, 3, 1), date(2025, 3, 31))

        report_port.iter_history_events.assert_not_called()


class TestOrdering:
    def test_orders_events_from_all_sources_by_time(self):
        use_case, _, _ = _build_use_case(
            history=[_history(_at(9)), _history(_at(11))],
            views=[_view(_at(10)), _view(_at(13))],
            reports=[_report(_at(8)), _report(_at(12))],
        )

        rows = parse_csv_rows(use_case.execute(FROM_DATE, TO_DATE))

        assert [row["Event time"] for row in rows] == [
            "08:00:00",
            "09:00:00",
            "10:00:00",
            "11:00:00",
            "12:00:00",
            "13:00:00",
        ]

    def test_keeps_history_then_views_then_reports_for_identical_times(self):
        use_case, _, _ = _build_use_case(
            history=[_history(_at(12))],
            views=[_view(_at(12))],
            reports=[_report(_at(12))],
        )

        rows = parse_csv_rows(use_case.execute(FROM_DATE, TO_DATE))

        assert [row["Event title"] for row in rows] == [
            "Application submitted",
            "Application viewed",
            "Report downloaded",
        ]


class TestCsvContent:
    def test_returns_headers_only_when_there_are_no_events(self):
        use_case, _, provider_details_port = _build_use_case()

        content = use_case.execute(FROM_DATE, TO_DATE)

        assert parse_csv_fieldnames(content) == AUDIT_TRAIL_REPORT_HEADERS
        assert parse_csv_rows(content) == []
        provider_details_port.get_firms_by_ids.assert_not_called()

    def test_formats_a_provider_row_with_firm_details(self):
        use_case, _, _ = _build_use_case(history=[_history(_at(14, 5, 9))])

        rows = parse_csv_rows(use_case.execute(FROM_DATE, TO_DATE))

        assert rows == [
            {
                "Event title": "Application submitted",
                "Event description": "Application received",
                "Event date": "2025-03-15",
                "Event time": "14:05:09",
                "Username": "provider@example.com",
                "Case reference": "INQ-123-456",
                "Firm name": "Test Firm",
                "Office account number": "0U651L",
            }
        ]

    def test_leaves_case_and_firm_fields_blank_when_not_applicable(self):
        use_case, _, _ = _build_use_case(reports=[_report()])

        (row,) = parse_csv_rows(use_case.execute(FROM_DATE, TO_DATE))

        assert row["Case reference"] == ""
        assert row["Firm name"] == ""
        assert row["Office account number"] == ""
        assert row["Event description"] == "Payment Extract downloaded"

    def test_reports_event_times_in_utc(self):
        offset = timezone(timedelta(hours=1))
        use_case, _, _ = _build_use_case(
            views=[
                AuditTrailEvent(
                    occurred_at=datetime(2025, 3, 16, 0, 30, tzinfo=offset),
                    event_reference="EVT-AUD-001",
                    username="a@example.com",
                )
            ]
        )

        (row,) = parse_csv_rows(use_case.execute(FROM_DATE, TO_DATE))

        assert (row["Event date"], row["Event time"]) == ("2025-03-15", "23:30:00")

    def test_treats_naive_timestamps_as_utc(self):
        use_case, _, _ = _build_use_case(
            views=[
                AuditTrailEvent(
                    # Naive on purpose: the history table can return naive values.
                    occurred_at=datetime(2025, 3, 15, 8, 0, tzinfo=UTC).replace(
                        tzinfo=None
                    ),
                    event_reference="EVT-AUD-001",
                    username="a@example.com",
                )
            ]
        )

        (row,) = parse_csv_rows(use_case.execute(FROM_DATE, TO_DATE))

        assert row["Event time"] == "08:00:00"

    def test_keeps_multi_line_descriptions_in_a_single_cell(self):
        use_case, _, _ = _build_use_case(
            history=[
                _history(
                    event_reference="EVT-BUS-X-001",
                    username="Caseworker",
                    firm_code=None,
                    office_id=None,
                    event_data={"note_text": "line one\nline two"},
                )
            ]
        )

        rows = parse_csv_rows(use_case.execute(FROM_DATE, TO_DATE))

        assert len(rows) == 1
        assert (
            rows[0]["Event description"] == "Caseworker note added\nline one\nline two"
        )

    @pytest.mark.parametrize("character", ["=", "+", "-", "@"])
    def test_prefixes_values_that_a_spreadsheet_could_evaluate(self, character):
        use_case, _, _ = _build_use_case(
            history=[_history(username=f"{character}cmd@example.com")]
        )

        (row,) = parse_csv_rows(use_case.execute(FROM_DATE, TO_DATE))

        assert row["Username"] == f"'{character}cmd@example.com"


class TestFirmDetails:
    def test_looks_up_each_firm_once_for_all_provider_events(self):
        use_case, _, provider_details_port = _build_use_case(
            history=[
                _history(_at(9)),
                _history(_at(10)),
                _history(_at(11), firm_code="0B999C", office_id="0X111Z"),
            ],
            firms=[
                {"firmNumber": "0A123B", "firmName": "Firm A"},
                {"firmNumber": "0B999C", "firmName": "Firm B"},
            ],
        )

        rows = parse_csv_rows(use_case.execute(FROM_DATE, TO_DATE))

        provider_details_port.get_firms_by_ids.assert_called_once()
        (requested,) = provider_details_port.get_firms_by_ids.call_args.args
        assert sorted(requested) == ["0A123B", "0B999C"]
        assert [(row["Firm name"], row["Office account number"]) for row in rows] == [
            ("Firm A", "0U651L"),
            ("Firm A", "0U651L"),
            ("Firm B", "0X111Z"),
        ]

    def test_does_not_look_up_firms_when_no_event_has_firm_details(self):
        use_case, _, provider_details_port = _build_use_case(
            history=[_history(firm_code=None, office_id=None)], views=[_view()]
        )

        use_case.execute(FROM_DATE, TO_DATE)

        provider_details_port.get_firms_by_ids.assert_not_called()

    def test_fails_when_a_firm_name_is_not_found(self):
        use_case, _, _ = _build_use_case(history=[_history()], firms=[])

        with pytest.raises(ReportGenerationError, match="0A123B"):
            use_case.execute(FROM_DATE, TO_DATE)

    def test_lets_a_provider_details_failure_propagate(self):
        use_case, _, provider_details_port = _build_use_case(history=[_history()])
        provider_details_port.get_firms_by_ids.side_effect = (
            ProviderDetailsRetrievalError()
        )

        with pytest.raises(ProviderDetailsRetrievalError):
            use_case.execute(FROM_DATE, TO_DATE)


class TestFailures:
    @pytest.mark.parametrize(
        "event",
        [
            _history(event_reference="EVT-BUS-ZZZ-999"),
            _history(event_reference="EVT-BUS-X-001", event_data=None),
        ],
        ids=["unknown_event_reference", "missing_event_data"],
    )
    def test_fails_without_output_when_an_event_cannot_be_described(
        self, event, caplog
    ):
        use_case, _, _ = _build_use_case(history=[_history(), event])

        with caplog.at_level(logging.ERROR), pytest.raises(ReportGenerationError):
            use_case.execute(FROM_DATE, TO_DATE)

        (failure,) = _failure_records(caplog)
        assert failure.levelno == logging.ERROR
        assert failure.exc_info[0] is ReportGenerationError
        assert event.event_reference in caplog.text
        assert failure.extra["from_date"] == FROM_DATE.isoformat()
        assert failure.extra["to_date"] == TO_DATE.isoformat()

    def test_fails_without_output_and_logs_when_reading_events_fails(self, caplog):
        use_case, report_port, _ = _build_use_case(history=[_history()])
        report_port.iter_report_events.side_effect = RuntimeError("database down")

        with caplog.at_level(logging.ERROR), pytest.raises(RuntimeError):
            use_case.execute(FROM_DATE, TO_DATE)

        (failure,) = _failure_records(caplog)
        assert failure.levelno == logging.ERROR
        assert failure.exc_info[0] is RuntimeError
        assert "database down" in caplog.text

    def test_logs_the_row_count_on_success(self, caplog):
        use_case, _, _ = _build_use_case(history=[_history()], views=[_view()])

        with caplog.at_level(logging.INFO):
            use_case.execute(FROM_DATE, TO_DATE)

        (generated,) = _logged_events(caplog, "audit_trail_report_generated")
        assert generated["row_count"] == 2
