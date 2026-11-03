import csv
import io
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from app.domain.application_backlog_report import ApplicationBacklogRecord
from app.domain.constants.report_csv_headers import APPLICATION_BACKLOG_REPORT_HEADERS
from app.models.application.enums import MeritsDecision
from app.use_cases.exceptions import (
    ProviderDetailsRetrievalError,
    ReportGenerationError,
)
from app.use_cases.generate_application_backlog_report import (
    GenerateApplicationBacklogReportUseCase,
)
from tests.helpers.csv_helpers import parse_csv_rows
from tests.unit.factories import create_base_application_backlog_record


def _build_use_case(
    applications: list[ApplicationBacklogRecord] | None = None,
    firms_response: list[dict] | None = None,
) -> GenerateApplicationBacklogReportUseCase:
    backlog_port = MagicMock()
    backlog_port.get_application_backlog_records.return_value = applications or []

    provider_details_port = MagicMock()
    provider_details_port.get_firms_by_ids.return_value = firms_response or []

    return GenerateApplicationBacklogReportUseCase(
        application_backlog_port=backlog_port,
        provider_details_port=provider_details_port,
    )


class TestGenerateApplicationBacklogReportUseCase:
    class TestDuplicateApplicationColumns:
        def test_returns_Yes_in_Potential_duplicate_column_for_applications_with_multiple_duplicates(
            self,
        ):
            record = ApplicationBacklogRecord(
                laa_reference="INQ-AAA-001",
                merits_decision="SUBMITTED",
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
                firm_code="123",
                office_id="T3STID",
                proceeding_description="Inquest",
                matter_type="INQUESTS",
                potential_duplicate_applications=["INQ-AAA-002", "INQ-AAA-003"],
            )
            backlog_port = MagicMock()
            backlog_port.get_application_backlog_records.return_value = [record]
            provider_details_port = MagicMock()
            provider_details_port.get_firms_by_ids.return_value = [
                {"firmNumber": "123", "firmName": "Test Firm"}
            ]
            use_case = GenerateApplicationBacklogReportUseCase(
                application_backlog_port=backlog_port,
                provider_details_port=provider_details_port,
            )

            rows = parse_csv_rows(use_case.execute())

            backlog_port.get_application_backlog_records.assert_called_once_with()
            backlog_port.get_pending_applications.assert_not_called()
            assert len(rows) == 1
            assert rows[0]["Potential duplicate"] == "Yes"
            assert rows[0][
                "Potential duplicate submitted application reference(s)"
            ] == ("INQ-AAA-002; INQ-AAA-003")

        def test_returns_Yes_in_Potential_duplicate_column_for_application_with_a_duplicate(
            self,
        ):
            record = ApplicationBacklogRecord(
                laa_reference="INQ-AAA-001",
                merits_decision="SUBMITTED",
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
                firm_code="123",
                office_id="T3STID",
                proceeding_description="Inquest",
                matter_type="INQUESTS",
                potential_duplicate_applications=["INQ-AAA-002"],
            )
            backlog_port = MagicMock()
            backlog_port.get_application_backlog_records.return_value = [record]
            provider_details_port = MagicMock()
            provider_details_port.get_firms_by_ids.return_value = [
                {"firmNumber": "123", "firmName": "Test Firm"}
            ]
            use_case = GenerateApplicationBacklogReportUseCase(
                application_backlog_port=backlog_port,
                provider_details_port=provider_details_port,
            )

            rows = parse_csv_rows(use_case.execute())

            backlog_port.get_application_backlog_records.assert_called_once_with()
            backlog_port.get_pending_applications.assert_not_called()
            assert len(rows) == 1
            assert rows[0]["Potential duplicate"] == "Yes"
            assert rows[0][
                "Potential duplicate submitted application reference(s)"
            ] == ("INQ-AAA-002")

        def test_returns_No_in_Potential_duplicate_column_when_no_application_duplicates(
            self,
        ):
            application = create_base_application_backlog_record()

            use_case = _build_use_case(
                applications=[application],
                firms_response=[{"firmNumber": "123", "firmName": "Test Firm"}],
            )

            result = use_case.execute()
            rows = parse_csv_rows(result)
            row = rows[0]

            assert row["Potential duplicate"] == "No"
            assert row["Potential duplicate submitted application reference(s)"] == ""

    def test_returns_empty_csv_with_headers_when_no_pending_applications(self):
        use_case = _build_use_case(applications=[])

        result = use_case.execute()

        reader = csv.reader(io.StringIO(result))
        headers = next(reader)
        rows = list(reader)

        assert headers == APPLICATION_BACKLOG_REPORT_HEADERS
        assert len(rows) == 0

    def test_returns_csv_row_for_pending_application(self):
        application = create_base_application_backlog_record()

        use_case = _build_use_case(
            applications=[application],
            firms_response=[{"firmNumber": "123", "firmName": "Test Firm"}],
        )

        result = use_case.execute()
        rows = parse_csv_rows(result)
        row = rows[0]

        assert len(rows) == 1
        assert row["Application reference"] == str(
            application.laa_reference
        )
        assert row["Current application status"] == MeritsDecision.SUBMITTED
        assert row["Office account number"] == application.office_id
        assert row["Firm name"] == "Test Firm"
        assert row["Proceeding"] == application.proceeding_description
        assert row["Matter type"] == "INQUESTS"
        assert row["Potential duplicate"] == "No"
        assert row["Potential duplicate submitted application reference(s)"] == ""

    def test_resolves_firm_name_from_firms_response(self):
        application = create_base_application_backlog_record(firm_code="456")

        use_case = _build_use_case(
            applications=[application],
            firms_response=[{"firmNumber": "456", "firmName": "Acme Solicitors"}],
        )

        result = use_case.execute()
        rows = parse_csv_rows(result)

        assert rows[0]["Firm name"] == "Acme Solicitors"

    def test_raises_error_when_firm_name_not_found_for_application(self):
        application = create_base_application_backlog_record(firm_code="999")

        use_case = _build_use_case(
            applications=[application],
            firms_response=[{"firmNumber": "OTHER", "firmName": "Other Firm"}],
        )

        with pytest.raises(ReportGenerationError):
            use_case.execute()

    def test_multiple_applications_all_included(self):
        app1 = create_base_application_backlog_record(
            laa_reference="INQ-AAA-001", firm_code="1"
        )
        app2 = create_base_application_backlog_record(
            laa_reference="INQ-AAA-002", firm_code="2"
        )

        use_case = _build_use_case(
            applications=[app1, app2],
            firms_response=[
                {"firmNumber": "1", "firmName": "Firm One"},
                {"firmNumber": "2", "firmName": "Firm Two"},
            ],
        )

        result = use_case.execute()
        rows = parse_csv_rows(result)

        assert len(rows) == 2
        refs = [row["Application reference"] for row in rows]
        assert app1.laa_reference in refs
        assert app2.laa_reference in refs

    def test_raises_exception_when_firms_retrieval_fails(self):
        application = create_base_application_backlog_record()

        backlog_port = MagicMock()
        backlog_port.get_application_backlog_records.return_value = [application]

        provider_details_port = MagicMock()
        provider_details_port.get_firms_by_ids.side_effect = (
            ProviderDetailsRetrievalError("Provider API unavailable")
        )

        use_case = GenerateApplicationBacklogReportUseCase(
            application_backlog_port=backlog_port,
            provider_details_port=provider_details_port,
        )

        with pytest.raises(ProviderDetailsRetrievalError):
            use_case.execute()

    def test_deduplicates_firm_ids_before_calling_port(self):
        app1 = create_base_application_backlog_record(laa_reference="INQ-AAA-001")
        app2 = create_base_application_backlog_record(laa_reference="INQ-AAA-002")

        backlog_port = MagicMock()
        backlog_port.get_application_backlog_records.return_value = [app1, app2]

        provider_details_port = MagicMock()
        provider_details_port.get_firms_by_ids.return_value = [
            {"firmNumber": "123", "firmName": "Shared Firm"}
        ]

        use_case = GenerateApplicationBacklogReportUseCase(
            application_backlog_port=backlog_port,
            provider_details_port=provider_details_port,
        )

        use_case.execute()

        provider_details_port.get_firms_by_ids.assert_called_once_with(["123"])
