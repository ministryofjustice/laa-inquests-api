"""Use case for building rejection email personalisation data from Claim objects."""

from datetime import UTC, datetime

from app.domain.claim import total_claim_amount
from app.models.application.index import Application
from app.models.claim.index import Claim
from app.models.gov_notify_templates.claim_reject_personalisation import (
    NotifyClaimRejectTemplatePersonalisation,
)
from app.use_cases.notify.format_utils import (
    format_amount,
    format_claim_type,
    format_submitted_at,
)


def create_claim_rejection_email_personalisation(
    claim: Claim,
    application: Application,
    justification: str,
    firm_name: str,
) -> NotifyClaimRejectTemplatePersonalisation:
    """Build personalisation payload for claim rejection notification."""

    return NotifyClaimRejectTemplatePersonalisation(
        cert_ref_number=str(application.laa_reference),
        provider_name=firm_name,
        client_first_name=application.client.client_first_name,
        client_last_name=application.client.client_last_name,
        claim_submitted_at=format_submitted_at(claim.submission_date),
        claim_type=format_claim_type(claim.claim_type_id),
        total_claim_amount=format_amount(
            total_claim_amount(
                claim.total_profit_cost_vat_zero, claim.total_profit_cost_gross
            )
        ),
        date_of_rejection=format_submitted_at(datetime.now(UTC)),
        justification=justification,
    )
