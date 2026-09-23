from datetime import UTC, datetime
from decimal import Decimal

from app.domain.payment_extract import (
    RecoupmentSourceLine,
    bankers_round,
    build_final_bill_disbursement_extract,
    build_final_bill_fees_extract,
    build_final_bill_nil_fees_extract,
    build_poa_disbursement_extract,
    build_poa_profit_cost_extract,
    build_recoupment_extract,
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
            claim_reference="INQC-WCLA-YHMY",
            sequence=1,
            submission_date=_submission(),
            net=Decimal("1000.00"),
            vat_zero_amount=None,
        )

        # 1000 * 0.8 * 1.2 = 960.00
        assert line.invoice_amount == Decimal("960.00")
        assert line.tax_code == TaxCode.GB_VAT_20

    def test_zero_vat_claim_amount_is_eighty_percent_of_vat_zero(self):
        line = build_poa_profit_cost_extract(
            claim_reference="INQC-WCLA-YHMY",
            sequence=1,
            submission_date=_submission(),
            net=None,
            vat_zero_amount=Decimal("1000.00"),
        )

        # 1000 * 0.8 = 800.00, no VAT added
        assert line.invoice_amount == Decimal("800.00")
        assert line.tax_code == TaxCode.ZERO_VAT

    def test_amount_is_banker_rounded_to_two_decimal_places(self):
        line = build_poa_profit_cost_extract(
            claim_reference="INQC-WCLA-YHMY",
            sequence=1,
            submission_date=_submission(),
            net=Decimal("333.33"),
            vat_zero_amount=None,
        )

        # 333.33 * 0.8 * 1.2 = 319.9968 -> 320.00
        assert line.invoice_amount == Decimal("320.00")

    def test_invoice_number_pads_sequence_to_three_digits(self):
        line = build_poa_profit_cost_extract(
            claim_reference="INQC-DEMO-XZ12",
            sequence=1,
            submission_date=_submission(),
            net=Decimal("1000.00"),
            vat_zero_amount=None,
        )

        assert line.sequence_number == 1
        assert line.invoice_number == "INQC-DEMO-XZ12_001"

    def test_invoice_number_uses_given_sequence(self):
        line = build_poa_profit_cost_extract(
            claim_reference="INQC-DEMO-XZ12",
            sequence=12,
            submission_date=_submission(),
            net=Decimal("1000.00"),
            vat_zero_amount=None,
        )

        assert line.sequence_number == 12
        assert line.invoice_number == "INQC-DEMO-XZ12_012"

    def test_invoice_date_is_submission_date(self):
        line = build_poa_profit_cost_extract(
            claim_reference="INQC-WCLA-YHMY",
            sequence=1,
            submission_date=_submission(2025, 1, 5),
            net=Decimal("1000.00"),
            vat_zero_amount=None,
        )

        assert line.invoice_date == datetime(2025, 1, 5, tzinfo=UTC).date()

    def test_invoice_type_is_poa(self):
        line = build_poa_profit_cost_extract(
            claim_reference="INQC-WCLA-YHMY",
            sequence=1,
            submission_date=_submission(),
            net=Decimal("1000.00"),
            vat_zero_amount=None,
        )

        assert line.invoice_type == InvoiceTypeCode.POA


