from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.domain.ogd_costs_report import (
    InvalidOgdCostsRecordError,
    OgdCostsReportSourceLine,
    build_ogd_costs_row,
    format_public_bodies,
    resolve_bill_type,
)
from app.models.application.enums import PublicBodyId
from app.models.claim.enums import (
    ClaimDecisionStatus,
    ClaimType,
    InvoiceTypeCode,
    TaxCode,
)


def _line(**overrides) -> OgdCostsReportSourceLine:
    defaults = {
        "application_id": 1,
        "claim_decision_date": datetime(2025, 3, 15, 12, 0, tzinfo=UTC),
        "claim_decision": ClaimDecisionStatus.PAY_IN_FULL,
        "invoice_type": InvoiceTypeCode.FINAL_BILL_FEES,
        "claim_type": ClaimType.FINAL_BILL,
        "laa_reference": "INQ-123-456",
        "invoice_number": "INQC-AAAA-BBBB_001",
        "invoice_amount": Decimal("120.5"),
        "tax_code": TaxCode.GB_VAT_20,
        "deceased_first_name": "Jane",
        "deceased_last_name": "Doe",
        "deceased_date_of_death": "2025-01-02",
    }
    return OgdCostsReportSourceLine(**(defaults | overrides))


class TestFormatPublicBodies:
    def test_single_body_has_no_delimiter(self):
        assert format_public_bodies([PublicBodyId.HOME_OFFICE]) == "Home Office"

    def test_many_bodies_are_sorted_and_joined_with_semicolon_and_space(self):
        bodies = [
            PublicBodyId.MINISTRY_OF_JUSTICE,
            PublicBodyId.HOME_OFFICE,
            PublicBodyId.CABINET_OFFICE,
        ]

        assert (
            format_public_bodies(bodies)
            == "Cabinet Office; Home Office; Ministry of Justice"
        )


class TestResolveBillType:
    @pytest.mark.parametrize(
        ("claim_type", "invoice_type", "expected"),
        [
            (ClaimType.PAYMENT_ON_ACCOUNT, InvoiceTypeCode.POA, "POA"),
            (ClaimType.FINAL_BILL, InvoiceTypeCode.FINAL_BILL_FEES, "Final bill"),
            (
                ClaimType.FINAL_BILL,
                InvoiceTypeCode.FINAL_BILL_DISBURSEMENT,
                "Final bill",
            ),
            (ClaimType.NIL_BILL, InvoiceTypeCode.FINAL_BILL_FEES, "Nil bill"),
        ],
    )
    def test_maps_claim_type_to_bill_type(self, claim_type, invoice_type, expected):
        line = _line(claim_type=claim_type, invoice_type=invoice_type)

        assert resolve_bill_type(line) == expected

    @pytest.mark.parametrize("claim_type", [ClaimType.FINAL_BILL, ClaimType.NIL_BILL])
    def test_recouped_line_is_a_poa_even_though_stored_against_the_final_bill(
        self, claim_type
    ):
        line = _line(claim_type=claim_type, invoice_type=InvoiceTypeCode.RECOUPED)

        assert resolve_bill_type(line) == "POA"


class TestBuildOgdCostsRow:
    def test_builds_row_in_header_order(self):
        row = build_ogd_costs_row(
            _line(invoice_amount=Decimal("-120.5"), tax_code=TaxCode.ZERO_VAT),
            [PublicBodyId.HOME_OFFICE, PublicBodyId.MINISTRY_OF_JUSTICE],
        )

        assert row == [
            "2025-03-15",
            "Pay in full",
            "Final bill",
            "Home Office; Ministry of Justice",
            "INQ-123-456",
            "INQC-AAAA-BBBB_001",
            "-120.50",
            "ZERO VAT",
            "Jane Doe",
            "2025-01-02",
        ]

    def test_naive_decision_datetime_is_treated_as_utc(self):
        # Naive on purpose: the DB can return naive datetimes (e.g. SQLite).
        line = _line(
            claim_decision_date=datetime(2025, 3, 15, 23, 59, 59)  # noqa: DTZ001
        )

        assert build_ogd_costs_row(line, [PublicBodyId.HOME_OFFICE])[0] == "2025-03-15"

    def test_aware_non_utc_decision_datetime_is_converted_to_utc_date(self):
        plus_two = timezone(timedelta(hours=2))
        line = _line(claim_decision_date=datetime(2025, 3, 16, 0, 30, tzinfo=plus_two))

        assert build_ogd_costs_row(line, [PublicBodyId.HOME_OFFICE])[0] == "2025-03-15"

    def test_deceased_name_is_formula_neutralised_but_amount_is_not(self):
        line = _line(deceased_first_name="=cmd", invoice_amount=Decimal(-5))

        row = build_ogd_costs_row(line, [PublicBodyId.HOME_OFFICE])

        assert row[8] == "'=cmd Doe"
        assert row[6] == "-5.00"

    def test_non_iso_date_of_death_raises(self):
        line = _line(deceased_date_of_death="01-01-2026")

        with pytest.raises(InvalidOgdCostsRecordError):
            build_ogd_costs_row(line, [PublicBodyId.HOME_OFFICE])

    def test_unsupported_claim_decision_raises(self):
        line = _line(claim_decision=ClaimDecisionStatus.REJECT)

        with pytest.raises(InvalidOgdCostsRecordError):
            build_ogd_costs_row(line, [PublicBodyId.HOME_OFFICE])
