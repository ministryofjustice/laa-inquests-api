import re
from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from sqlmodel import Session, select

from app import api
from app.auth.rbac import Role
from app.models.application.enums import PublicBodyId
from app.models.application.index import (
    Application,
    ApplicationPublicBody,
    Deceased,
)
from app.models.claim.enums import (
    ClaimDecisionStatus,
    ClaimType,
    InvoiceTypeCode,
    TaxCode,
)
from app.models.claim.index import Claim, ClaimDecision, ClaimPaymentExtract
from app.routers.reports import get_ogd_costs_report_port
from tests.e2e.factories import create_claim_in_db
from tests.helpers.csv_helpers import parse_csv_fieldnames, parse_csv_rows

OGD_COSTS_REPORT_HEADERS = [
    "Claim Decision Date",
    "Claim Decision",
    "Bill Type",
    "Public Body(ies)",
    "Legal Aid Reference",
    "Invoice Number",
    "Invoice Amount",
    "Tax Code",
    "Name of Deceased",
    "Date of Death",
]

URL = "/reports/ogd-costs"
ASSURANCE_HEADERS = {"Authorization": f"Bearer {Role.ASSURANCE.value}"}

DECIDED_IN_RANGE = datetime(2025, 3, 15, 12, 0, tzinfo=UTC)
DEFAULT_PARAMS = {"from": "2025-03-01", "to": "2025-03-31"}
FILENAME_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2} - Report - IDDS OGD Costs - OFFICIAL-SENSITIVE - LAA Use Only\.csv$"
)


def _application(session: Session) -> Application:
    return session.exec(select(Application)).first()


def _claim(session: Session, claim_type: ClaimType = ClaimType.FINAL_BILL) -> Claim:
    return create_claim_in_db(
        session,
        application_id=_application(session).application_id,
        claim_type=claim_type,
    )


def _add_decision(
    session: Session,
    claim: Claim,
    decided_at: datetime = DECIDED_IN_RANGE,
    decision: ClaimDecisionStatus = ClaimDecisionStatus.PAY_IN_FULL,
) -> ClaimDecision:
    claim_decision = ClaimDecision(
        claim_id=claim.claim_id, decision=decision, created_at=decided_at
    )
    session.add(claim_decision)
    session.commit()
    return claim_decision


def _add_extract(
    session: Session,
    claim: Claim,
    *,
    invoice_type: InvoiceTypeCode = InvoiceTypeCode.FINAL_BILL_FEES,
    sequence_number: int = 1,
    invoice_number: str | None = None,
    invoice_amount: str = "100.00",
    tax_code: TaxCode = TaxCode.GB_VAT_20,
    invoice_date: date = date(2025, 1, 5),
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
    )
    session.add(extract)
    session.commit()
    return extract


def _paid_claim(
    session: Session,
    claim_type: ClaimType = ClaimType.FINAL_BILL,
    decided_at: datetime = DECIDED_IN_RANGE,
    **extract_kwargs,
) -> tuple[Claim, ClaimPaymentExtract]:
    claim = _claim(session, claim_type)
    _add_decision(session, claim, decided_at)
    return claim, _add_extract(session, claim, **extract_kwargs)


def _set_public_bodies(session: Session, bodies: list[PublicBodyId]) -> None:
    application = _application(session)
    for existing in session.exec(select(ApplicationPublicBody)).all():
        session.delete(existing)
    session.commit()
    for body in bodies:
        session.add(
            ApplicationPublicBody(
                application_id=application.application_id, public_body_id=body
            )
        )
    session.commit()


def _set_deceased(session: Session, **fields) -> None:
    deceased = session.exec(select(Deceased)).first()
    for name, value in fields.items():
        setattr(deceased, name, value)
    session.add(deceased)
    session.commit()


def _get(client, params: dict | None = None):
    return client.get(
        URL,
        params=DEFAULT_PARAMS if params is None else params,
        headers=ASSURANCE_HEADERS,
    )


