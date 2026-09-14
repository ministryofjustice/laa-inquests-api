from datetime import UTC, datetime
from decimal import Decimal

from app.domain.payment_extract import (
    bankers_round,
    build_poa_profit_cost_extract,
)
from app.models.claim.enums import InvoiceTypeCode, TaxCode


def _submission(year=2026, month=9, day=14) -> datetime:
    return datetime(year, month, day, 10, 30, tzinfo=UTC)


class TestBankersRound:
    def test_rounds_to_two_decimal_places(self):
        assert bankers_round(Decimal("1.234")) == Decimal("1.23")

    def test_rounds_half_to_even_down(self):
        assert bankers_round(Decimal("2.125")) == Decimal("2.12")

    def test_rounds_half_to_even_up(self):
        assert bankers_round(Decimal("2.135")) == Decimal("2.14")

    def test_rounds_half_to_even_when_preceding_digit_is_even(self):
        assert bankers_round(Decimal("2.145")) == Decimal("2.14")

    def test_rounds_non_tie_up(self):
        assert bankers_round(Decimal("2.126")) == Decimal("2.13")


class TestBuildPoaProfitCostExtract:
    def test_vat_claim_amount_is_eighty_percent_of_net_plus_vat(self):
        line = build_poa_profit_cost_extract(
            claim_id=7,
            sequence=1,
            submission_date=_submission(),
            net=Decimal("1000.00"),
            vat_zero=None,
        )

        # 1000 * 0.8 * 1.2 = 960.00
        assert line.invoice_amount == Decimal("960.00")
        assert line.tax_code == TaxCode.GB_VAT_20

    def test_zero_vat_claim_amount_is_eighty_percent_of_vat_zero(self):
        line = build_poa_profit_cost_extract(
            claim_id=7,
            sequence=1,
            submission_date=_submission(),
            net=None,
            vat_zero=Decimal("1000.00"),
        )

        # 1000 * 0.8 = 800.00, no VAT added
        assert line.invoice_amount == Decimal("800.00")
        assert line.tax_code == TaxCode.ZERO_VAT

    def test_amount_is_banker_rounded_to_two_decimal_places(self):
        line = build_poa_profit_cost_extract(
            claim_id=7,
            sequence=1,
            submission_date=_submission(),
            net=Decimal("333.33"),
            vat_zero=None,
        )

        # 333.33 * 0.8 * 1.2 = 319.9968 -> 320.00
        assert line.invoice_amount == Decimal("320.00")

    def test_invoice_number_pads_sequence_to_three_digits(self):
        line = build_poa_profit_cost_extract(
            claim_id=42,
            sequence=1,
            submission_date=_submission(),
            net=Decimal("1000.00"),
            vat_zero=None,
        )

        assert line.sequence_number == 1
        assert line.invoice_number == "42_001"

    def test_invoice_number_uses_given_sequence(self):
        line = build_poa_profit_cost_extract(
            claim_id=42,
            sequence=12,
            submission_date=_submission(),
            net=Decimal("1000.00"),
            vat_zero=None,
        )

        assert line.sequence_number == 12
        assert line.invoice_number == "42_012"

    def test_invoice_date_is_submission_date(self):
        line = build_poa_profit_cost_extract(
            claim_id=7,
            sequence=1,
            submission_date=_submission(2025, 1, 5),
            net=Decimal("1000.00"),
            vat_zero=None,
        )

        assert line.invoice_date == datetime(2025, 1, 5, tzinfo=UTC).date()

    def test_invoice_type_is_poa(self):
        line = build_poa_profit_cost_extract(
            claim_id=7,
            sequence=1,
            submission_date=_submission(),
            net=Decimal("1000.00"),
            vat_zero=None,
        )

        assert line.invoice_type == InvoiceTypeCode.POA
