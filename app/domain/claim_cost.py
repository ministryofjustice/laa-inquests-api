from dataclasses import dataclass

from app.models.claim.enums import POAType


@dataclass(frozen=True)
class ClaimCost:
    poa_type: POAType | None
    net: int | None
    gross: int | None
    vat_zero_total: int | None

    def __post_init__(self) -> None:
        if self.poa_type == POAType.PROFIT_COST:
            self._validate_profit_cost()

    def _validate_profit_cost(self) -> None:
        has_vat_zero = self.vat_zero_total is not None
        has_net = self.net is not None
        has_gross = self.gross is not None

        if has_vat_zero and (has_net or has_gross):
            raise ValueError(
                "You cannot submit a profit cost claim with both 0% and 20% VAT"
            )

        if not has_vat_zero and not (has_net and has_gross):
            if has_net and not has_gross:
                raise ValueError("Please complete the gross total value of your claim")
            raise ValueError(
                "Either total_profit_cost_vat_zero or both "
                "total_profit_cost_net and total_profit_cost_gross must be provided"
            )

        if has_net and self.net < 0:
            raise ValueError("net cost must not be negative")

        if has_net and has_gross and self.net > self.gross:
            raise ValueError("Net total cannot be higher than the gross total value")
