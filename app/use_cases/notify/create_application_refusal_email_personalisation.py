"""Use case for building refusal email personalisation data from Application objects."""

from app.models.application.index import Application, ApplicationProceeding
from app.models.gov_notify_templates.application_refuse_personalisation import (
    NotifyApplicationRefuseTemplatePersonalisation,
)
from app.use_cases.notify.format_utils import format_submitted_at


def create_application_refusal_email_personalisation(
    application: Application,
    proceeding: ApplicationProceeding,
) -> NotifyApplicationRefuseTemplatePersonalisation:
    """Build personalisation payload for refusal decision notification."""

    return NotifyApplicationRefuseTemplatePersonalisation(
        client_first_name=application.client.client_first_name,
        client_last_name=application.client.client_last_name,
        laa_reference=str(application.laa_reference),
        application_submitted_at=format_submitted_at(application.created_at),
        reason_for_refusal=proceeding.reason_for_refusal,
        justification=proceeding.justification,
    )
