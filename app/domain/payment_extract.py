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
