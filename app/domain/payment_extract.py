from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_HALF_EVEN, Decimal

from app.domain.constants.claims import PROFIT_COST_PAYMENT_RATE, VAT_MULTIPLIER
from app.models.claim.enums import InvoiceTypeCode, TaxCode

_TWO_DECIMAL_PLACES = Decimal("0.01")


def bankers_round(value: Decimal) -> Decimal:
    return value.quantize(_TWO_DECIMAL_PLACES, rounding=ROUND_HALF_EVEN)


@dataclass(frozen=True)
class PaymentExtractLine:
    sequence_number: int
    invoice_number: str
    invoice_amount: Decimal
    invoice_date: date
    invoice_type: InvoiceTypeCode
    tax_code: TaxCode


def build_poa_profit_cost_extract(
    claim_id: int,
    sequence: int,
    submission_date: datetime,
    net: Decimal | None,
    vat_zero: Decimal | None,
) -> PaymentExtractLine:
    if vat_zero is not None:
        invoice_amount = bankers_round(vat_zero * PROFIT_COST_PAYMENT_RATE)
        tax_code = TaxCode.ZERO_VAT
    elif net is not None:
        invoice_amount = bankers_round(net * PROFIT_COST_PAYMENT_RATE * VAT_MULTIPLIER)
        tax_code = TaxCode.GB_VAT_20
    else:
        raise ValueError("POA profit cost extract requires a net or vat_zero amount")

    return PaymentExtractLine(
        sequence_number=sequence,
        invoice_number=f"{claim_id}_{sequence:03d}",
        invoice_amount=invoice_amount,
        invoice_date=submission_date.date(),
        invoice_type=InvoiceTypeCode.POA,
        tax_code=tax_code,
    )


def build_final_bill_fee_lines(
    claim_id: int,
    submission_date: datetime,
    gross: Decimal | None,
    vat_zero: Decimal | None,
    start_sequence: int = 1,
) -> list[PaymentExtractLine]:
    standard_amount = (gross or Decimal(0)) - (vat_zero or Decimal(0))
    zero_amount = vat_zero or Decimal(0)

    lines: list[PaymentExtractLine] = []
    sequence = start_sequence
    invoice_date = submission_date.date()

    if standard_amount > 0:
        lines.append(
            PaymentExtractLine(
                sequence_number=sequence,
                invoice_number=f"{claim_id}_{sequence:03d}",
                invoice_amount=bankers_round(standard_amount),
                invoice_date=invoice_date,
                invoice_type=InvoiceTypeCode.FINAL_BILL_FEES,
                tax_code=TaxCode.GB_VAT_20,
            )
        )
        sequence += 1

    if zero_amount > 0:
        lines.append(
            PaymentExtractLine(
                sequence_number=sequence,
                invoice_number=f"{claim_id}_{sequence:03d}",
                invoice_amount=bankers_round(zero_amount),
                invoice_date=invoice_date,
                invoice_type=InvoiceTypeCode.FINAL_BILL_FEES,
                tax_code=TaxCode.ZERO_VAT,
            )
        )

    if not lines:
        raise ValueError("Final bill fee lines require a gross or vat_zero amount")

    return lines


def build_recoupment_line(
    claim_id: int,
    sequence: int,
    original_amount: Decimal,
    tax_code: TaxCode,
    decision_date: date,
) -> PaymentExtractLine:
    return PaymentExtractLine(
        sequence_number=sequence,
        invoice_number=f"{claim_id}_{sequence:03d}",
        invoice_amount=bankers_round(-original_amount),
        invoice_date=decision_date,
        invoice_type=InvoiceTypeCode.RECOUPED,
        tax_code=tax_code,
    )
