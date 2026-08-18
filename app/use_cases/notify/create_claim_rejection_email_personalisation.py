"""Use case for building rejection email personalisation data from Claim objects."""

from datetime import UTC, datetime
from decimal import Decimal

from app.models.application.index import Application
from app.models.claim.index import Claim
from app.models.gov_notify_templates.claim_reject_personalisation import (
    NotifyClaimRejectTemplatePersonalisation,
)
from app.use_cases.notify.format_utils import format_claim_type, format_submitted_at


def _format_amount(value: Decimal | None) -> str:
    """Format a monetary amount with thousands separators and two decimal places."""
    return f"{value or Decimal(0):,.2f}"


def _claimed_and_vat_amounts(claim: Claim) -> tuple[Decimal, Decimal]:
    if claim.total_profit_cost_vat_zero is not None:
        return claim.total_profit_cost_vat_zero, Decimal(0)

    gross = claim.total_profit_cost_gross or Decimal(0)
    net = claim.total_profit_cost_net or Decimal(0)
    return gross, gross - net


def create_claim_rejection_email_personalisation(
    claim: Claim,
    application: Application,
    justification: str,
    firm_name: str,
) -> NotifyClaimRejectTemplatePersonalisation:
    """Build personalisation payload for claim rejection notification."""

    claimed_amount, vat_amount = _claimed_and_vat_amounts(claim)

    return NotifyClaimRejectTemplatePersonalisation(
        cert_ref_number=str(application.laa_reference),
        provider_name=firm_name,
        client_first_name=application.client.client_first_name,
        client_last_name=application.client.client_last_name,
        claim_submitted_at=format_submitted_at(claim.submission_date),
        claim_type=format_claim_type(claim.claim_type_id),
        claimed_amount=_format_amount(claimed_amount),
        VAT_amount=_format_amount(vat_amount),
        date_of_rejection=format_submitted_at(datetime.now(UTC)),
        justification=justification,
    )
