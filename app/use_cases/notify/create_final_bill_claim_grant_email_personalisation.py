"""Build final bill claim paid (granted) email personalisation data."""

from decimal import Decimal

from app.domain.pay_in_full import PayInFullClaim
from app.models.application.index import Application
from app.models.claim.index import Claim
from app.models.gov_notify_templates.final_bill_claim_grant_personalisation import (
    NotifyFinalBillClaimGrantTemplatePersonalisation,
)
from app.use_cases.notify.format_utils import (
    format_amount,
    format_claim_type,
    format_date,
)


def _amount_or_zero(value: Decimal | None) -> Decimal:
    return value if value is not None else Decimal("0.00")


def create_final_bill_claim_grant_email_personalisation(
    claim: Claim,
    application: Application,
    firm_name: str,
    decision_amounts: PayInFullClaim,
) -> NotifyFinalBillClaimGrantTemplatePersonalisation:
    """Build personalisation data for a final bill claim paid notification.

    A pay-in-full decision means the amounts to be paid equal the amounts
    claimed, so the assessed decision amounts are used for the breakdown.
    """

    profit_total = _amount_or_zero(
        decision_amounts.profit_cost_gross
        if decision_amounts.profit_cost_gross is not None
        else decision_amounts.profit_cost_vat_zero
    )
    disbursement_total = _amount_or_zero(
        decision_amounts.disbursement_gross
        if decision_amounts.disbursement_gross is not None
        else decision_amounts.disbursement_vat_zero
    )

    return NotifyFinalBillClaimGrantTemplatePersonalisation(
        ref_number=str(application.laa_reference),
        provider_name=firm_name,
        client_first_name=application.client.client_first_name,
        client_last_name=application.client.client_last_name,
        date_of_claim=format_date(claim.submission_date),
        claim_type=format_claim_type(claim.claim_type_id),
        claim_ref=str(claim.claim_reference),
        claimed_amount=format_amount(profit_total + disbursement_total),
        net_profit_costs=format_amount(
            _amount_or_zero(decision_amounts.profit_cost_net)
        ),
        gross_profit_costs=format_amount(
            _amount_or_zero(decision_amounts.profit_cost_gross)
        ),
        zero_vat_profit_costs=format_amount(
            _amount_or_zero(decision_amounts.profit_cost_vat_zero)
        ),
        net_disbursement_costs=format_amount(
            _amount_or_zero(decision_amounts.disbursement_net)
        ),
        gross_disbursement_costs=format_amount(
            _amount_or_zero(decision_amounts.disbursement_gross)
        ),
        zero_vat_disbursement_costs=format_amount(
            _amount_or_zero(decision_amounts.disbursement_vat_zero)
        ),
    )
