from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

from app.domain.claim_error import ClaimErrorCode, ClaimValidationError
from app.domain.claim_rejection import ClaimRejection, ClaimRejectionReason
from app.domain.constants.claim_messages import (
    MIXED_VAT_MESSAGE,
    MISSING_GROSS_MESSAGE,
    MISSING_NON_PROFIT_COST_TOTAL_MESSAGE,
    MISSING_POA_TYPE_MESSAGE,
    MISSING_TOTAL_MESSAGE,
    NEGATIVE_NET_MESSAGE,
    NET_GT_GROSS_MESSAGE,
    POA_NOT_ALLOWED_MESSAGE,
)
from app.models.application.index import Application
from app.models.claim.enums import ClaimStatus

if TYPE_CHECKING:
    from app.models.claim.index import Claim as DBClaim
from app.models.claim.enums import ClaimType, POAType


def _as_utc(dt: datetime) -> datetime:
    """Treat timezone-naive datetimes as UTC for safe comparison."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


MAX_PROFIT_COST_POA_CLAIM_COUNT = 4


@dataclass(frozen=True)
class Claim:
    claim_type: ClaimType
    poa_type: POAType | None
    net: Decimal | None
    gross: Decimal | None
    vat_zero_total: Decimal | None

    def __post_init__(self) -> None:
        self._validate_claim_type_poa_combination()

    def validate_total_claim_cost(self) -> None:
        self._validate_totals_consistency()

        if (
            self.claim_type == ClaimType.PAYMENT_ON_ACCOUNT
            and self.poa_type is not None
            and self.poa_type != POAType.PROFIT_COST
        ):
            self._validate_non_profit_cost_has_at_least_one_total()
            self._normalize_non_profit_cost_totals()

        if self.poa_type == POAType.PROFIT_COST:
            self._validate_profit_cost()

    def total_claim_cost_for_limit_check(self) -> Decimal | None:
        return self.gross

    def should_auto_reject_for_max_poa_count(
        self,
        existing_claims: list[DBClaim],
        reference_date: datetime | None = None,
    ) -> ClaimRejectionReason | None:
        if self.poa_type != POAType.PROFIT_COST:
            return None

        cutoff = (reference_date or datetime.now(UTC)) - timedelta(days=365)
        active_poas = [
            c
            for c in existing_claims
            if c.poa_type_id == POAType.PROFIT_COST
            and c.status_id in (ClaimStatus.PENDING, ClaimStatus.ACCEPTED)
            and _as_utc(c.submission_date) >= cutoff
        ]
        exceeds = len(active_poas) >= MAX_PROFIT_COST_POA_CLAIM_COUNT
        return ClaimRejectionReason.MAX_POA_CLAIMS_EXCEEDED if exceeds else None

    def should_auto_reject_for_limit(
        self, application: Application
    ) -> ClaimRejectionReason | None:
        total = self.total_claim_cost_for_limit_check()
        if total is None:
            return None

        limit = self._get_substantive_cost_limit(application)
        if limit is None:
            return None

        exceeds_limit = total > limit
        return (
            ClaimRejectionReason.CLAIM_EXCEEDS_SUBSTANTIVE_COST_LIMIT
            if exceeds_limit
            else None
        )

    def should_auto_reject_for_application_total_limit(
        self,
        application: Application,
        existing_claims: list[DBClaim],
    ) -> ClaimRejectionReason | None:
        if self.gross is None:
            return None

        limit = self._get_substantive_cost_limit(application)
        if limit is None:
            return None

        application_claims = [
            c
            for c in existing_claims
            if c.status_id in (ClaimStatus.PENDING, ClaimStatus.ACCEPTED)
        ]
        existing_total = sum(
            (c.total_profit_cost_gross or Decimal(0)) for c in application_claims
        )
        total = existing_total + self.gross
        exceeds_limit = total > limit
        return (
            ClaimRejectionReason.APPLICATION_CLAIMS_EXCEED_COST_LIMIT
            if exceeds_limit
            else None
        )

    def should_auto_reject(
        self,
        application: Application,
        existing_claims: list[DBClaim],
        reference_date: datetime | None = None,
    ) -> ClaimRejection:
        reasons = []

        max_poa_reason = self.should_auto_reject_for_max_poa_count(
            existing_claims, reference_date
        )
        if max_poa_reason:
            reasons.append(max_poa_reason)

        limit_reason = self.should_auto_reject_for_limit(application)
        if limit_reason:
            reasons.append(limit_reason)

        app_total_reason = self.should_auto_reject_for_application_total_limit(
            application, existing_claims
        )
        if app_total_reason:
            reasons.append(app_total_reason)

        return ClaimRejection(reasons=reasons)

    def _get_substantive_cost_limit(self, application: Application) -> Decimal | None:
        if not application.proceedings:
            return None
        raw_limit = application.proceedings[0].substantive_cost_limitation
        if raw_limit is None:
            return None
        return Decimal(str(raw_limit))

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

    def _validate_non_profit_cost_has_at_least_one_total(self) -> None:
        if self.net is None and self.gross is None and self.vat_zero_total is None:
            raise ClaimValidationError(
                ClaimErrorCode.MISSING_NON_PROFIT_COST_TOTAL,
                MISSING_NON_PROFIT_COST_TOTAL_MESSAGE,
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
