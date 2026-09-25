from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from sqlmodel import Session, select

from app import api
from app.auth.rbac import Role
from app.models.application.index import Application
from app.models.claim.enums import ClaimType, InvoiceTypeCode, POAType, TaxCode
from app.models.claim.index import Claim, ClaimPaymentExtract
from app.routers.applications import get_provider_details_port
from app.use_cases.exceptions import ProviderDetailsRetrievalError
from tests.e2e.factories import create_claim_in_db
from tests.helpers.csv_helpers import parse_csv_fieldnames, parse_csv_rows

PAYMENT_EXTRACT_REPORT_HEADERS = [
    "DESCRIPTION",
    "INVOICE AMOUNT",
    "INVOICE DATE",
    "INVOICE TYPE",
    "INVOICE NUM",
    "VENDOR NAME",
    "VENDOR SITE CODE",
    "CASE REFERENCE",
    "CLIENT NAME",
    "TAX CODE",
    "MODEL NUMBER",
    "PROVIDER CASE REF NO",
]

URL = "/reports/payment-extract"
FINANCE_HEADERS = {"Authorization": f"Bearer {Role.FINANCE.value}"}


IN_RANGE = datetime(2025, 3, 15, 12, 0, tzinfo=UTC)
DEFAULT_PARAMS = {"from": "2025-03-01", "to": "2025-03-31"}


def _application(session: Session) -> Application:
    return session.exec(select(Application)).first()


def _claim(
    session: Session,
    claim_type: ClaimType = ClaimType.FINAL_BILL,
    poa_type: POAType | None = None,
) -> Claim:
    return create_claim_in_db(
        session,
        application_id=_application(session).application_id,
        claim_type=claim_type,
        poa_type=poa_type,
    )


def _add_extract(
    session: Session,
    claim: Claim,
    *,
    invoice_type: InvoiceTypeCode,
    sequence_number: int = 1,
    invoice_number: str | None = None,
    invoice_amount: str = "100.00",
    tax_code: TaxCode = TaxCode.GB_VAT_20,
    invoice_date: date = date(2025, 3, 10),
    created_at: datetime = IN_RANGE,
) -> ClaimPaymentExtract:
    extract = ClaimPaymentExtract(
        claim_id=claim.claim_id,
        sequence_number=sequence_number,
        invoice_number=invoice_number
        or f"{claim.claim_reference}_{sequence_number:03d}",
        invoice_amount=Decimal(invoice_amount),
        invoice_date=invoice_date,
        invoice_type=invoice_type,
        tax_code=tax_code,
        created_at=created_at,
    )
    session.add(extract)
    session.commit()
    session.refresh(extract)
    return extract


def _get(client, params: dict | None = None):
    return client.get(
        URL,
        params=DEFAULT_PARAMS if params is None else params,
        headers=FINANCE_HEADERS,
    )


def _single_row(client) -> dict[str, str]:
    response = _get(client)
    assert response.status_code == 200
    rows = parse_csv_rows(response.text)
    assert len(rows) == 1
    return rows[0]


def _override_provider_details_port(mock_port: MagicMock) -> None:
    api.dependency_overrides[get_provider_details_port] = lambda: mock_port


