"""Build final bill claim rejection email personalisation data."""

from datetime import UTC, datetime

from app.domain.claim import total_claim_amount
from app.models.application.index import Application
from app.models.claim.index import Claim
from app.models.gov_notify_templates.final_bill_claim_reject_personalisation import (
    NotifyFinalBillClaimRejectTemplatePersonalisation,
)
from app.use_cases.notify.format_utils import (
    format_amount,
    format_claim_type,
    format_date,
)


def create_final_bill_claim_rejection_email_personalisation(
    claim: Claim,
    application: Application,
    justification: str,
    firm_name: str,
) -> NotifyFinalBillClaimRejectTemplatePersonalisation:
    """Build personalisation data for a final bill rejection notification."""

    return NotifyFinalBillClaimRejectTemplatePersonalisation(
        ref_number=str(application.laa_reference),
        provider_name=firm_name,
        client_first_name=application.client.client_first_name,
        client_last_name=application.client.client_last_name,
        date_of_claim=format_date(claim.submission_date),
        claim_type=format_claim_type(claim.claim_type_id),
        claim_ref=str(claim.claim_id),
        claimed_amount=format_amount(
            total_claim_amount(
                claim.total_profit_cost_vat_zero,
                claim.total_profit_cost_gross,
            )
        ),
        reason_for_refusal=justification,
        date_of_rejection=format_date(datetime.now(UTC)),
    )
