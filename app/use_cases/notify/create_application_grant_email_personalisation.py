"""Use case for building grant email personalisation data from Application objects."""

from typing import Any
from app.models.application.index import Application, ApplicationProceeding
from app.models.gov_notify_templates.application_grant_personalisation import (
    NotifyApplicationGrantTemplatePersonalisation,
)


def _format_issue_date(issue_date) -> str:
    """Format date into Gov Notify display format like '18 June 2026'."""
    return f"{issue_date.day} {issue_date.strftime('%B %Y')}"


def create_application_grant_email_personalisation(
    application: Application,
    proceeding: ApplicationProceeding,
    certificate_payload: dict[str, Any],
) -> NotifyApplicationGrantTemplatePersonalisation:
    """Build personalisation payload for grant decision notification."""

    return NotifyApplicationGrantTemplatePersonalisation(
        laa_reference=str(application.laa_reference),
        issue_date=_format_issue_date(proceeding.certificate_issue_date),
        link_to_file=certificate_payload,
    )
