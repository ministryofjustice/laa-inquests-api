"""Use case for building grant email personalisation data from Claim objects."""

from decimal import Decimal

from app.models.application.index import Application
from app.models.claim.index import Claim
from app.models.gov_notify_templates.claim_grant_personalisation import (
    NotifyClaimGrantTemplatePersonalisation,
)
from app.use_cases.notify.format_utils import (
    format_amount,
    format_claim_type,
    format_date,
)


def create_claim_grant_email_personalisation(
    claim: Claim,
    application: Application,
    firm_name: str,
) -> NotifyClaimGrantTemplatePersonalisation:
    """Build personalisation payload for POA claim grant notification."""

    return NotifyClaimGrantTemplatePersonalisation(
        ref_number=str(application.laa_reference),
        provider_name=firm_name,
        client_first_name=application.client.client_first_name,
        client_last_name=application.client.client_last_name,
        date_of_claim=format_date(claim.submission_date),
        claim_type=format_claim_type(claim.claim_type_id),
        claim_ref=str(claim.claim_id),
        zero_vat_POA_costs=format_amount(
            claim.total_profit_cost_vat_zero or Decimal("0.00")
        ),
        net_POA_costs=format_amount(claim.total_profit_cost_net or Decimal("0.00")),
        gross_POA_costs=format_amount(claim.total_profit_cost_gross or Decimal("0.00")),
    )