class TestGetPaymentExtractReport:
    """E2E tests for GET /reports/payment-extract."""

    def test_200_returns_csv_attachment_with_expected_headers(self, client):
        response = _get(client)

        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        assert "attachment" in response.headers["content-disposition"]
        assert (
            "payment_extract_2025-03-01_2025-03-31.csv"
            in response.headers["content-disposition"]
        )
        assert parse_csv_fieldnames(response.text) == PAYMENT_EXTRACT_REPORT_HEADERS

    def test_200_final_bill_fees_row_contains_expected_values(self, session, client):
        claim = _claim(session)
        _add_extract(
            session,
            claim,
            invoice_type=InvoiceTypeCode.FINAL_BILL_FEES,
            invoice_amount="1234.5",
            tax_code=TaxCode.GB_VAT_20,
            invoice_date=date(2025, 3, 10),
        )
        application = _application(session)

        row = _single_row(client)

        assert row == {
            "DESCRIPTION": "Profit costs",
            "INVOICE AMOUNT": "1234.50",
            "INVOICE DATE": "2025-03-10",
            "INVOICE TYPE": "Inq Final Bill (Fees)",
            "INVOICE NUM": f"{claim.claim_reference}_001",
            "VENDOR NAME": f"Firm {application.provider.firm_code}",
            "VENDOR SITE CODE": application.provider.office_id,
            "CASE REFERENCE": application.laa_reference,
            "CLIENT NAME": "",
            "TAX CODE": "GB VAT 20%",
            "MODEL NUMBER": "Profit costs",
            "PROVIDER CASE REF NO": "",
        }

    def test_200_final_bill_disbursement_row_is_expert_costs_disbursements(
        self, session, client
    ):
        claim = _claim(session)
        _add_extract(
            session,
            claim,
            invoice_type=InvoiceTypeCode.FINAL_BILL_DISBURSEMENT,
            tax_code=TaxCode.ZERO_VAT,
        )

        row = _single_row(client)

        assert row["DESCRIPTION"] == "Expert costs"
        assert row["MODEL NUMBER"] == "Disbursements"
        assert row["INVOICE TYPE"] == "Inq Final Bill (Disb)"
        assert row["TAX CODE"] == "ZERO VAT"

    def test_200_poa_profit_cost_row_is_profit_costs_80_percent(self, session, client):
        claim = _claim(session, ClaimType.PAYMENT_ON_ACCOUNT, POAType.PROFIT_COST)
        _add_extract(session, claim, invoice_type=InvoiceTypeCode.POA)

        row = _single_row(client)

        assert row["DESCRIPTION"] == "Profit costs (80%)"
        assert row["MODEL NUMBER"] == "Profit costs"
        assert row["INVOICE TYPE"] == "Inq POA"

    @pytest.mark.parametrize(
        "poa_type", [POAType.EXPERT_COST, POAType.NON_EXPERT_DISBURSEMENT]
    )
    def test_200_poa_disbursement_row_is_expert_costs_disbursements(
        self, session, client, poa_type
    ):
        claim = _claim(session, ClaimType.PAYMENT_ON_ACCOUNT, poa_type)
        _add_extract(session, claim, invoice_type=InvoiceTypeCode.POA)

        row = _single_row(client)

        assert row["DESCRIPTION"] == "Expert costs"
        assert row["MODEL NUMBER"] == "Disbursements"

    @pytest.mark.parametrize(
        ("poa_type", "description", "model_number"),
        [
            (POAType.PROFIT_COST, "Profit costs (80%)", "Profit costs"),
            (POAType.EXPERT_COST, "Expert costs", "Disbursements"),
        ],
    )
    def test_200_recouped_row_takes_type_from_original_poa_line(
        self, session, client, poa_type, description, model_number
    ):
        poa_claim = _claim(session, ClaimType.PAYMENT_ON_ACCOUNT, poa_type)
        original = _add_extract(
            session,
            poa_claim,
            invoice_type=InvoiceTypeCode.POA,
            created_at=datetime(2025, 1, 1, tzinfo=UTC),
        )
        final_bill_claim = _claim(session)
        _add_extract(
            session,
            final_bill_claim,
            invoice_type=InvoiceTypeCode.RECOUPED,
            invoice_number=f"{original.invoice_number}-R",
            invoice_amount="-100.00",
        )

        row = _single_row(client)

        assert row["INVOICE TYPE"] == "Inq Recouped POA"
        assert row["INVOICE NUM"] == f"{original.invoice_number}-R"
        assert row["INVOICE AMOUNT"] == "-100.00"
        assert row["DESCRIPTION"] == description
        assert row["MODEL NUMBER"] == model_number

    def test_200_nil_bill_zero_amount_row_is_included(self, session, client):
        claim = _claim(session)
        _add_extract(
            session,
            claim,
            invoice_type=InvoiceTypeCode.FINAL_BILL_FEES,
            invoice_amount="0.00",
            tax_code=TaxCode.ZERO_VAT,
        )

        row = _single_row(client)

        assert row["INVOICE AMOUNT"] == "0.00"
        assert row["DESCRIPTION"] == "Profit costs"

    def test_200_filters_rows_on_created_at_with_inclusive_dates(self, session, client):
        claim = _claim(session)
        created_ats = {
            "before": datetime(2025, 2, 28, 23, 59, 59, tzinfo=UTC),
            "start": datetime(2025, 3, 1, 0, 0, tzinfo=UTC),
            "end": datetime(2025, 3, 31, 23, 59, 59, tzinfo=UTC),
            "after": datetime(2025, 4, 1, 0, 0, tzinfo=UTC),
        }
        invoice_numbers = {}
        for sequence, (label, created_at) in enumerate(created_ats.items(), start=1):
            extract = _add_extract(
                session,
                claim,
                invoice_type=InvoiceTypeCode.FINAL_BILL_FEES,
                sequence_number=sequence,
                created_at=created_at,
            )
            invoice_numbers[label] = extract.invoice_number

        response = _get(client)

        invoice_nums = [row["INVOICE NUM"] for row in parse_csv_rows(response.text)]
        assert invoice_nums == [invoice_numbers["start"], invoice_numbers["end"]]

    def test_200_rows_are_ordered_by_created_at(self, session, client):
        claim = _claim(session)
        later = _add_extract(
            session,
            claim,
            invoice_type=InvoiceTypeCode.FINAL_BILL_FEES,
            sequence_number=1,
            created_at=datetime(2025, 3, 20, tzinfo=UTC),
        )
        earlier = _add_extract(
            session,
            claim,
            invoice_type=InvoiceTypeCode.FINAL_BILL_DISBURSEMENT,
            sequence_number=2,
            created_at=datetime(2025, 3, 5, tzinfo=UTC),
        )

        response = _get(client)

        invoice_nums = [row["INVOICE NUM"] for row in parse_csv_rows(response.text)]
        assert invoice_nums == [earlier.invoice_number, later.invoice_number]

    def test_200_returns_headers_only_when_no_rows_in_range(self, session, client):
        claim = _claim(session)
        _add_extract(
            session,
            claim,
            invoice_type=InvoiceTypeCode.FINAL_BILL_FEES,
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
        )

        response = _get(client)

        assert response.status_code == 200
        assert parse_csv_fieldnames(response.text) == PAYMENT_EXTRACT_REPORT_HEADERS
        assert parse_csv_rows(response.text) == []

    @pytest.mark.parametrize(
        "params",
        [
            {"to": "2025-03-31"},
            {"from": "2025-03-01"},
            {},
        ],
    )
    def test_422_when_date_params_missing(self, client, params):
        response = _get(client, params)

        assert response.status_code == 422

    @pytest.mark.parametrize(
        "params",
        [
            {"from": "not-a-date", "to": "2025-03-31"},
            {"from": "2025-03-01", "to": "31/03/2025"},
        ],
    )
    def test_422_when_date_params_invalid(self, client, params):
        response = _get(client, params)

        assert response.status_code == 422

    def test_422_when_from_is_after_to(self, client):
        response = _get(client, {"from": "2025-04-01", "to": "2025-03-31"})

        assert response.status_code == 422

    def test_500_when_firm_name_missing(self, session, client):
        claim = _claim(session)
        _add_extract(session, claim, invoice_type=InvoiceTypeCode.FINAL_BILL_FEES)
        mock_port = MagicMock()
        mock_port.get_firms_by_ids.return_value = []
        _override_provider_details_port(mock_port)

        response = _get(client)

        assert response.status_code == 500
        assert "text/csv" not in response.headers["content-type"]

    def test_500_when_provider_details_retrieval_fails(self, session, client):
        claim = _claim(session)
        _add_extract(session, claim, invoice_type=InvoiceTypeCode.FINAL_BILL_FEES)
        mock_port = MagicMock()
        mock_port.get_firms_by_ids.side_effect = ProviderDetailsRetrievalError()
        _override_provider_details_port(mock_port)

        response = _get(client)

        assert response.status_code == 500
        assert "text/csv" not in response.headers["content-type"]

    def test_500_when_poa_line_has_no_poa_type(self, session, client):
        claim = _claim(session, ClaimType.PAYMENT_ON_ACCOUNT, poa_type=None)
        _add_extract(session, claim, invoice_type=InvoiceTypeCode.POA)

        response = _get(client)

        assert response.status_code == 500
        assert "text/csv" not in response.headers["content-type"]

    def test_500_when_recouped_line_has_no_original_poa_line(self, session, client):
        claim = _claim(session)
        _add_extract(
            session,
            claim,
            invoice_type=InvoiceTypeCode.RECOUPED,
            invoice_number="INQC-NONE-NONE_001-R",
            invoice_amount="-100.00",
        )

        response = _get(client)

        assert response.status_code == 500
        assert "text/csv" not in response.headers["content-type"]


class TestGetPaymentExtractReportAuth:
    """Authentication tests for GET /reports/payment-extract."""

    @pytest.mark.parametrize("role", [Role.FINANCE, Role.ASSURANCE])
    def test_200_returns_ok_for_payment_report_roles(self, client, role):
        response = client.get(
            URL,
            params=DEFAULT_PARAMS,
            headers={"Authorization": f"Bearer {role.value}"},
        )

        assert response.status_code == 200
