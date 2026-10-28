from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.models.audit.enums import AuditEventReference


class EventDescriptionError(ValueError):
    def __init__(self, event_reference: str, message: str) -> None:
        super().__init__(message)
        self.event_reference = event_reference


class UnknownEventReferenceError(EventDescriptionError):
    pass


class InvalidEventDataError(EventDescriptionError):
    pass


@dataclass(frozen=True)
class EventDescription:
    title: str
    description: str


EventData = dict[str, Any] | None
_DescriptionBuilder = Callable[[EventData], str]


def format_enum(value: str) -> str:
    return value.replace("_", " ").lower().capitalize()


def _text(event_data: EventData, key: str) -> str:
    return str((event_data or {})[key])


def _join_values(event_data: EventData, key: str) -> str:
    value = (event_data or {})[key]
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value)


def _application_assessment(event_data: EventData) -> str:
    decision = _text(event_data, "merits_decision").lower()
    heading = f"Application {decision}"
    if decision != "refused":
        return heading
    reason = format_enum(_text(event_data, "refusal_reason"))
    return f"{heading}\n{reason}\n{_text(event_data, 'refusal_justification')}"


def _claim_assessment(event_data: EventData) -> str:
    claim_type = format_enum(_text(event_data, "claim_type"))
    decision = format_enum(_text(event_data, "claim_decision")).lower()
    justification = (event_data or {}).get("decision_justification")
    has_justification = isinstance(justification, str) and justification.strip()
    if decision == "rejected" and has_justification:
        return f"{claim_type} claim {decision}\n{justification}"
    return f"{claim_type} claim {decision}: {_text(event_data, 'claim_reference')}"


def _interested_parties(event_data: EventData) -> str:
    return (
        "Interested parties updated from "
        f"{_join_values(event_data, 'old_public_bodies')} to "
        f"{_join_values(event_data, 'new_public_bodies')}"
    )


def _claim_received(event_data: EventData) -> str:
    return (
        f"{format_enum(_text(event_data, 'claim_type'))} claim received: "
        f"{_text(event_data, 'claim_reference')}"
    )


_DYNAMIC_EVENTS: dict[str, tuple[str, _DescriptionBuilder]] = {
    "EVT-BUS-X-001": (
        "Case note added",
        lambda data: f"Caseworker note added\n{_text(data, 'note_text')}",
    ),
    "EVT-BUS-APP-002": ("Application assessment complete", _application_assessment),
    "EVT-BUS-APP-004": ("Interested party updated", _interested_parties),
    "EVT-BUS-CLM-001": ("Claim submitted", _claim_received),
    "EVT-BUS-CLM-002": ("Claim assessment complete", _claim_assessment),
    "EVT-BUS-CLM-003": (
        "POA auto-approved",
        lambda data: f"POA claim {_text(data, 'claim_reference')} auto-approved",
    ),
    "EVT-BUS-CLM-004": (
        "POA auto-rejected",
        lambda data: f"POA claim {_text(data, 'claim_reference')} auto-rejected",
    ),
    AuditEventReference.REPORT_DOWNLOADED: (
        "Report downloaded",
        lambda data: f"{_text(data, 'report_name')} downloaded",
    ),
}

_STATIC_EVENTS: dict[str, EventDescription] = {
    "EVT-BUS-APP-001": EventDescription(
        "Application submitted", "Application received"
    ),
    "EVT-BUS-APP-003": EventDescription("Certificate created", "Certificate created"),
    "EVT-COM-APP-001": EventDescription(
        "Application submission confirmation",
        "Application submission confirmation sent",
    ),
    "EVT-COM-APP-002": EventDescription(
        "Application granted (Email)", "Application granted email sent"
    ),
    "EVT-COM-APP-003": EventDescription(
        "Application granted (Letter)", "Application granted letter sent"
    ),
    "EVT-COM-APP-004": EventDescription(
        "Application refused", "Application refused email sent"
    ),
    "EVT-COM-CLM-001": EventDescription(
        "Claim submission confirmation", "Claim submission confirmation sent"
    ),
    "EVT-COM-CLM-002": EventDescription("Claim approved", "Claim approved email sent"),
    "EVT-COM-CLM-003": EventDescription("Claim Rejected", "Claim rejection email sent"),
    AuditEventReference.APPLICATION_VIEWED: EventDescription(
        "Application viewed", "Application viewed"
    ),
    AuditEventReference.CERTIFICATE_VIEWED: EventDescription(
        "Certificate viewed", "Certificate viewed"
    ),
}


def describe_event(event_reference: str, event_data: EventData) -> EventDescription:
    if event_reference in _DYNAMIC_EVENTS:
        title, build_description = _DYNAMIC_EVENTS[event_reference]
        try:
            return EventDescription(title, build_description(event_data))
        except KeyError as exc:
            raise InvalidEventDataError(
                event_reference, f"Event {event_reference} is missing event data {exc}"
            ) from exc
    if event_reference in _STATIC_EVENTS:
        return _STATIC_EVENTS[event_reference]
    raise UnknownEventReferenceError(
        event_reference, f"Unknown event reference {event_reference}"
    )