def _rows(client, params: dict | None = None) -> list[dict[str, str]]:
    response = _get(client, params)
    assert response.status_code == 200
    return parse_csv_rows(response.text)


def _single_row(client) -> dict[str, str]:
    rows = _rows(client)
    assert len(rows) == 1
    return rows[0]


class TestGetOgdCostsReport:
    """E2E tests for GET /reports/ogd-costs."""

    def test_200_returns_csv_attachment_with_expected_headers_in_order(self, client):
        response = _get(client)

        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        assert "attachment" in response.headers["content-disposition"]
        assert parse_csv_fieldnames(response.text) == OGD_COSTS_REPORT_HEADERS

    def test_200_filename_follows_laa_pattern(self, client):
        response = _get(client)

        disposition = response.headers["content-disposition"]
        filename = disposition.split("filename=", 1)[1].strip('"')
        assert FILENAME_PATTERN.match(filename)

    def test_200_returns_headers_only_when_no_records_in_range(self, session, client):
        _paid_claim(session, decided_at=datetime(2024, 1, 1, tzinfo=UTC))

        response = _get(client)

        assert response.status_code == 200
        assert parse_csv_fieldnames(response.text) == OGD_COSTS_REPORT_HEADERS
        assert parse_csv_rows(response.text) == []

    def test_200_row_contains_all_required_fields(self, session, client):
        _set_public_bodies(session, [PublicBodyId.HOME_OFFICE])
        _set_deceased(
            session,
            deceased_first_name="Jane",
            deceased_last_name="Doe",
            deceased_date_of_death="2025-01-02",
        )
        claim, _ = _paid_claim(
            session,
            invoice_amount="1234.50",
            tax_code=TaxCode.ZERO_VAT,
        )

        row = _single_row(client)

        assert row == {
            "Claim Decision Date": "2025-03-15",
            "Claim Decision": "Pay in full",
            "Bill Type": "Final bill",
            "Public Body(ies)": "Home Office",
            "Legal Aid Reference": "INQ-123-456",
            "Invoice Number": f"{claim.claim_reference}_001",
            "Invoice Amount": "1234.50",
            "Tax Code": "ZERO VAT",
            "Name of Deceased": "Jane Doe",
            "Date of Death": "2025-01-02",
        }

    @pytest.mark.parametrize(
        ("claim_type", "invoice_type", "expected_bill_type"),
        [
            (ClaimType.PAYMENT_ON_ACCOUNT, InvoiceTypeCode.POA, "POA"),
            (ClaimType.FINAL_BILL, InvoiceTypeCode.FINAL_BILL_FEES, "Final bill"),
            (ClaimType.NIL_BILL, InvoiceTypeCode.FINAL_BILL_FEES, "Nil bill"),
        ],
    )
    def test_200_includes_poa_final_bill_and_nil_bill_rows(
        self, session, client, claim_type, invoice_type, expected_bill_type
    ):
        _paid_claim(session, claim_type, invoice_type=invoice_type)

        row = _single_row(client)

        assert row["Bill Type"] == expected_bill_type

    def test_200_nil_bill_zero_amount_row_is_included(self, session, client):
        _paid_claim(
            session,
            ClaimType.NIL_BILL,
            invoice_amount="0.00",
            tax_code=TaxCode.ZERO_VAT,
        )

        row = _single_row(client)

        assert row["Invoice Amount"] == "0.00"
        assert row["Bill Type"] == "Nil bill"

    def test_200_recoupment_row_is_negative_with_bill_type_poa(self, session, client):
        _, poa_line = _paid_claim(
            session,
            ClaimType.PAYMENT_ON_ACCOUNT,
            decided_at=datetime(2025, 2, 10, tzinfo=UTC),
            invoice_type=InvoiceTypeCode.POA,
        )
        final_bill = _claim(session)
        _add_decision(session, final_bill, DECIDED_IN_RANGE)
        _add_extract(
            session,
            final_bill,
            invoice_type=InvoiceTypeCode.RECOUPED,
            invoice_number=f"{poa_line.invoice_number}-R",
            invoice_amount="-100.00",
        )

        row = _single_row(client)

        assert row["Invoice Number"] == f"{poa_line.invoice_number}-R"
        assert row["Invoice Amount"] == "-100.00"
        assert row["Bill Type"] == "POA"

    def test_200_recoupment_uses_final_bill_decision_date(self, session, client):
        _, poa_line = _paid_claim(
            session,
            ClaimType.PAYMENT_ON_ACCOUNT,
            decided_at=datetime(2025, 2, 10, tzinfo=UTC),
            invoice_type=InvoiceTypeCode.POA,
        )
        final_bill = _claim(session)
        _add_decision(session, final_bill, datetime(2025, 3, 20, 9, 0, tzinfo=UTC))
        _add_extract(
            session,
            final_bill,
            invoice_type=InvoiceTypeCode.RECOUPED,
            invoice_number=f"{poa_line.invoice_number}-R",
            invoice_amount="-100.00",
        )

        row = _single_row(client)

        assert row["Claim Decision Date"] == "2025-03-20"

    def test_200_one_row_per_invoice_line_without_aggregation(self, session, client):
        claim = _claim(session)
        _add_decision(session, claim)
        _add_extract(
            session,
            claim,
            invoice_type=InvoiceTypeCode.FINAL_BILL_FEES,
            sequence_number=1,
            invoice_amount="100.00",
        )
        _add_extract(
            session,
            claim,
            invoice_type=InvoiceTypeCode.FINAL_BILL_DISBURSEMENT,
            sequence_number=2,
            invoice_amount="50.00",
        )
        _add_extract(
            session,
            claim,
            invoice_type=InvoiceTypeCode.FINAL_BILL_DISBURSEMENT,
            sequence_number=3,
            invoice_amount="25.00",
            tax_code=TaxCode.ZERO_VAT,
        )

        rows = _rows(client)

        assert [row["Invoice Amount"] for row in rows] == ["100.00", "50.00", "25.00"]
        assert len({row["Invoice Number"] for row in rows}) == 3

    def test_200_single_public_body_is_listed(self, session, client):
        _set_public_bodies(session, [PublicBodyId.MINISTRY_OF_JUSTICE])
        _paid_claim(session)

        assert _single_row(client)["Public Body(ies)"] == "Ministry of Justice"

    def test_200_multiple_public_bodies_are_separated_by_semicolon_and_space(
        self, session, client
    ):
        _set_public_bodies(
            session,
            [PublicBodyId.MINISTRY_OF_JUSTICE, PublicBodyId.HOME_OFFICE],
        )
        _paid_claim(session)

        assert (
            _single_row(client)["Public Body(ies)"]
            == "Home Office; Ministry of Justice"
        )

    def test_200_filters_on_claim_decision_date_with_inclusive_utc_dates(
        self, session, client
    ):
        decided_ats = {
            "before": datetime(2025, 2, 28, 23, 59, 59, tzinfo=UTC),
            "start": datetime(2025, 3, 1, 0, 0, tzinfo=UTC),
            "end": datetime(2025, 3, 31, 23, 59, 59, tzinfo=UTC),
            "after": datetime(2025, 4, 1, 0, 0, tzinfo=UTC),
        }
        invoice_numbers = {}
        for key, decided_at in decided_ats.items():
            claim = _claim(session)
            _add_decision(session, claim, decided_at)
            # Invoice date is deliberately always outside the range.
            _add_extract(session, claim, invoice_date=date(2024, 6, 1))
            invoice_numbers[key] = f"{claim.claim_reference}_001"

        rows = _rows(client)

        assert {row["Invoice Number"] for row in rows} == {
            invoice_numbers["start"],
            invoice_numbers["end"],
        }

    def test_200_rows_without_a_pay_in_full_decision_are_excluded(
        self, session, client
    ):
        claim = _claim(session)
        _add_decision(session, claim, decision=ClaimDecisionStatus.REJECT)
        _add_extract(session, claim)

        assert _rows(client) == []

    def test_200_deceased_name_starting_with_formula_character_is_neutralised(
        self, session, client
    ):
        _set_deceased(session, deceased_first_name="=cmd", deceased_last_name="Doe")
        _paid_claim(session)

        assert _single_row(client)["Name of Deceased"] == "'=cmd Doe"

    def test_500_when_date_of_death_is_not_an_iso_date_and_no_csv_is_returned(
        self, session, client
    ):
        _set_deceased(session, deceased_date_of_death="01-01-2026")
        _paid_claim(session)

        response = _get(client)

        assert response.status_code == 500
        assert "text/csv" not in response.headers["content-type"]

    def test_200_all_dates_are_formatted_yyyy_mm_dd(self, session, client):
        _set_deceased(session, deceased_date_of_death="2025-01-02")
        _paid_claim(session)

        row = _single_row(client)

        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", row["Claim Decision Date"])
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", row["Date of Death"])

    def test_200_supports_at_least_2000_records(self, session, client):
        claim = _claim(session)
        _add_decision(session, claim)
        session.add_all(
            ClaimPaymentExtract(
                claim_id=claim.claim_id,
                sequence_number=sequence,
                invoice_number=f"{claim.claim_reference}_{sequence:04d}",
                invoice_amount=Decimal("10.00"),
                invoice_date=date(2025, 3, 10),
                invoice_type=InvoiceTypeCode.FINAL_BILL_DISBURSEMENT,
                tax_code=TaxCode.GB_VAT_20,
            )
            for sequence in range(1, 2001)
        )
        session.commit()

        assert len(_rows(client)) == 2000

    @pytest.mark.parametrize(
        "params",
        [{"to": "2025-03-31"}, {"from": "2025-03-01"}, {}],
    )
    def test_422_when_date_params_missing(self, client, params):
        assert _get(client, params).status_code == 422

    @pytest.mark.parametrize(
        "params",
        [
            {"from": "not-a-date", "to": "2025-03-31"},
            {"from": "2025-03-01", "to": "31/03/2025"},
        ],
    )
    def test_422_when_date_params_invalid(self, client, params):
        assert _get(client, params).status_code == 422

    def test_422_when_from_is_after_to(self, client):
        response = _get(client, {"from": "2025-04-01", "to": "2025-03-31"})

        assert response.status_code == 422

    def test_422_when_date_range_exceeds_90_days_and_no_csv_is_returned(
        self, session, client
    ):
        _paid_claim(session)

        response = _get(client, {"from": "2025-01-01", "to": "2025-04-01"})

        assert response.status_code == 422
        assert "90 days" in response.json()["detail"]
        assert "text/csv" not in response.headers["content-type"]

    def test_200_when_date_range_is_exactly_90_days(self, client):
        response = _get(client, {"from": "2025-01-01", "to": "2025-03-31"})

        assert response.status_code == 200

    def test_500_when_case_has_no_public_bodies_and_no_csv_is_returned(
        self, session, client
    ):
        _set_public_bodies(session, [])
        _paid_claim(session)

        response = _get(client)

        assert response.status_code == 500
        assert "text/csv" not in response.headers["content-type"]

    def test_500_when_generation_fails_part_way_and_no_csv_is_returned(self, client):
        def failing_lines(*_args):
            raise RuntimeError("database connection lost")
            yield  # pragma: no cover

        port = MagicMock()
        port.get_ogd_public_bodies_by_application.return_value = {}
        port.iter_ogd_costs_report_lines.side_effect = failing_lines
        api.dependency_overrides[get_ogd_costs_report_port] = lambda: port

        response = _get(client)

        assert response.status_code == 500
        assert "text/csv" not in response.headers["content-type"]
        assert "content-disposition" not in response.headers
        assert OGD_COSTS_REPORT_HEADERS[0] not in response.text


class TestGetOgdCostsReportAuth:
    """Authentication tests for GET /reports/ogd-costs."""

    def test_200_returns_ok_for_assurance_role(self, client):
        response = client.get(URL, params=DEFAULT_PARAMS, headers=ASSURANCE_HEADERS)

        assert response.status_code == 200