class TestBuildPoaDisbursementExtract:
    def test_gross_only_produces_single_standard_rated_line(self):
        lines = build_poa_disbursement_extract(
            claim_reference="INQC-WCLA-YHMY",
            submission_date=_submission(),
            gross=Decimal("1200.00"),
            vat_zero_amount=None,
        )

        assert len(lines) == 1
        line = lines[0]
        assert line.sequence_number == 1
        assert line.invoice_number == "INQC-WCLA-YHMY_001"
        assert line.invoice_amount == Decimal("1200.00")
        assert line.invoice_type == InvoiceTypeCode.POA
        assert line.tax_code == TaxCode.GB_VAT_20

    def test_vat_zero_only_produces_single_zero_rated_line(self):
        lines = build_poa_disbursement_extract(
            claim_reference="INQC-WCLA-YHMY",
            submission_date=_submission(),
            gross=None,
            vat_zero_amount=Decimal("500.00"),
        )

        assert len(lines) == 1
        line = lines[0]
        assert line.sequence_number == 1
        assert line.invoice_number == "INQC-WCLA-YHMY_001"
        assert line.invoice_amount == Decimal("500.00")
        assert line.tax_code == TaxCode.ZERO_VAT

    def test_gross_and_vat_zero_produce_two_incrementing_lines(self):
        lines = build_poa_disbursement_extract(
            claim_reference="INQC-DEMO-XZ12",
            submission_date=_submission(),
            gross=Decimal("1200.00"),
            vat_zero_amount=Decimal("200.00"),
        )

        assert len(lines) == 2

        standard_line, zero_line = lines

        # Standard-rated amount is gross (1200) minus zero-rated (200) = 1000.00
        assert standard_line.sequence_number == 1
        assert standard_line.invoice_number == "INQC-DEMO-XZ12_001"
        assert standard_line.invoice_amount == Decimal("1000.00")
        assert standard_line.tax_code == TaxCode.GB_VAT_20

        assert zero_line.sequence_number == 2
        assert zero_line.invoice_number == "INQC-DEMO-XZ12_002"
        assert zero_line.invoice_amount == Decimal("200.00")
        assert zero_line.tax_code == TaxCode.ZERO_VAT

    def test_zero_standard_rated_amount_skips_standard_line(self):
        lines = build_poa_disbursement_extract(
            claim_reference="INQC-WCLA-YHMY",
            submission_date=_submission(),
            gross=Decimal("500.00"),
            vat_zero_amount=Decimal("500.00"),
        )

        assert len(lines) == 1
        assert lines[0].sequence_number == 1
        assert lines[0].tax_code == TaxCode.ZERO_VAT
        assert lines[0].invoice_amount == Decimal("500.00")

    def test_amount_is_banker_rounded_to_two_decimal_places(self):
        lines = build_poa_disbursement_extract(
            claim_reference="INQC-WCLA-YHMY",
            submission_date=_submission(),
            gross=Decimal("1000.125"),
            vat_zero_amount=None,
        )

        assert lines[0].invoice_amount == Decimal("1000.12")

    def test_invoice_date_is_submission_date(self):
        lines = build_poa_disbursement_extract(
            claim_reference="INQC-WCLA-YHMY",
            submission_date=_submission(2025, 1, 5),
            gross=Decimal("1200.00"),
            vat_zero_amount=None,
        )

        assert lines[0].invoice_date == datetime(2025, 1, 5, tzinfo=UTC).date()

    def test_no_amounts_produces_no_lines(self):
        lines = build_poa_disbursement_extract(
            claim_reference="INQC-WCLA-YHMY",
            submission_date=_submission(),
            gross=None,
            vat_zero_amount=None,
        )

        assert lines == []


class TestBuildFinalBillFeesExtract:
    def test_vat_zero_produces_zero_rated_line_at_full_value(self):
        line = build_final_bill_fees_extract(
            claim_reference="INQC-WCLA-YHMY",
            sequence=1,
            invoice_date=_submission().date(),
            gross=None,
            vat_zero_amount=Decimal("1000.00"),
        )

        assert line is not None
        assert line.invoice_amount == Decimal("1000.00")
        assert line.tax_code == TaxCode.ZERO_VAT
        assert line.invoice_type == InvoiceTypeCode.FINAL_BILL_FEES

    def test_gross_produces_standard_rated_line_at_full_value(self):
        line = build_final_bill_fees_extract(
            claim_reference="INQC-WCLA-YHMY",
            sequence=1,
            invoice_date=_submission().date(),
            gross=Decimal("1200.00"),
            vat_zero_amount=None,
        )

        assert line is not None
        assert line.invoice_amount == Decimal("1200.00")
        assert line.tax_code == TaxCode.GB_VAT_20
        assert line.invoice_type == InvoiceTypeCode.FINAL_BILL_FEES

    def test_vat_zero_takes_precedence_over_gross(self):
        line = build_final_bill_fees_extract(
            claim_reference="INQC-WCLA-YHMY",
            sequence=1,
            invoice_date=_submission().date(),
            gross=Decimal("1200.00"),
            vat_zero_amount=Decimal("500.00"),
        )

        assert line is not None
        assert line.invoice_amount == Decimal("500.00")
        assert line.tax_code == TaxCode.ZERO_VAT

    def test_no_amounts_produces_no_line(self):
        assert (
            build_final_bill_fees_extract(
                claim_reference="INQC-WCLA-YHMY",
                sequence=1,
                invoice_date=_submission().date(),
                gross=None,
                vat_zero_amount=None,
            )
            is None
        )

    def test_zero_amounts_produce_no_line(self):
        assert (
            build_final_bill_fees_extract(
                claim_reference="INQC-WCLA-YHMY",
                sequence=1,
                invoice_date=_submission().date(),
                gross=Decimal("0.00"),
                vat_zero_amount=Decimal("0.00"),
            )
            is None
        )

    def test_invoice_number_pads_given_sequence(self):
        line = build_final_bill_fees_extract(
            claim_reference="INQC-DEMO-XZ12",
            sequence=1,
            invoice_date=_submission().date(),
            gross=Decimal("1200.00"),
            vat_zero_amount=None,
        )

        assert line is not None
        assert line.invoice_number == "INQC-DEMO-XZ12_001"

    def test_amount_is_banker_rounded(self):
        line = build_final_bill_fees_extract(
            claim_reference="INQC-WCLA-YHMY",
            sequence=1,
            invoice_date=_submission().date(),
            gross=Decimal("1000.125"),
            vat_zero_amount=None,
        )

        assert line is not None
        assert line.invoice_amount == Decimal("1000.12")


