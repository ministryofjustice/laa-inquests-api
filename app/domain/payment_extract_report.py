from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.models.claim.enums import InvoiceTypeCode, POAType, TaxCode


class UnclassifiablePaymentLineError(ValueError):
    pass


@dataclass(frozen=True)
class PaymentLineClassification:
    description: str
    model_number: str


FINAL_BILL_PROFIT_COSTS = PaymentLineClassification("Profit costs", "Profit costs")
POA_PROFIT_COSTS = PaymentLineClassification("Profit costs (80%)", "Profit costs")
DISBURSEMENTS = PaymentLineClassification("Expert costs", "Disbursements")


@dataclass(frozen=True)
class PaymentLineType:
    invoice_type: InvoiceTypeCode
    poa_type: POAType | None = None
    original_poa_type: POAType | None = None


@dataclass(frozen=True)
class PaymentExtractReportSourceLine:
    invoice_number: str
    invoice_amount: Decimal
    invoice_date: date
    tax_code: TaxCode
    line_type: PaymentLineType
    firm_code: str
    office_id: str
    laa_reference: str


def classify_payment_line(line_type: PaymentLineType) -> PaymentLineClassification:
    match line_type.invoice_type:
        case InvoiceTypeCode.FINAL_BILL_FEES:
            return FINAL_BILL_PROFIT_COSTS
        case InvoiceTypeCode.FINAL_BILL_DISBURSEMENT:
            return DISBURSEMENTS
        case InvoiceTypeCode.POA:
            return _classify_poa(line_type.poa_type, line_type)
        case InvoiceTypeCode.RECOUPED:
            # Recoupments live on the final bill claim, so the type comes from the original POA.
            return _classify_poa(line_type.original_poa_type, line_type)
    raise UnclassifiablePaymentLineError(
        f"Unknown invoice type {line_type.invoice_type}"
    )


def _classify_poa(
    poa_type: POAType | None, line_type: PaymentLineType
) -> PaymentLineClassification:
    if poa_type is None:
        raise UnclassifiablePaymentLineError(
            f"Cannot classify {line_type.invoice_type.value} line without a POA type"
        )
    if poa_type == POAType.PROFIT_COST:
        return POA_PROFIT_COSTS
    return DISBURSEMENTS
