from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.models.audit.enums import AuditEventReference, ReportType
from app.models.history.enums import ActorType

SYSTEM_USERNAME = "System"
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


@dataclass(frozen=True)
class AuditTrailEvent:
    occurred_at: datetime
    event_reference: str
    username: str
    laa_reference: str | None = None
    firm_code: str | None = None
    office_id: str | None = None
    event_data: dict[str, Any] | None = None


def csv_safe(value: str) -> str:
    """Stops spreadsheet tools from evaluating a cell as a formula."""
    return f"'{value}" if value.startswith(_FORMULA_PREFIXES) else value


def resolve_history_username(
    actor_type: ActorType, actor: str, actor_email_address: str | None
) -> str:
    if actor_type == ActorType.SYSTEM:
        return SYSTEM_USERNAME
    if actor_type == ActorType.CASEWORKER:
        # Caseworker events recorded before emails were stored have none to report.
        return actor_email_address or ""
    return actor


def history_event(
    occurred_at: datetime,
    event_reference: str,
    actor_type: ActorType,
    actor: str,
    actor_email_address: str | None,
    laa_reference: str | None,
    firm_code: str | None,
    office_id: str | None,
    event_data: dict[str, Any] | None,
) -> AuditTrailEvent:
    is_provider_action = actor_type == ActorType.PROVIDER
    return AuditTrailEvent(
        occurred_at=occurred_at,
        event_reference=event_reference,
        username=resolve_history_username(actor_type, actor, actor_email_address),
        laa_reference=laa_reference,
        firm_code=firm_code if is_provider_action else None,
        office_id=office_id if is_provider_action else None,
        event_data=event_data,
    )


def application_overview_view_event(
    occurred_at: datetime, user_email_address: str, laa_reference: str
) -> AuditTrailEvent:
    return AuditTrailEvent(
        occurred_at=occurred_at,
        event_reference=AuditEventReference.APPLICATION_VIEWED.value,
        username=user_email_address,
        laa_reference=laa_reference,
    )


def application_certificate_view_event(
    occurred_at: datetime, user_email_address: str, laa_reference: str
) -> AuditTrailEvent:
    return AuditTrailEvent(
        occurred_at=occurred_at,
        event_reference=AuditEventReference.CERTIFICATE_VIEWED.value,
        username=user_email_address,
        laa_reference=laa_reference,
    )


def report_download_event(
    occurred_at: datetime, user_email_address: str, report_type: ReportType
) -> AuditTrailEvent:
    return AuditTrailEvent(
        occurred_at=occurred_at,
        event_reference=AuditEventReference.REPORT_DOWNLOADED.value,
        username=user_email_address,
        event_data={"report_name": report_type.value},
    )
