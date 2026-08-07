import csv
import io
from datetime import UTC, datetime
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
from tests.unit.factories import create_base_application, create_base_provider


def _build_claim(
    *,
    claim_id: int,
    laa_reference: int,
    claim_type: ClaimType = ClaimType.FINAL_BILL,
    status: ClaimStatus = ClaimStatus.SUBMITTED,
    submission_date: datetime = datetime(2026, 1, 1, tzinfo=UTC),
    vat_zero: Decimal | None = Decimal("0.00"),
    net: Decimal | None = Decimal("100.00"),
    gross: Decimal | None = Decimal("120.00"),
) -> Claim:
    return Claim(
        claim_id=claim_id,
        laa_reference=laa_reference,
        claim_type_id=claim_type,
        status_id=status,
        submission_date=submission_date,
        total_profit_cost_vat_zero=vat_zero,
        total_profit_cost_net=net,
        total_profit_cost_gross=gross,
    )


def _build_use_case(
    claims: list[Claim] | None = None,
    office_lookup: dict[str, dict] | None = None,
    application_lookup_side_effect=None,
) -> GenerateClaimBacklogReportUseCase:
    claim_backlog_port = MagicMock()
    claim_backlog_port.get_open_claims.return_value = claims or []

    application_lookup_port = MagicMock()
    if application_lookup_side_effect is not None:
        application_lookup_port.get_application_by_laa_reference.side_effect = (
            application_lookup_side_effect
        )
    else:
        application = create_base_application(
            provider=create_base_provider(office_id="001")
        )
        application_lookup_port.get_application_by_laa_reference.return_value = (
            application
        )

    provider_details_port = MagicMock()
    provider_details_port.get_offices_by_codes.return_value = office_lookup or {
        "001": {"firmOfficeCode": "001", "officeName": "Office One"}
    }

    return GenerateClaimBacklogReportUseCase(
        claim_backlog_port=claim_backlog_port,
        application_lookup_port=application_lookup_port,
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
        use_case = _build_use_case(claims=[claim])

        result = use_case.execute()
        rows = _parse_csv(result)

        assert len(rows) == 1
        row = rows[0]
        assert row["Claims Reference Number"] == "10"
        assert row["Current Claims Status"] == ClaimStatus.SUBMITTED
        assert row["Office Name"] == "Office One"
        assert row["Office Account Number (Firm Office Code)"] == "001"
        assert row["Total 0% VAT claim value"] == "0.00"
        assert row["Net total claim value"] == "100.00"
        assert row["Gross total claim value"] == "120.00"
        assert row["Claim type (POA or final bill)"] == str(ClaimType.FINAL_BILL)

    def test_uses_raw_payment_on_account_claim_type_value(self):
        claim = _build_claim(
            claim_id=11,
            laa_reference=12345,
            claim_type=ClaimType.PAYMENT_ON_ACCOUNT,
        )
        use_case = _build_use_case(claims=[claim])

        result = use_case.execute()
        rows = _parse_csv(result)

        assert rows[0]["Claim type (POA or final bill)"] == str(
            ClaimType.PAYMENT_ON_ACCOUNT
        )

    def test_raises_error_when_application_not_found_for_claim(self):
        claim = _build_claim(claim_id=12, laa_reference=99999)

        use_case = _build_use_case(
            claims=[claim],
            application_lookup_side_effect=lambda _: None,
        )

        with pytest.raises(ReportGenerationError):
            use_case.execute()

    def test_raises_error_when_office_name_missing_for_office_code(self):
        claim = _build_claim(claim_id=13, laa_reference=12345)
        use_case = _build_use_case(
            claims=[claim],
            office_lookup={"001": {"firmOfficeCode": "001", "officeName": None}},
        )

        with pytest.raises(ReportGenerationError):
            use_case.execute()

    def test_raises_exception_when_offices_retrieval_fails(self):
        claim = _build_claim(claim_id=14, laa_reference=12345)

        claim_backlog_port = MagicMock()
        claim_backlog_port.get_open_claims.return_value = [claim]

        application_lookup_port = MagicMock()
        application_lookup_port.get_application_by_laa_reference.return_value = (
            create_base_application(provider=create_base_provider(office_id="001"))
        )

        provider_details_port = MagicMock()
        provider_details_port.get_offices_by_codes.side_effect = (
            ProviderDetailsRetrievalError("Provider API unavailable")
        )

        use_case = GenerateClaimBacklogReportUseCase(
            claim_backlog_port=claim_backlog_port,
            application_lookup_port=application_lookup_port,
            provider_details_port=provider_details_port,
        )

        with pytest.raises(ProviderDetailsRetrievalError):
            use_case.execute()

    def test_deduplicates_office_codes_before_calling_port(self):
        claim_1 = _build_claim(claim_id=15, laa_reference=100)
        claim_2 = _build_claim(claim_id=16, laa_reference=200)

        claim_backlog_port = MagicMock()
        claim_backlog_port.get_open_claims.return_value = [claim_1, claim_2]

        application_lookup_port = MagicMock()
        application_lookup_port.get_application_by_laa_reference.side_effect = [
            create_base_application(provider=create_base_provider(office_id="001")),
            create_base_application(provider=create_base_provider(office_id="001")),
        ]

        provider_details_port = MagicMock()
        provider_details_port.get_offices_by_codes.return_value = {
            "001": {"firmOfficeCode": "001", "officeName": "Office One"}
        }

        use_case = GenerateClaimBacklogReportUseCase(
            claim_backlog_port=claim_backlog_port,
            application_lookup_port=application_lookup_port,
            provider_details_port=provider_details_port,
        )

        use_case.execute()

        provider_details_port.get_offices_by_codes.assert_called_once_with(["001"])
