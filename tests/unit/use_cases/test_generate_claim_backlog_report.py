import csv
import io
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.domain.constants.report_csv_headers import CLAIMS_BACKLOG_REPORT_HEADERS
from app.models.claim.enums import ClaimStatus, ClaimType
from app.models.claim.index import Claim
from app.use_cases.exceptions import (
    ProviderDetailsRetrievalError,
    ReportGenerationError,
)
from app.use_cases.generate_claim_backlog_report import (
    GenerateClaimBacklogReportUseCase,
)
from tests.helpers import parse_csv_rows
from tests.unit.factories import (
    create_base_application,
    create_base_claim,
    create_base_provider,
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
        claim = create_base_claim(
            claim_id=10,
            laa_reference=12345,
            claim_type_id=ClaimType.FINAL_BILL,
            total_profit_cost_vat_zero=Decimal("0.00"),
            total_profit_cost_net=Decimal("100.00"),
            total_profit_cost_gross=Decimal("120.00"),
        )
        claim.application = create_base_application(
            provider=create_base_provider(firm_code="ABC123")
        )
        use_case = _build_use_case(claims=[claim])

        result = use_case.execute()
        rows = parse_csv_rows(result)

        assert len(rows) == 1
        row = rows[0]
        assert row["Case reference"] == "10"
        assert row["Firm Name"] == "Test Firm"
        assert row["Firm Account Number"] == "ABC123"
        assert row["Submission date"] == "2026-01-01 00:00:00"
        assert row["Claim status"] == ClaimStatus.SUBMITTED
        assert row["Total 0% VAT claim value"] == "0.00"
        assert row["Net total claim value"] == "100.00"
        assert row["Gross total claim value"] == "120.00"
        assert row["Claim type"] == "FINAL_BILL"

    def test_raises_error_when_firm_name_missing_for_firm_code(self):
        claim = create_base_claim(claim_id=13, laa_reference=12345)
        claim.application = create_base_application(
            provider=create_base_provider(firm_code="ABC123")
        )
        use_case = _build_use_case(claims=[claim], firms=[])

        with pytest.raises(ReportGenerationError):
            use_case.execute()

    def test_raises_error_when_firms_retrieval_fails(self):
        claim = create_base_claim(claim_id=14, laa_reference=12345)
        claim.application = create_base_application(
            provider=create_base_provider(firm_code="ABC123")
        )

        claim_backlog_port = MagicMock()
        claim_backlog_port.get_open_claims.return_value = [claim]

        provider_details_port = MagicMock()
        provider_details_port.get_firms_by_ids.side_effect = (
            ProviderDetailsRetrievalError()
        )

        use_case = GenerateClaimBacklogReportUseCase(
            claim_backlog_port=claim_backlog_port,
            provider_details_port=provider_details_port,
        )

        with pytest.raises(ProviderDetailsRetrievalError):
            use_case.execute()

    def test_deduplicates_firm_codes_before_calling_port(self):
        claim_1 = create_base_claim(
            claim_id=15,
            laa_reference=100,
            claim_type_id=ClaimType.FINAL_BILL,
            total_profit_cost_vat_zero=Decimal("0.00"),
            total_profit_cost_net=Decimal("100.00"),
            total_profit_cost_gross=Decimal("120.00"),
        )
        claim_2 = create_base_claim(
            claim_id=16,
            laa_reference=200,
            claim_type_id=ClaimType.FINAL_BILL,
            total_profit_cost_vat_zero=Decimal("0.00"),
            total_profit_cost_net=Decimal("100.00"),
            total_profit_cost_gross=Decimal("120.00"),
        )
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
