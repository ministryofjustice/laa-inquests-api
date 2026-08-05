import csv
import io
from unittest.mock import MagicMock
import pytest

from app.models.application.enums import MeritsDecision
from app.use_cases.generate_application_backlog_report import (
    GenerateApplicationBacklogReportUseCase,
)
from app.use_cases.exceptions import ProviderDetailsRetrievalError
from tests.unit.factories import (
    create_base_application,
    create_base_application_proceeding,
    create_base_provider,
)

EXPECTED_HEADERS = [
    "Application Reference",
    "Current Status",
    "Application Received Date",
    "Firm Name",
    "Firm Account Number",
    "Proceeding Code",
    "Matter Type",
]


def _build_use_case(
    applications: list | None = None,
    advocate_firms: dict[str, str] | None = None,
) -> GenerateApplicationBacklogReportUseCase:
    backlog_port = MagicMock()
    backlog_port.get_pending_applications.return_value = applications or []

    provider_details_port = MagicMock()
    provider_details_port.get_advocate_firms.return_value = advocate_firms or {}

    return GenerateApplicationBacklogReportUseCase(
        application_backlog_port=backlog_port,
        provider_details_port=provider_details_port,
    )


def _parse_csv(csv_content: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(csv_content)))


class TestGenerateApplicationBacklogReportUseCase:
    def test_returns_empty_csv_with_headers_when_no_pending_applications(self):
        use_case = _build_use_case(applications=[])

        result = use_case.execute()

        reader = csv.reader(io.StringIO(result))
        headers = next(reader)
        rows = list(reader)

        assert headers == EXPECTED_HEADERS
        assert len(rows) == 0

    def test_returns_csv_row_for_pending_application(self):
        provider = create_base_provider(firm_code="FIRM01")
        proceeding = create_base_application_proceeding(
            merits_decision=MeritsDecision.PENDING,
        )
        application = create_base_application(
            provider=provider,
            proceeding=proceeding,
        )

        use_case = _build_use_case(applications=[application])

        result = use_case.execute()
        rows = _parse_csv(result)
        row = rows[0]

        assert len(rows) == 1
        assert row["Application Reference"] == str(application.laa_reference)
        assert row["Current Status"] == MeritsDecision.PENDING
        assert row["Firm Account Number"] == "FIRM01"
        assert row["Proceeding Code"] == "IQOT"
        assert row["Matter Type"] == "INQUESTS"

    def test_resolves_firm_name_from_advocate_firms_lookup(self):
        provider = create_base_provider(firm_code="FIRM01")
        application = create_base_application(provider=provider)

        use_case = _build_use_case(
            applications=[application],
            advocate_firms={"FIRM01": "Acme Solicitors"},
        )

        result = use_case.execute()
        rows = _parse_csv(result)

        assert rows[0]["Firm Name"] == "Acme Solicitors"

    def test_firm_name_empty_when_not_in_advocate_firms(self):
        provider = create_base_provider(firm_code="UNKNOWN")
        application = create_base_application(provider=provider)

        use_case = _build_use_case(
            applications=[application],
            advocate_firms={"OTHER": "Other Firm"},
        )

        result = use_case.execute()
        rows = _parse_csv(result)

        assert rows[0]["Firm Name"] == ""

    def test_multiple_applications_all_included(self):
        app1 = create_base_application(
            laa_reference=100,
            provider=create_base_provider(firm_code="F1"),
        )
        app2 = create_base_application(
            laa_reference=200,
            provider=create_base_provider(firm_code="F2"),
        )

        use_case = _build_use_case(applications=[app1, app2])

        result = use_case.execute()
        rows = _parse_csv(result)

        assert len(rows) == 2
        refs = [row["Application Reference"] for row in rows]
        assert "100" in refs
        assert "200" in refs

    def test_raises_exception_when_advocate_firms_retrieval_fails(self):
        provider = create_base_provider(firm_code="FIRM01")
        application = create_base_application(provider=provider)

        backlog_port = MagicMock()
        backlog_port.get_pending_applications.return_value = [application]

        provider_details_port = MagicMock()
        provider_details_port.get_advocate_firms.side_effect = (
            ProviderDetailsRetrievalError("Provider API unavailable")
        )

        use_case = GenerateApplicationBacklogReportUseCase(
            application_backlog_port=backlog_port,
            provider_details_port=provider_details_port,
        )

        with pytest.raises(ProviderDetailsRetrievalError):
            use_case.execute()
