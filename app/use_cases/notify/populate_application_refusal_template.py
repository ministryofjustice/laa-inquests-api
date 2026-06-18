"""Use case for building refusal email personalisation data from Application objects."""

from app.models.application.index import Application, ApplicationProceeding
from app.models.gov_notify_templates.application_refuse_personalisation import (
    NotifyApplicationRefuseTemplatePersonalisation,
)


def _format_submitted_at(submitted_at) -> str:
    """Format datetime into Gov Notify display format like '18 June 2026 14:03 UTC'."""
    return f"{submitted_at.day} {submitted_at.strftime('%B %Y %H:%M UTC')}"


def populate_application_refusal_template(
    application: Application,
    proceeding: ApplicationProceeding,
) -> NotifyApplicationRefuseTemplatePersonalisation:
    """Build personalisation payload for refusal decision notification."""
    reason_for_refusal = proceeding.reason_for_refusal or ""

    return NotifyApplicationRefuseTemplatePersonalisation(
        client_first_name=application.client.client_first_name,
        client_last_name=application.client.client_last_name,
        laa_reference=str(application.laa_reference),
        application_submitted_at=_format_submitted_at(application.created_at),
        reason_for_refusal=reason_for_refusal,
        justification=proceeding.justification or "",
    )
