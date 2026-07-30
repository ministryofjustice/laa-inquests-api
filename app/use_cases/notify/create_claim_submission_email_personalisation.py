"""Use case for building claim submission email personalisation data."""

from datetime import datetime

from app.models.application.index import Application
from app.models.claim.index import Claim
from app.models.gov_notify_templates.claim_submit_personalisation import (
    NotifyClaimSubmitTemplatePersonalisation,
)


def _format_submission_date(submission_date: datetime) -> str:
    """Format date into Gov Notify display format like '18 June 2026'."""
    return f"{submission_date.day} {submission_date.strftime('%B %Y')}"


def create_claim_submission_email_personalisation(
    claim: Claim,
    application: Application,
) -> NotifyClaimSubmitTemplatePersonalisation:
    """Build personalisation payload for claim submission notification."""
    client = application.client
    client_name = f"{client.client_first_name} {client.client_last_name}"

    return NotifyClaimSubmitTemplatePersonalisation(
        laa_reference=str(application.laa_reference),
        client_name=client_name,
        submission_date=_format_submission_date(claim.submission_date),
    )