from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

from app.domain.decisions_report import neutralise_csv_formula
from app.models.application.enums import PublicBodyId
from app.models.claim.enums import (
    ClaimDecisionStatus,
    ClaimType,
    InvoiceTypeCode,
    TaxCode,
)

PUBLIC_BODY_DELIMITER = "; "

_BILL_TYPE_LABELS = {
    ClaimType.PAYMENT_ON_ACCOUNT: "POA",
    ClaimType.FINAL_BILL: "Final bill",
    ClaimType.NIL_BILL: "Nil bill",
}
_RECOUPED_BILL_TYPE = "POA"
_DECISION_LABELS = {ClaimDecisionStatus.PAY_IN_FULL: "Pay in full"}


class InvalidOgdCostsRecordError(ValueError):
    pass


@dataclass(frozen=True)
class OgdCostsReportSourceLine:
    application_id: int
    claim_decision_date: datetime
    claim_decision: ClaimDecisionStatus
    invoice_type: InvoiceTypeCode
    claim_type: ClaimType
    laa_reference: str
    invoice_number: str
    invoice_amount: Decimal
    tax_code: TaxCode
    deceased_first_name: str
    deceased_last_name: str
    deceased_date_of_death: str


def format_public_bodies(bodies: list[PublicBodyId]) -> str:
    return PUBLIC_BODY_DELIMITER.join(sorted(body.value for body in bodies))


def resolve_bill_type(line: OgdCostsReportSourceLine) -> str:
    # Recoupments are stored against the final bill's claim but reverse a POA payment.
    if line.invoice_type == InvoiceTypeCode.RECOUPED:
        return _RECOUPED_BILL_TYPE
    return _BILL_TYPE_LABELS[line.claim_type]


def build_ogd_costs_row(
    line: OgdCostsReportSourceLine, public_bodies: list[PublicBodyId]
) -> list[str]:
    decision_label = _DECISION_LABELS.get(line.claim_decision)
    if decision_label is None:
        raise InvalidOgdCostsRecordError(
            f"Unsupported claim decision {line.claim_decision}"
        )

    return [
        _decision_date(line.claim_decision_date),
        decision_label,
        resolve_bill_type(line),
        format_public_bodies(public_bodies),
        line.laa_reference,
        line.invoice_number,
        f"{line.invoice_amount:.2f}",
        line.tax_code.value,
        neutralise_csv_formula(f"{line.deceased_first_name} {line.deceased_last_name}"),
        _date_of_death(line.deceased_date_of_death),
    ]


def _decision_date(decided_at: datetime) -> str:
    if decided_at.tzinfo is None:
        decided_at = decided_at.replace(tzinfo=UTC)
    return decided_at.astimezone(UTC).date().isoformat()


def _date_of_death(value: str) -> str:
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise InvalidOgdCostsRecordError(
            "Date of death is not a valid YYYY-MM-DD date"
        ) from exc
