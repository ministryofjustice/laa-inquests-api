import csv
import io
from unittest.mock import MagicMock

import pytest

from app.domain.constants.report_csv_headers import APPLICATION_BACKLOG_REPORT_HEADERS
from app.models.application.enums import MeritsDecision
from app.use_cases.exceptions import (
    ProviderDetailsRetrievalError,
    ReportGenerationError,
)
from app.use_cases.generate_application_backlog_report import (
    GenerateApplicationBacklogReportUseCase,
)
from tests.unit.factories import (
    create_base_application,
    create_base_application_proceeding,
    create_base_provider,
)
from tests.helpers import parse_csv_rows


def _build_use_case(
    applications: list | None = None,
    firms_response: list[dict] | None = None,
) -> GenerateApplicationBacklogReportUseCase:
    backlog_port = MagicMock()
    backlog_port.get_pending_applications.return_value = applications or []

    provider_details_port = MagicMock()
    provider_details_port.get_firms_by_ids.return_value = firms_response or []

    return GenerateApplicationBacklogReportUseCase(
        application_backlog_port=backlog_port,
        provider_details_port=provider_details_port,
    )


class TestGenerateApplicationBacklogReportUseCase:
    def test_returns_empty_csv_with_headers_when_no_pending_applications(self):
        use_case = _build_use_case(applications=[])

        result = use_case.execute()

        reader = csv.reader(io.StringIO(result))
        headers = next(reader)
        rows = list(reader)

        assert headers == APPLICATION_BACKLOG_REPORT_HEADERS
        assert len(rows) == 0

    def test_returns_csv_row_for_pending_application(self):
        provider = create_base_provider(firm_code="123")
        proceeding = create_base_application_proceeding(
            merits_decision=MeritsDecision.PENDING,
        )
        application = create_base_application(
            provider=provider,
            proceeding=proceeding,
        )

        use_case = _build_use_case(
            applications=[application],
            firms_response=[{"firmNumber": "123", "firmName": "Test Firm"}],
        )

        result = use_case.execute()
        rows = parse_csv_rows(result)
        row = rows[0]

        assert len(rows) == 1
        assert row["Application / Case Reference Number"] == str(
            application.laa_reference
        )
        assert row["Current Application Status"] == MeritsDecision.PENDING
        assert row["Firm Account Number"] == "123"
        assert row["Firm Name"] == "Test Firm"
        assert row["Proceeding Code"] == "IQOT"
        assert row["Matter Type"] == "INQUESTS"

    def test_resolves_firm_name_from_firms_response(self):
        provider = create_base_provider(firm_code="456")
        application = create_base_application(provider=provider)

        use_case = _build_use_case(
            applications=[application],
            firms_response=[{"firmNumber": "456", "firmName": "Acme Solicitors"}],
        )

        result = use_case.execute()
        rows = parse_csv_rows(result)

        assert rows[0]["Firm Name"] == "Acme Solicitors"

    def test_raises_error_when_firm_name_not_found_for_application(self):
        provider = create_base_provider(firm_code="999")
        application = create_base_application(provider=provider)

        use_case = _build_use_case(
            applications=[application],
            firms_response=[{"firmNumber": "OTHER", "firmName": "Other Firm"}],
        )

        with pytest.raises(ReportGenerationError):
            use_case.execute()

    def test_multiple_applications_all_included(self):
        app1 = create_base_application(
            laa_reference=100,
            provider=create_base_provider(firm_code="1"),
        )
        app2 = create_base_application(
            laa_reference=200,
            provider=create_base_provider(firm_code="2"),
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
        refs = [row["Application / Case Reference Number"] for row in rows]
        assert "100" in refs
        assert "200" in refs

    def test_raises_exception_when_firms_retrieval_fails(self):
        provider = create_base_provider(firm_code="123")
        application = create_base_application(provider=provider)

        backlog_port = MagicMock()
        backlog_port.get_pending_applications.return_value = [application]

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
        provider = create_base_provider(firm_code="123")
        app1 = create_base_application(laa_reference=100, provider=provider)
        app2 = create_base_application(laa_reference=200, provider=provider)

        backlog_port = MagicMock()
        backlog_port.get_pending_applications.return_value = [app1, app2]

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