class TestBuildFinalBillNilFeesExtract:
    def test_produces_zero_value_final_bill_fees_line(self):
        line = build_final_bill_nil_fees_extract(
            claim_reference="INQC-DEMO-XZ12",
            sequence=1,
            invoice_date=_submission().date(),
        )

        assert line.sequence_number == 1
        assert line.invoice_number == "INQC-DEMO-XZ12_001"
        assert line.invoice_amount == Decimal("0.00")
        assert line.invoice_date == _submission().date()
        assert line.invoice_type == InvoiceTypeCode.FINAL_BILL_FEES
        assert line.tax_code == TaxCode.GB_VAT_20


class TestBuildFinalBillDisbursementExtract:
    def test_gross_and_vat_zero_produce_standard_then_zero_lines(self):
        lines = build_final_bill_disbursement_extract(
            claim_reference="INQC-DEMO-XZ12",
            start_sequence=2,
            invoice_date=_submission().date(),
            gross=Decimal("1200.00"),
            vat_zero_amount=Decimal("200.00"),
        )

        assert len(lines) == 2
        standard_line, zero_line = lines

        assert standard_line.sequence_number == 2
        assert standard_line.invoice_number == "INQC-DEMO-XZ12_002"
        assert standard_line.invoice_amount == Decimal("1000.00")
        assert standard_line.tax_code == TaxCode.GB_VAT_20
        assert standard_line.invoice_type == InvoiceTypeCode.FINAL_BILL_DISBURSEMENT

        assert zero_line.sequence_number == 3
        assert zero_line.invoice_number == "INQC-DEMO-XZ12_003"
        assert zero_line.invoice_amount == Decimal("200.00")
        assert zero_line.tax_code == TaxCode.ZERO_VAT
        assert zero_line.invoice_type == InvoiceTypeCode.FINAL_BILL_DISBURSEMENT

    def test_start_sequence_is_respected_for_single_line(self):
        lines = build_final_bill_disbursement_extract(
            claim_reference="INQC-WCLA-YHMY",
            start_sequence=5,
            invoice_date=_submission().date(),
            gross=Decimal("1200.00"),
            vat_zero_amount=None,
        )

        assert len(lines) == 1
        assert lines[0].sequence_number == 5
        assert lines[0].invoice_number == "INQC-WCLA-YHMY_005"

    def test_zero_standard_rated_amount_skips_standard_line(self):
        lines = build_final_bill_disbursement_extract(
            claim_reference="INQC-WCLA-YHMY",
            start_sequence=2,
            invoice_date=_submission().date(),
            gross=Decimal("500.00"),
            vat_zero_amount=Decimal("500.00"),
        )

        assert len(lines) == 1
        assert lines[0].sequence_number == 2
        assert lines[0].tax_code == TaxCode.ZERO_VAT

    def test_no_amounts_produce_no_lines(self):
        lines = build_final_bill_disbursement_extract(
            claim_reference="INQC-WCLA-YHMY",
            start_sequence=2,
            invoice_date=_submission().date(),
            gross=None,
            vat_zero_amount=None,
        )

        assert lines == []


class TestBuildRecoupmentExtract:
    def test_each_source_line_is_negated_with_dash_r_suffix(self):
        sources = [
            RecoupmentSourceLine(
                invoice_number="INQC-POAA-0001_001",
                invoice_amount=Decimal("800.00"),
                tax_code=TaxCode.GB_VAT_20,
            ),
            RecoupmentSourceLine(
                invoice_number="INQC-POAB-0002_001",
                invoice_amount=Decimal("200.00"),
                tax_code=TaxCode.ZERO_VAT,
            ),
        ]

        lines = build_recoupment_extract(
            start_sequence=4,
            invoice_date=_submission(2026, 9, 21).date(),
            original_lines=sources,
        )

        assert len(lines) == 2

        first, second = lines
        assert first.sequence_number == 4
        assert first.invoice_number == "INQC-POAA-0001_001-R"
        assert first.invoice_amount == Decimal("-800.00")
        assert first.tax_code == TaxCode.GB_VAT_20
        assert first.invoice_type == InvoiceTypeCode.RECOUPED
        assert first.invoice_date == _submission(2026, 9, 21).date()

        assert second.sequence_number == 5
        assert second.invoice_number == "INQC-POAB-0002_001-R"
        assert second.invoice_amount == Decimal("-200.00")
        assert second.tax_code == TaxCode.ZERO_VAT

    def test_empty_sources_produce_no_lines(self):
        assert (
            build_recoupment_extract(
                start_sequence=4,
                invoice_date=_submission().date(),
                original_lines=[],
            )
            == []
        )
