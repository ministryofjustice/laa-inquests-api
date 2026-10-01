from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.domain.claim_error import ClaimErrorCode, ClaimValidationError
from app.domain.constants.claim_messages import (
    DISB_GROSS_NOT_GREATER_THAN_TOTAL_MESSAGE,
    DISB_MISSING_GROSS_TOTAL_MESSAGE,
    DISB_MISSING_NET_TOTAL_MESSAGE,
    DISB_MISSING_TOTAL_MESSAGE,
    DISB_NOT_ALLOWED_FOR_NIL_BILL_MESSAGE,
    DISB_NOT_ALLOWED_FOR_POA_MESSAGE,
    NET_GT_GROSS_MESSAGE,
    PIF_MISSING_GROSS_TOTAL_MESSAGE,
    PIF_MISSING_NET_TOTAL_MESSAGE,
    PIF_MISSING_TOTAL_CLAIM_COST_MESSAGE,
    PIF_PROFIT_COST_MIXED_VAT_MESSAGE,
    PIF_PROFIT_COST_NOT_ALLOWED_FOR_NIL_BILL_MESSAGE,
    PIF_PROFIT_COST_NOT_ALLOWED_FOR_POA_MESSAGE,
)
from app.models.claim.enums import ClaimType, POAType
from app.models.claim.index import Claim


@dataclass(frozen=True, kw_only=True)
class PayInFullClaim:
    claim_type_id: ClaimType
    poa_type_id: POAType | None = None
    profit_cost_net: Decimal | None = None
    profit_cost_gross: Decimal | None = None
    profit_cost_vat_zero: Decimal | None = None
    disbursement_net: Decimal | None = None
    disbursement_gross: Decimal | None = None
    disbursement_vat_zero: Decimal | None = None

    def validate(self) -> None:
        self._validate_profit_cost()
        self._validate_disbursement()

    @property
    def is_nil_bill(self) -> bool:
        amounts = (
            self.profit_cost_net,
            self.profit_cost_gross,
            self.profit_cost_vat_zero,
            self.disbursement_net,
            self.disbursement_gross,
            self.disbursement_vat_zero,
        )
        return all(amount is None or amount == 0 for amount in amounts)

    def _profit_cost_not_applicable(self) -> bool:
        return (
            self.claim_type_id == ClaimType.PAYMENT_ON_ACCOUNT
            and self.poa_type_id is not None
            and self.poa_type_id != POAType.PROFIT_COST
        )

    def _disbursement_not_applicable(self) -> bool:
        return (
            self.claim_type_id == ClaimType.PAYMENT_ON_ACCOUNT
            and self.poa_type_id == POAType.PROFIT_COST
        )

    def _validate_profit_cost(self) -> None:
        has_net = self.profit_cost_net is not None
        has_gross = self.profit_cost_gross is not None
        has_vat_zero = self.profit_cost_vat_zero is not None

        if self.claim_type_id == ClaimType.NIL_BILL:
            if has_net or has_gross or has_vat_zero:
                raise ClaimValidationError(
                    ClaimErrorCode.PROFIT_COST_NOT_ALLOWED_FOR_NIL_BILL_CLAIM,
                    PIF_PROFIT_COST_NOT_ALLOWED_FOR_NIL_BILL_MESSAGE,
                )
            return

        if self._profit_cost_not_applicable():
            if has_net or has_gross or has_vat_zero:
                raise ClaimValidationError(
                    ClaimErrorCode.PROFIT_COST_NOT_ALLOWED_FOR_POA_CLAIM,
                    PIF_PROFIT_COST_NOT_ALLOWED_FOR_POA_MESSAGE,
                )
            return

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

        if self.claim_type_id == ClaimType.NIL_BILL:
            if has_net or has_gross or has_vat_zero:
                raise ClaimValidationError(
                    ClaimErrorCode.DISBURSEMENT_NOT_ALLOWED_FOR_NIL_BILL_CLAIM,
                    DISB_NOT_ALLOWED_FOR_NIL_BILL_MESSAGE,
                )
            return

        if self._disbursement_not_applicable():
            if has_net or has_gross or has_vat_zero:
                raise ClaimValidationError(
                    ClaimErrorCode.DISBURSEMENT_NOT_ALLOWED_FOR_POA_CLAIM,
                    DISB_NOT_ALLOWED_FOR_POA_MESSAGE,
                )
            return

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
            has_no_standard_rated_disbursement = (
                self.disbursement_gross == 0 and self.disbursement_net == 0
            )
            if (
                not has_no_standard_rated_disbursement
                and self.disbursement_gross <= vat_zero + self.disbursement_net
            ):
                raise ClaimValidationError(
                    ClaimErrorCode.DISBURSEMENT_GROSS_NOT_GREATER_THAN_TOTAL,
                    DISB_GROSS_NOT_GREATER_THAN_TOTAL_MESSAGE,
                )


def pay_in_full_claim_from_submitted_poa_claim(claim: Claim) -> PayInFullClaim:
    """Reconstruct the decision amounts a provider originally submitted for
    a Payment on account claim, so a manual 'Pay in full' decision -- or
    auto-approval -- can reuse them without the amounts being re-entered."""
    is_profit_cost = claim.poa_type_id == POAType.PROFIT_COST
    return PayInFullClaim(
        claim_type_id=claim.claim_type_id,
        poa_type_id=claim.poa_type_id,
        profit_cost_net=claim.total_profit_cost_net if is_profit_cost else None,
        profit_cost_gross=claim.total_profit_cost_gross if is_profit_cost else None,
        profit_cost_vat_zero=claim.total_profit_cost_vat_zero
        if is_profit_cost
        else None,
        disbursement_net=claim.total_profit_cost_net if not is_profit_cost else None,
        disbursement_gross=claim.total_profit_cost_gross
        if not is_profit_cost
        else None,
        disbursement_vat_zero=claim.total_profit_cost_vat_zero
        if not is_profit_cost
        else None,
    )
