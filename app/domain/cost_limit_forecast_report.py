from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.domain.claim import ApprovedClaimAmount, calculate_available_funds
from app.models.application.enums import MeritsDecision, PublicBodyId
from app.models.claim.enums import ClaimDecisionStatus, ClaimStatus, ClaimType

PUBLIC_BODY_DELIMITER = "; "
_LIVE_APPLICATION_STATUS = "LIVE"
_DATE_FORMAT = "%d-%m-%Y"


class InvalidCostLimitForecastRecordError(ValueError):
    pass


@dataclass(frozen=True)
class ForecastClaim:
    claim_type: ClaimType
    status: ClaimStatus
    gross: Decimal | None
    vat_zero_total: Decimal | None


@dataclass(frozen=True)
class CostLimitForecastCandidate:
    application_id: int
    laa_reference: str
    application_status: str | None
    merits_decision: MeritsDecision | str
    certificate_end_date: date | None
    cost_limit: int | None
    certificate_effective_date: date
    claims: tuple[ForecastClaim, ...]
    public_bodies: tuple[PublicBodyId, ...]

    def is_live(self, report_date: date) -> bool:
        return (
            self.application_status == _LIVE_APPLICATION_STATUS
            and self.merits_decision == MeritsDecision.GRANTED
            and (
                self.certificate_end_date is None
                or self.certificate_end_date >= report_date
            )
        )

    def has_paid_final_bill(self) -> bool:
        return any(
            claim.claim_type == ClaimType.FINAL_BILL
            and claim.status == ClaimStatus.PAY_IN_FULL
            for claim in self.claims
        )

    def remaining_cost_limit(self) -> Decimal:
        paid_claims = [
            ApprovedClaimAmount(
                decision=ClaimDecisionStatus.PAY_IN_FULL,
                gross=claim.gross,
                vat_zero_total=claim.vat_zero_total,
            )
            for claim in self.claims
            if claim.status == ClaimStatus.PAY_IN_FULL
        ]
        return calculate_available_funds(self.cost_limit, paid_claims)


def build_cost_limit_forecast_row(
    candidate: CostLimitForecastCandidate, report_date: date
) -> list[str] | None:
    """Return the CSV row, or None when the certificate is not part of the forecast."""
    if not candidate.is_live(report_date) or candidate.has_paid_final_bill():
        return None

    remaining = candidate.remaining_cost_limit()
    if remaining <= 0:
        return None

    if not candidate.public_bodies:
        raise InvalidCostLimitForecastRecordError(
            f"No public bodies found for application {candidate.application_id}"
        )

    return [
        candidate.laa_reference,
        PUBLIC_BODY_DELIMITER.join(
            sorted(body.value for body in candidate.public_bodies)
        ),
        f"{Decimal(candidate.cost_limit):.2f}",
        f"{remaining:.2f}",
        candidate.certificate_effective_date.strftime(_DATE_FORMAT),
    ]
