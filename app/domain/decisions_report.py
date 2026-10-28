from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from app.domain.audit_trail import resolve_history_username
from app.models.application.enums import ReasonForRefusal
from app.models.history.enums import ActorType, HistoryEventReference

DECISION_EVENT_REFERENCES = (
    HistoryEventReference.APPLICATION_ASSESSMENT_COMPLETED,
    HistoryEventReference.CLAIM_ASSESSMENT_COMPLETED,
    HistoryEventReference.POA_AUTO_APPROVED,
    HistoryEventReference.POA_AUTO_REJECTED,
)

_DATE_FORMAT = "%d-%m-%Y"
_TIME_FORMAT = "%H:%M:%S"
_FORMULA_TRIGGERS = ("=", "+", "-", "@", "\t", "\r")

_PAY_IN_FULL = "PAY_IN_FULL"
_REJECTED = "REJECTED"

_APPLICATION_DECISIONS = {"Granted", "Refused"}
_CLAIM_DECISION_LABELS = {_PAY_IN_FULL: "Pay in full", _REJECTED: "Rejected"}
_REFUSAL_REASON_LABELS = {
    ReasonForRefusal.NOT_IN_SCOPE.value: "Not in scope",
    ReasonForRefusal.INSUFFICIENT_INFORMATION.value: "Insufficient information",
    ReasonForRefusal.DUPLICATE_CASE.value: "Duplicate case",
}


class InvalidDecisionRecordError(ValueError):
    pass


class SubmissionType(StrEnum):
    APPLICATION = "Application"
    CLAIM = "Claim"


@dataclass(frozen=True)
class DecisionsReportSourceRecord:
    event_reference: HistoryEventReference
    decided_at: datetime
    actor: str
    actor_type: ActorType
    actor_email_address: str | None
    event_data: dict | None
    laa_reference: str
    application_submitted_at: datetime
    claim_submitted_at: datetime | None = None


@dataclass(frozen=True)
class DecisionsReportRow:
    submission_type: str
    case_reference: str
    claim_reference: str
    decision: str
    submission_date: str
    date_of_decision: str
    time_of_decision: str
    who: str
    refusal_reason: str
    justification: str

    def as_list(self) -> list[str]:
        return [
            self.submission_type,
            self.case_reference,
            self.claim_reference,
            self.decision,
            self.submission_date,
            self.date_of_decision,
            self.time_of_decision,
            self.who,
            self.refusal_reason,
            self.justification,
        ]


def neutralise_csv_formula(value: str) -> str:
    """Stop spreadsheet applications from evaluating free text as a formula."""
    if value.startswith(_FORMULA_TRIGGERS):
        return f"'{value}"
    return value


def build_decisions_report_row(
    record: DecisionsReportSourceRecord,
) -> DecisionsReportRow:
    match record.event_reference:
        case HistoryEventReference.APPLICATION_ASSESSMENT_COMPLETED:
            return _application_row(record)
        case HistoryEventReference.CLAIM_ASSESSMENT_COMPLETED:
            decision = _event_data(record).get("claim_decision")
            justification = _event_data(record).get("decision_justification")
            return _claim_row(record, decision, justification)
        case HistoryEventReference.POA_AUTO_APPROVED:
            return _claim_row(record, _PAY_IN_FULL, None)
        case HistoryEventReference.POA_AUTO_REJECTED:
            return _claim_row(record, _REJECTED, None)
    raise InvalidDecisionRecordError(
        f"Event {record.event_reference} is not a decision event"
    )


def _application_row(record: DecisionsReportSourceRecord) -> DecisionsReportRow:
    data = _event_data(record)
    decision = data.get("merits_decision")
    if decision not in _APPLICATION_DECISIONS:
        raise InvalidDecisionRecordError(f"Unknown application decision {decision!r}")

    refusal_reason = ""
    justification = ""
    if decision == "Refused":
        reason = data.get("refusal_reason")
        if reason not in _REFUSAL_REASON_LABELS:
            raise InvalidDecisionRecordError(f"Unknown refusal reason {reason!r}")
        refusal_reason = _REFUSAL_REASON_LABELS[reason]
        justification = data.get("refusal_justification") or ""

    return _build_row(
        record,
        submission_type=SubmissionType.APPLICATION,
        claim_reference="",
        decision=decision,
        submitted_at=record.application_submitted_at,
        refusal_reason=refusal_reason,
        justification=justification,
    )


def _claim_row(
    record: DecisionsReportSourceRecord,
    decision: str | None,
    justification: str | None,
) -> DecisionsReportRow:
    if decision not in _CLAIM_DECISION_LABELS:
        raise InvalidDecisionRecordError(f"Unknown claim decision {decision!r}")
    claim_reference = _event_data(record).get("claim_reference")
    if not claim_reference:
        raise InvalidDecisionRecordError("Claim decision has no claim reference")
    if record.claim_submitted_at is None:
        raise InvalidDecisionRecordError(
            f"Claim {claim_reference} has no submission date"
        )

    return _build_row(
        record,
        submission_type=SubmissionType.CLAIM,
        claim_reference=claim_reference,
        decision=_CLAIM_DECISION_LABELS[decision],
        submitted_at=record.claim_submitted_at,
        refusal_reason="",
        justification=justification or "",
    )


def _build_row(
    record: DecisionsReportSourceRecord,
    *,
    submission_type: SubmissionType,
    claim_reference: str,
    decision: str,
    submitted_at: datetime,
    refusal_reason: str,
    justification: str,
) -> DecisionsReportRow:
    decided_at = _as_utc(record.decided_at)
    return DecisionsReportRow(
        submission_type=submission_type.value,
        case_reference=record.laa_reference,
        claim_reference=claim_reference,
        decision=decision,
        submission_date=_as_utc(submitted_at).strftime(_DATE_FORMAT),
        date_of_decision=decided_at.strftime(_DATE_FORMAT),
        time_of_decision=decided_at.strftime(_TIME_FORMAT),
        who=neutralise_csv_formula(
            resolve_history_username(
                record.actor_type, record.actor, record.actor_email_address
            )
        ),
        refusal_reason=refusal_reason,
        justification=neutralise_csv_formula(justification),
    )


def _event_data(record: DecisionsReportSourceRecord) -> dict:
    if not isinstance(record.event_data, dict):
        raise InvalidDecisionRecordError("Decision event has no event data")
    return record.event_data


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
