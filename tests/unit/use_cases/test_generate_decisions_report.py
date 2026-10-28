import logging
from datetime import UTC, date, datetime
from unittest.mock import MagicMock

import pytest

from app.domain.constants.report_csv_headers import DECISIONS_REPORT_HEADERS
from app.domain.decisions_report import DecisionsReportSourceRecord
from app.models.history.enums import ActorType, HistoryEventReference
from app.use_cases.exceptions import InvalidDateRangeError, ReportGenerationError
from app.use_cases.generate_decisions_report import GenerateDecisionsReportUseCase
from tests.helpers.csv_helpers import parse_csv_fieldnames, parse_csv_rows

FROM_DATE = date(2025, 3, 1)
TO_DATE = date(2025, 3, 31)


def _grant_record(
    laa_reference="INQ-AAA-BBB", actor_email_address="jane.smith@example.com"
):
    return DecisionsReportSourceRecord(
        event_reference=HistoryEventReference.APPLICATION_ASSESSMENT_COMPLETED,
        decided_at=datetime(2025, 3, 15, 13, 5, 9, tzinfo=UTC),
        actor="Jane Smith",
        actor_type=ActorType.CASEWORKER,
        actor_email_address=actor_email_address,
        event_data={"merits_decision": "Granted"},
        laa_reference=laa_reference,
        application_submitted_at=datetime(2025, 3, 2, 9, 30, tzinfo=UTC),
    )


def _use_case(records=()):
    port = MagicMock()
    port.get_decisions_report_records.return_value = list(records)
    return GenerateDecisionsReportUseCase(decisions_report_port=port), port


class TestDateRangeValidation:
    def test_from_after_to_is_rejected(self):
        use_case, port = _use_case()

        with pytest.raises(InvalidDateRangeError):
            use_case.execute(date(2025, 3, 31), date(2025, 3, 1))

        port.get_decisions_report_records.assert_not_called()

    def test_same_day_range_is_allowed(self):
        use_case, _ = _use_case()

        use_case.execute(FROM_DATE, FROM_DATE)

    @pytest.mark.parametrize(
        "from_date,to_date",
        [
            (date(2025, 3, 1), date(2025, 4, 1)),
            (date(2025, 1, 31), date(2025, 2, 28)),
            (date(2024, 1, 31), date(2024, 2, 29)),
            (date(2025, 12, 15), date(2026, 1, 15)),
        ],
    )
    def test_range_up_to_same_day_next_month_is_allowed(self, from_date, to_date):
        use_case, _ = _use_case()

        use_case.execute(from_date, to_date)

    @pytest.mark.parametrize(
        "from_date,to_date",
        [
            (date(2025, 3, 1), date(2025, 4, 2)),
            (date(2025, 1, 31), date(2025, 3, 1)),
        ],
    )
    def test_range_longer_than_one_calendar_month_is_rejected(self, from_date, to_date):
        use_case, port = _use_case()

        with pytest.raises(InvalidDateRangeError):
            use_case.execute(from_date, to_date)

        port.get_decisions_report_records.assert_not_called()


class TestCsvOutput:
    def test_no_records_returns_header_only_csv(self):
        use_case, _ = _use_case()

        csv_content = use_case.execute(FROM_DATE, TO_DATE)

        assert parse_csv_fieldnames(csv_content) == DECISIONS_REPORT_HEADERS
        assert parse_csv_rows(csv_content) == []

    def test_one_row_per_record_in_port_order(self):
        use_case, _ = _use_case(
            [_grant_record("INQ-AAA-111"), _grant_record("INQ-BBB-222")]
        )

        rows = parse_csv_rows(use_case.execute(FROM_DATE, TO_DATE))

        assert [row["Case reference"] for row in rows] == [
            "INQ-AAA-111",
            "INQ-BBB-222",
        ]

    def test_queries_half_open_utc_range_covering_whole_to_date(self):
        use_case, port = _use_case()

        use_case.execute(FROM_DATE, TO_DATE)

        port.get_decisions_report_records.assert_called_once_with(
            datetime(2025, 3, 1, 0, 0, tzinfo=UTC),
            datetime(2025, 4, 1, 0, 0, tzinfo=UTC),
        )

    def test_who_column_holds_the_caseworker_email_address(self):
        use_case, _ = _use_case([_grant_record()])

        rows = parse_csv_rows(use_case.execute(FROM_DATE, TO_DATE))

        assert rows[0]["Who"] == "jane.smith@example.com"

    def test_values_with_commas_and_quotes_round_trip(self):
        use_case, _ = _use_case([_grant_record(actor_email_address='a, "b"')])

        rows = parse_csv_rows(use_case.execute(FROM_DATE, TO_DATE))

        assert rows[0]["Who"] == 'a, "b"'


class TestAllOrNothing:
    def _bad_record(self):
        return DecisionsReportSourceRecord(
            event_reference=HistoryEventReference.APPLICATION_ASSESSMENT_COMPLETED,
            decided_at=datetime(2025, 3, 16, tzinfo=UTC),
            actor="Secret Name",
            actor_type=ActorType.CASEWORKER,
            actor_email_address="secret.name@example.com",
            event_data={"merits_decision": "Mystery"},
            laa_reference="INQ-BAD-000",
            application_submitted_at=datetime(2025, 3, 2, tzinfo=UTC),
        )

    def test_invalid_record_fails_whole_report(self):
        use_case, _ = _use_case([_grant_record(), self._bad_record()])

        with pytest.raises(ReportGenerationError):
            use_case.execute(FROM_DATE, TO_DATE)

    def test_invalid_record_is_logged_without_personal_data(self, caplog):
        use_case, _ = _use_case([self._bad_record()])

        with caplog.at_level(logging.ERROR), pytest.raises(ReportGenerationError):
            use_case.execute(FROM_DATE, TO_DATE)

        record = next(
            r
            for r in caplog.records
            if getattr(r, "extra", {}).get("event")
            == "decisions_report_generation_failed"
        )
        assert "Secret Name" not in record.getMessage()
        assert "Secret Name" not in str(record.extra)
        assert "secret.name@example.com" not in record.getMessage()
        assert "secret.name@example.com" not in str(record.extra)
        assert "INQ-BAD-000" not in str(record.extra)

    def test_port_errors_propagate(self):
        use_case, port = _use_case()
        port.get_decisions_report_records.side_effect = RuntimeError("db down")

        with pytest.raises(RuntimeError):
            use_case.execute(FROM_DATE, TO_DATE)

    def test_success_logs_row_count(self, caplog):
        use_case, _ = _use_case([_grant_record(), _grant_record()])

        with caplog.at_level(logging.INFO):
            use_case.execute(FROM_DATE, TO_DATE)

        record = next(
            r
            for r in caplog.records
            if getattr(r, "extra", {}).get("event") == "decisions_report_generated"
        )
        assert record.extra["row_count"] == 2
