from dataclasses import dataclass
from decimal import Decimal

from app.domain.claim_error import ClaimErrorCode, ClaimValidationError
from app.domain.constants.claim_messages import (
    MIXED_VAT_MESSAGE,
    MISSING_GROSS_MESSAGE,
    MISSING_POA_TYPE_MESSAGE,
    MISSING_TOTAL_MESSAGE,
    NEGATIVE_NET_MESSAGE,
    NET_GT_GROSS_MESSAGE,
    POA_NOT_ALLOWED_MESSAGE,
)
from app.models.claim.enums import ClaimType, POAType


@dataclass(frozen=True)
class Claim:
    claim_type: ClaimType
    poa_type: POAType | None
    net: Decimal | None
    gross: Decimal | None
    vat_zero_total: Decimal | None

    def __post_init__(self) -> None:
        self._validate_claim_type_poa_combination()

        self._validate_totals_consistency()

        if (
            self.claim_type == ClaimType.PAYMENT_ON_ACCOUNT
            and self.poa_type is not None
            and self.poa_type != POAType.PROFIT_COST
        ):
            self._normalize_non_profit_cost_totals()

        if self.poa_type == POAType.PROFIT_COST:
            self._validate_profit_cost()

    def _normalize_non_profit_cost_totals(self) -> None:
        object.__setattr__(
            self,
            "net",
            self.net if self.net is not None else Decimal("0.00"),
        )
        object.__setattr__(
            self,
            "gross",
            self.gross if self.gross is not None else Decimal("0.00"),
        )
        object.__setattr__(
            self,
            "vat_zero_total",
            self.vat_zero_total if self.vat_zero_total is not None else Decimal("0.00"),
        )

    def _validate_claim_type_poa_combination(self) -> None:
        if self.claim_type == ClaimType.PAYMENT_ON_ACCOUNT and self.poa_type is None:
            raise ClaimValidationError(
                ClaimErrorCode.MISSING_POA_TYPE_FOR_PAYMENT_ON_ACCOUNT,
                MISSING_POA_TYPE_MESSAGE,
            )

        if (
            self.claim_type != ClaimType.PAYMENT_ON_ACCOUNT
            and self.poa_type is not None
        ):
            raise ClaimValidationError(
                ClaimErrorCode.POA_TYPE_NOT_ALLOWED_FOR_NON_PAYMENT_ON_ACCOUNT,
                POA_NOT_ALLOWED_MESSAGE,
            )

    def _validate_profit_cost(self) -> None:
        has_vat_zero = self.vat_zero_total is not None
        has_net = self.net is not None
        has_gross = self.gross is not None

        if has_vat_zero and (has_net or has_gross):
            raise ClaimValidationError(
                ClaimErrorCode.PROFIT_COST_MIXED_VAT,
                MIXED_VAT_MESSAGE,
            )

        if not has_vat_zero and not (has_net and has_gross):
            if has_net and not has_gross:
                raise ClaimValidationError(
                    ClaimErrorCode.MISSING_GROSS_TOTAL_WHEN_NET_ENTERED,
                    MISSING_GROSS_MESSAGE,
                )
            raise ClaimValidationError(
                ClaimErrorCode.MISSING_TOTAL_CLAIM_COST,
                MISSING_TOTAL_MESSAGE,
            )

    def _validate_totals_consistency(self) -> None:
        has_net = self.net is not None
        has_gross = self.gross is not None

        if has_net and self.net < 0:
            raise ClaimValidationError(
                ClaimErrorCode.NEGATIVE_NET_COST,
                NEGATIVE_NET_MESSAGE,
            )

        if has_net and has_gross and self.net > self.gross:
            raise ClaimValidationError(
                ClaimErrorCode.NET_TOTAL_HIGHER_THAN_GROSS_TOTAL,
                NET_GT_GROSS_MESSAGE,
            )
