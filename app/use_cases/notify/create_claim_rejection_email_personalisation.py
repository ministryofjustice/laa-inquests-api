"""Use case for building rejection email personalisation data from Claim objects."""

from app.models.application.index import Application
from app.models.claim.index import Claim
from app.models.gov_notify_templates.claim_reject_personalisation import (
    NotifyClaimRejectTemplatePersonalisation,
)


def _format_submitted_at(submitted_at) -> str:
    """Format datetime into Gov Notify display format like '18 June 2026 14:03 UTC'."""
    return f"{submitted_at.day} {submitted_at.strftime('%B %Y %H:%M UTC')}"


def create_claim_rejection_email_personalisation(
    claim: Claim,
    application: Application,
    justification: str,
) -> NotifyClaimRejectTemplatePersonalisation:
    """Build personalisation payload for claim rejection notification."""

    return NotifyClaimRejectTemplatePersonalisation(
        laa_reference=str(application.laa_reference),
        claim_id=str(claim.claim_id),
        client_first_name=application.client.client_first_name,
        client_last_name=application.client.client_last_name,
        claim_submitted_at=_format_submitted_at(claim.submission_date),
        justification=justification,
    )
