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
    vat_zero_amount: Decimal | None,
) -> PaymentExtractLine:
    if vat_zero_amount is not None:
        invoice_amount = bankers_round(vat_zero_amount * PROFIT_COST_PAYMENT_RATE)
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


def build_poa_disbursement_extract(
    claim_id: int,
    submission_date: datetime,
    gross: Decimal | None,
    vat_zero_amount: Decimal | None,
) -> list[PaymentExtractLine]:
    invoice_date = submission_date.date()
    vat_20_percent_amount = (gross or Decimal("0.00")) - (
        vat_zero_amount or Decimal("0.00")
    )

    lines: list[PaymentExtractLine] = []
    sequence = 1

    if vat_20_percent_amount > 0:
        lines.append(
            PaymentExtractLine(
                sequence_number=sequence,
                invoice_number=f"{claim_id}_{sequence:03d}",
                invoice_amount=bankers_round(vat_20_percent_amount),
                invoice_date=invoice_date,
                invoice_type=InvoiceTypeCode.POA,
                tax_code=TaxCode.GB_VAT_20,
            )
        )
        sequence += 1

    if vat_zero_amount is not None and vat_zero_amount > 0:
        lines.append(
            PaymentExtractLine(
                sequence_number=sequence,
                invoice_number=f"{claim_id}_{sequence:03d}",
                invoice_amount=bankers_round(vat_zero_amount),
                invoice_date=invoice_date,
                invoice_type=InvoiceTypeCode.POA,
                tax_code=TaxCode.ZERO_VAT,
            )
        )

    return lines


def build_final_bill_fees_extract(
    claim_id: int,
    sequence: int,
    invoice_date: date,
    gross: Decimal | None,
    vat_zero_amount: Decimal | None,
) -> PaymentExtractLine | None:
    if vat_zero_amount is not None and vat_zero_amount > 0:
        invoice_amount = vat_zero_amount
        tax_code = TaxCode.ZERO_VAT
    elif gross is not None and gross > 0:
        invoice_amount = gross
        tax_code = TaxCode.GB_VAT_20
    else:
        return None

    return PaymentExtractLine(
        sequence_number=sequence,
        invoice_number=f"{claim_id}_{sequence:03d}",
        invoice_amount=bankers_round(invoice_amount),
        invoice_date=invoice_date,
        invoice_type=InvoiceTypeCode.FINAL_BILL_FEES,
        tax_code=tax_code,
    )


def build_final_bill_disbursement_extract(
    claim_id: int,
    start_sequence: int,
    invoice_date: date,
    gross: Decimal | None,
    vat_zero_amount: Decimal | None,
) -> list[PaymentExtractLine]:
    vat_20_percent_amount = (gross or Decimal("0.00")) - (
        vat_zero_amount or Decimal("0.00")
    )

    lines: list[PaymentExtractLine] = []
    sequence = start_sequence

    if vat_20_percent_amount > 0:
        lines.append(
            PaymentExtractLine(
                sequence_number=sequence,
                invoice_number=f"{claim_id}_{sequence:03d}",
                invoice_amount=bankers_round(vat_20_percent_amount),
                invoice_date=invoice_date,
                invoice_type=InvoiceTypeCode.FINAL_BILL_DISBURSEMENT,
                tax_code=TaxCode.GB_VAT_20,
            )
        )
        sequence += 1

    if vat_zero_amount is not None and vat_zero_amount > 0:
        lines.append(
            PaymentExtractLine(
                sequence_number=sequence,
                invoice_number=f"{claim_id}_{sequence:03d}",
                invoice_amount=bankers_round(vat_zero_amount),
                invoice_date=invoice_date,
                invoice_type=InvoiceTypeCode.FINAL_BILL_DISBURSEMENT,
                tax_code=TaxCode.ZERO_VAT,
            )
        )

    return lines


@dataclass(frozen=True)
class RecoupmentSourceLine:
    invoice_number: str
    invoice_amount: Decimal
    tax_code: TaxCode


def build_recoupment_extract(
    start_sequence: int,
    invoice_date: date,
    original_lines: list[RecoupmentSourceLine],
) -> list[PaymentExtractLine]:
    lines: list[PaymentExtractLine] = []
    for offset, original in enumerate(original_lines):
        sequence = start_sequence + offset
        lines.append(
            PaymentExtractLine(
                sequence_number=sequence,
                # Recoupments reclaim the original POA payment, so appear as a negative.
                invoice_number=f"{original.invoice_number}-R",
                invoice_amount=bankers_round(-original.invoice_amount),
                invoice_date=invoice_date,
                invoice_type=InvoiceTypeCode.RECOUPED,
                tax_code=original.tax_code,
            )
        )
    return lines
