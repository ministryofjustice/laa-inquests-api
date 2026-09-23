"""Use case for building claim submission email personalisation data."""

from decimal import Decimal

from app.models.application.index import Application
from app.models.claim.index import Claim
from app.models.gov_notify_templates.claim_submit_personalisation import (
    NotifyClaimSubmitTemplatePersonalisation,
)
from app.use_cases.notify.format_utils import (
    format_amount,
    format_claim_type,
    format_date,
)


def create_claim_submission_email_personalisation(
    claim: Claim,
    application: Application,
    firm_name: str,
) -> NotifyClaimSubmitTemplatePersonalisation:
    """Build personalisation payload for claim submission notification."""
    return NotifyClaimSubmitTemplatePersonalisation(
        provider_name=firm_name,
        ref_number=str(application.laa_reference),
        client_first_name=application.client.client_first_name,
        client_last_name=application.client.client_last_name,
        date_of_claim=format_date(claim.submission_date),
        claim_type=format_claim_type(claim.claim_type_id),
        claim_reference=str(claim.claim_reference),
        claimed_amount=format_amount(claim.total_profit_cost_gross or Decimal("0.00")),
    )
