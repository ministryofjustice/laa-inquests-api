from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.domain.claim_error import ClaimErrorCode, ClaimValidationError
from app.domain.constants.claim_messages import (
    DISB_GROSS_NOT_GREATER_THAN_TOTAL_MESSAGE,
    DISB_MISSING_GROSS_TOTAL_MESSAGE,
    DISB_MISSING_NET_TOTAL_MESSAGE,
    DISB_MISSING_TOTAL_MESSAGE,
    NET_GT_GROSS_MESSAGE,
    PIF_MISSING_GROSS_TOTAL_MESSAGE,
    PIF_MISSING_NET_TOTAL_MESSAGE,
    PIF_MISSING_TOTAL_CLAIM_COST_MESSAGE,
    PIF_PROFIT_COST_MIXED_VAT_MESSAGE,
)


@dataclass(frozen=True)
class PayInFullClaim:
    profit_cost_net: Decimal | None = None
    profit_cost_gross: Decimal | None = None
    profit_cost_vat_zero: Decimal | None = None
    disbursement_net: Decimal | None = None
    disbursement_gross: Decimal | None = None
    disbursement_vat_zero: Decimal | None = None

    def validate(self) -> None:
        self._validate_profit_cost()
        self._validate_disbursement()

    def _validate_profit_cost(self) -> None:
        has_net = self.profit_cost_net is not None
        has_gross = self.profit_cost_gross is not None
        has_vat_zero = self.profit_cost_vat_zero is not None

        if not has_net and not has_gross and not has_vat_zero:
            raise ClaimValidationError(
                ClaimErrorCode.MISSING_TOTAL_CLAIM_COST,
                PIF_MISSING_TOTAL_CLAIM_COST_MESSAGE,
            )

        if has_vat_zero and (has_net or has_gross):
            raise ClaimValidationError(
                ClaimErrorCode.PROFIT_COST_MIXED_VAT,
                PIF_PROFIT_COST_MIXED_VAT_MESSAGE,
            )

        if has_net and not has_gross:
            raise ClaimValidationError(
                ClaimErrorCode.MISSING_GROSS_TOTAL_WHEN_NET_ENTERED,
                PIF_MISSING_GROSS_TOTAL_MESSAGE,
            )

        if has_gross and not has_net:
            raise ClaimValidationError(
                ClaimErrorCode.MISSING_NET_TOTAL_WHEN_GROSS_ENTERED,
                PIF_MISSING_NET_TOTAL_MESSAGE,
            )

        if (
            self.profit_cost_net is not None
            and self.profit_cost_gross is not None
            and self.profit_cost_net > self.profit_cost_gross
        ):
            raise ClaimValidationError(
                ClaimErrorCode.NET_TOTAL_HIGHER_THAN_GROSS_TOTAL,
                NET_GT_GROSS_MESSAGE,
            )

    def _validate_disbursement(self) -> None:
        has_net = self.disbursement_net is not None
        has_gross = self.disbursement_gross is not None
        has_vat_zero = self.disbursement_vat_zero is not None

        if not has_net and not has_gross and not has_vat_zero:
            raise ClaimValidationError(
                ClaimErrorCode.MISSING_DISBURSEMENT_TOTAL,
                DISB_MISSING_TOTAL_MESSAGE,
            )

        if has_net and not has_gross:
            raise ClaimValidationError(
                ClaimErrorCode.MISSING_DISBURSEMENT_GROSS_WHEN_NET_ENTERED,
                DISB_MISSING_GROSS_TOTAL_MESSAGE,
            )

        if has_gross and not has_net:
            raise ClaimValidationError(
                ClaimErrorCode.MISSING_DISBURSEMENT_NET_WHEN_GROSS_ENTERED,
                DISB_MISSING_NET_TOTAL_MESSAGE,
            )

        if self.disbursement_net is not None and self.disbursement_gross is not None:
            vat_zero = self.disbursement_vat_zero or Decimal(0)
            if self.disbursement_gross <= vat_zero + self.disbursement_net:
                raise ClaimValidationError(
                    ClaimErrorCode.DISBURSEMENT_GROSS_NOT_GREATER_THAN_TOTAL,
                    DISB_GROSS_NOT_GREATER_THAN_TOTAL_MESSAGE,
                )
