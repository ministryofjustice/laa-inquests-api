from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal

from app.models.claim.enums import InvoiceTypeCode, TaxCode
from app.models.claim.index import ClaimDecisionAmount


class CreateClaimDecisionAmountPort(ABC):
    @abstractmethod
    def create_claim_decision_amount(
        self,
        claim_decision_id: int,
        profit_cost_net: Decimal | None = None,
        profit_cost_gross: Decimal | None = None,
        profit_cost_vat_zero: Decimal | None = None,
        disbursement_net: Decimal | None = None,
        disbursement_gross: Decimal | None = None,
        disbursement_vat_zero: Decimal | None = None,
        invoice_number: str | None = None,
        invoice_amount: Decimal | None = None,
        invoice_date: date | None = None,
        invoice_type: InvoiceTypeCode | None = None,
        tax_code: TaxCode | None = None,
    ) -> ClaimDecisionAmount: ...
