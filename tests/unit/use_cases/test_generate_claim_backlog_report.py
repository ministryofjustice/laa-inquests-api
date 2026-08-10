import csv
import io
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from app.domain.constants.report_csv_headers import CLAIMS_BACKLOG_REPORT_HEADERS
from app.models.claim.enums import ClaimStatus
from app.models.claim.index import Claim
from app.use_cases.exceptions import (
    ProviderDetailsRetrievalError,
    ReportGenerationError,
)
from app.use_cases.generate_claim_backlog_report import (
    GenerateClaimBacklogReportUseCase,
)
from tests.unit.factories import create_base_application, create_base_provider


def _build_claim(
    *,
    claim_id: int,
    laa_reference: int,
    status: ClaimStatus = ClaimStatus.SUBMITTED,
    submission_date: datetime = datetime(2026, 1, 1, tzinfo=UTC),
) -> Claim:
    return Claim(
        claim_id=claim_id,
        laa_reference=laa_reference,
        claim_type_id="FINAL_BILL",
        status_id=status,
        submission_date=submission_date,
    )


def _build_use_case(
    claims: list[Claim] | None = None,
    firms: list[dict] | None = None,
) -> GenerateClaimBacklogReportUseCase:
    claim_backlog_port = MagicMock()
    claim_backlog_port.get_open_claims.return_value = claims or []

    provider_details_port = MagicMock()
    provider_details_port.get_firms_by_ids.return_value = (
        [{"firmNumber": "ABC123", "firmName": "Test Firm"}] if firms is None else firms
    )

    return GenerateClaimBacklogReportUseCase(
        claim_backlog_port=claim_backlog_port,
        provider_details_port=provider_details_port,
    )


def _parse_csv(csv_content: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(csv_content)))


class TestGenerateClaimBacklogReportUseCase:
    def test_returns_empty_csv_with_headers_when_no_open_claims(self):
        use_case = _build_use_case(claims=[])

        result = use_case.execute()

        reader = csv.reader(io.StringIO(result))
        headers = next(reader)
        rows = list(reader)

        assert headers == CLAIMS_BACKLOG_REPORT_HEADERS
        assert rows == []

    def test_returns_csv_row_for_open_claim(self):
        claim = _build_claim(claim_id=10, laa_reference=12345)
        claim.application = create_base_application(
            provider=create_base_provider(firm_code="ABC123")
        )
        use_case = _build_use_case(claims=[claim])

        result = use_case.execute()
        rows = _parse_csv(result)

        assert len(rows) == 1
        row = rows[0]
        assert row["Claims Reference Number"] == "10"
        assert row["Current Claims Status"] == ClaimStatus.SUBMITTED
        assert row["Claim Received Date"] == "2026-01-01 00:00:00"
        assert row["Firm Name"] == "Test Firm"
        assert row["Firm Account Number"] == "ABC123"
        assert row["Proceeding Code"] == "IQOT"
        assert row["Matter Type"] == "INQUESTS"

    def test_raises_error_when_firm_name_missing_for_firm_code(self):
        claim = _build_claim(claim_id=13, laa_reference=12345)
        claim.application = create_base_application(
            provider=create_base_provider(firm_code="ABC123")
        )
        use_case = _build_use_case(claims=[claim], firms=[])

        with pytest.raises(ReportGenerationError):
            use_case.execute()

    def test_raises_exception_when_firms_retrieval_fails(self):
        claim = _build_claim(claim_id=14, laa_reference=12345)
        claim.application = create_base_application(
            provider=create_base_provider(firm_code="ABC123")
        )

        claim_backlog_port = MagicMock()
        claim_backlog_port.get_open_claims.return_value = [claim]

        provider_details_port = MagicMock()
        provider_details_port.get_firms_by_ids.side_effect = (
            ProviderDetailsRetrievalError("Provider API unavailable")
        )

        use_case = GenerateClaimBacklogReportUseCase(
            claim_backlog_port=claim_backlog_port,
            provider_details_port=provider_details_port,
        )

        with pytest.raises(ProviderDetailsRetrievalError):
            use_case.execute()

    def test_deduplicates_firm_codes_before_calling_port(self):
        claim_1 = _build_claim(claim_id=15, laa_reference=100)
        claim_2 = _build_claim(claim_id=16, laa_reference=200)
        application = create_base_application(
            provider=create_base_provider(firm_code="ABC123")
        )
        claim_1.application = application
        claim_2.application = application

        claim_backlog_port = MagicMock()
        claim_backlog_port.get_open_claims.return_value = [claim_1, claim_2]

        provider_details_port = MagicMock()
        provider_details_port.get_firms_by_ids.return_value = [
            {"firmNumber": "ABC123", "firmName": "Test Firm"}
        ]

        use_case = GenerateClaimBacklogReportUseCase(
            claim_backlog_port=claim_backlog_port,
            provider_details_port=provider_details_port,
        )

        use_case.execute()

        provider_details_port.get_firms_by_ids.assert_called_once_with(["ABC123"])
        provider_details_port.get_firms_by_ids.assert_called_once_with(["ABC123"])
