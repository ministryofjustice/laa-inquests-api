from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.domain.payment_extract import (
    bankers_round,
    build_final_bill_fee_lines,
    build_poa_profit_cost_extract,
    build_recoupment_line,
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


class TestBuildFinalBillFeeLines:
    def test_gross_only_produces_single_twenty_percent_line(self):
        lines = build_final_bill_fee_lines(
            claim_id=7,
            submission_date=_submission(),
            gross=Decimal("420.00"),
            vat_zero=None,
        )

        assert len(lines) == 1
        assert lines[0].invoice_amount == Decimal("420.00")
        assert lines[0].tax_code == TaxCode.GB_VAT_20
        assert lines[0].invoice_type == InvoiceTypeCode.FINAL_BILL_FEES
        assert lines[0].sequence_number == 1
        assert lines[0].invoice_number == "7_001"

    def test_vat_zero_only_produces_single_zero_vat_line(self):
        lines = build_final_bill_fee_lines(
            claim_id=7,
            submission_date=_submission(),
            gross=None,
            vat_zero=Decimal("200.00"),
        )

        assert len(lines) == 1
        assert lines[0].invoice_amount == Decimal("200.00")
        assert lines[0].tax_code == TaxCode.ZERO_VAT
        assert lines[0].invoice_type == InvoiceTypeCode.FINAL_BILL_FEES
        assert lines[0].sequence_number == 1
        assert lines[0].invoice_number == "7_001"

    def test_mixed_vat_splits_into_two_lines(self):
        lines = build_final_bill_fee_lines(
            claim_id=7,
            submission_date=_submission(),
            gross=Decimal("420.00"),
            vat_zero=Decimal("200.00"),
        )

        assert len(lines) == 2

        # 20% line comes first: gross - vat_zero = 420 - 200 = 220
        assert lines[0].invoice_amount == Decimal("220.00")
        assert lines[0].tax_code == TaxCode.GB_VAT_20
        assert lines[0].sequence_number == 1
        assert lines[0].invoice_number == "7_001"

        # 0% line second: vat_zero = 200
        assert lines[1].invoice_amount == Decimal("200.00")
        assert lines[1].tax_code == TaxCode.ZERO_VAT
        assert lines[1].sequence_number == 2
        assert lines[1].invoice_number == "7_002"

    def test_amounts_are_banker_rounded_to_two_decimal_places(self):
        lines = build_final_bill_fee_lines(
            claim_id=7,
            submission_date=_submission(),
            gross=Decimal("100.125"),
            vat_zero=Decimal("50.005"),
        )

        # 20% line = 100.125 - 50.005 = 50.12 -> 50.12
        assert lines[0].invoice_amount == Decimal("50.12")
        # 0% line = 50.005 -> 50.00
        assert lines[1].invoice_amount == Decimal("50.00")

    def test_lines_start_from_given_sequence(self):
        lines = build_final_bill_fee_lines(
            claim_id=7,
            submission_date=_submission(),
            gross=Decimal("420.00"),
            vat_zero=Decimal("200.00"),
            start_sequence=5,
        )

        assert lines[0].sequence_number == 5
        assert lines[0].invoice_number == "7_005"
        assert lines[1].sequence_number == 6
        assert lines[1].invoice_number == "7_006"

    def test_invoice_date_is_submission_date(self):
        lines = build_final_bill_fee_lines(
            claim_id=7,
            submission_date=_submission(2025, 1, 5),
            gross=Decimal("420.00"),
            vat_zero=None,
        )

        assert lines[0].invoice_date == datetime(2025, 1, 5, tzinfo=UTC).date()

    def test_raises_when_no_amounts_provided(self):
        with pytest.raises(ValueError):
            build_final_bill_fee_lines(
                claim_id=7,
                submission_date=_submission(),
                gross=None,
                vat_zero=None,
            )


class TestBuildRecoupmentLine:
    def test_amount_is_negative_of_original(self):
        line = build_recoupment_line(
            claim_id=7,
            sequence=3,
            original_amount=Decimal("960.00"),
            tax_code=TaxCode.GB_VAT_20,
            decision_date=_submission().date(),
        )

        assert line.invoice_amount == Decimal("-960.00")

    def test_preserves_original_tax_code(self):
        line = build_recoupment_line(
            claim_id=7,
            sequence=3,
            original_amount=Decimal("800.00"),
            tax_code=TaxCode.ZERO_VAT,
            decision_date=_submission().date(),
        )

        assert line.tax_code == TaxCode.ZERO_VAT

    def test_invoice_type_is_recouped(self):
        line = build_recoupment_line(
            claim_id=7,
            sequence=3,
            original_amount=Decimal("800.00"),
            tax_code=TaxCode.ZERO_VAT,
            decision_date=_submission().date(),
        )

        assert line.invoice_type == InvoiceTypeCode.RECOUPED

    def test_invoice_number_uses_final_bill_prefix_and_sequence(self):
        line = build_recoupment_line(
            claim_id=42,
            sequence=3,
            original_amount=Decimal("800.00"),
            tax_code=TaxCode.ZERO_VAT,
            decision_date=_submission().date(),
        )

        assert line.sequence_number == 3
        assert line.invoice_number == "42_003"

    def test_invoice_date_is_decision_date(self):
        decision_date = _submission(2025, 3, 9).date()
        line = build_recoupment_line(
            claim_id=7,
            sequence=3,
            original_amount=Decimal("800.00"),
            tax_code=TaxCode.ZERO_VAT,
            decision_date=decision_date,
        )

        assert line.invoice_date == decision_date
