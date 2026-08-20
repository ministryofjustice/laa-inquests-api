from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.domain.constants.claims import SUBSTANTIVE_CERTIFICATE_AMOUNT
from app.models.claim.enums import (
    ClaimDecisionStatus,
    ClaimStatus,
    ClaimType,
    POAType,
    ReasonCode,
)
from app.models.claim.index import Claim, ClaimDecision, DecisionReason
from app.ports.application_lookup_port import ApplicationLookupPort
from app.ports.claim.get_claim_by_id_port import GetClaimByIdPort
from app.ports.claim.get_claim_decision_port import GetClaimDecisionPort
from app.use_cases.exceptions import ApplicationNotFoundError, ClaimNotFoundError
from app.use_cases.get_claim import GetClaimUseCase


def _claim(
    claim_id: int = 1,
    laa_reference: int = 1,
    total_funds_remaining_after_claim: Decimal = Decimal(
        SUBSTANTIVE_CERTIFICATE_AMOUNT
    ),
) -> Claim:
    return Claim(
        claim_id=claim_id,
        laa_reference=laa_reference,
        claim_type_id=ClaimType.PAYMENT_ON_ACCOUNT,
        status_id=ClaimStatus.SUBMITTED,
        submission_date=datetime.now(UTC),
        total_profit_cost_net=Decimal("1000.00"),
        total_profit_cost_gross=Decimal("1200.00"),
        total_profit_cost_vat_zero=Decimal("500.00"),
        total_funds_remaining_after_claim=total_funds_remaining_after_claim,
        poa_type_id=POAType.PROFIT_COST,
    )


def _application(laa_reference: int = 1, substantive_cost_limitation: int = 10000):
    application = MagicMock()
    application.laa_reference = laa_reference
    application.proceeding.substantive_cost_limitation = substantive_cost_limitation
    return application


def _build_use_case(
    claim=None,
    application=None,
    decision=None,
):
    claim_port = MagicMock(spec=GetClaimByIdPort)
    claim_port.get_claim_by_id.return_value = claim

    decision_port = MagicMock(spec=GetClaimDecisionPort)
    decision_port.get_claim_decision_by_claim_id.return_value = decision

    lookup_port = MagicMock(spec=ApplicationLookupPort)
    lookup_port.get_application_by_laa_reference.return_value = application

    return GetClaimUseCase(
        get_claim_by_id_port=claim_port,
        get_claim_decision_port=decision_port,
        application_lookup_port=lookup_port,
    )


def test_returns_response_for_valid_application_and_claim():
    use_case = _build_use_case(claim=_claim(), application=_application())

    result = use_case.execute("1", 1)

    assert result.claim_id == 1
    assert result.claim_type_id == ClaimType.PAYMENT_ON_ACCOUNT
    assert result.total_profit_cost_net == Decimal("1000.00")


def test_raises_application_not_found_when_application_missing():
    use_case = _build_use_case(claim=_claim(), application=None)

    with pytest.raises(ApplicationNotFoundError):
        use_case.execute("999999", 1)


def test_raises_claim_not_found_when_claim_missing():
    use_case = _build_use_case(claim=None, application=_application())

    with pytest.raises(ClaimNotFoundError):
        use_case.execute("1", 999999)


def test_raises_claim_not_found_when_claim_belongs_to_another_application():
    use_case = _build_use_case(
        claim=_claim(claim_id=1, laa_reference=1),
        application=_application(laa_reference=2),
    )

    with pytest.raises(ClaimNotFoundError):
        use_case.execute("2", 1)


def test_maps_substantive_cost_limitation_from_application():
    use_case = _build_use_case(
        claim=_claim(),
        application=_application(substantive_cost_limitation=25000),
    )

    result = use_case.execute("1", 1)

    assert result.substantive_cost_limitation == 25000


def test_includes_claim_decision_when_present():
    decision = ClaimDecision(
        claim_decision_id=7,
        claim_id=1,
        decision=ClaimDecisionStatus.REJECT,
        decision_reasons=[
            DecisionReason(
                decision_reason_id=1,
                claim_decision_id=7,
                reason_code=ReasonCode.MAX_POA_CLAIMS_EXCEEDED,
                justification="Too many",
            )
        ],
    )
    use_case = _build_use_case(
        claim=_claim(), application=_application(), decision=decision
    )

    result = use_case.execute("1", 1)

    assert result.claim_decision is not None
    assert result.claim_decision.claim_decision_id == 7
    assert result.claim_decision.decision == ClaimDecisionStatus.REJECT
    assert result.claim_decision.decision_reasons[0].reason_code == (
        ReasonCode.MAX_POA_CLAIMS_EXCEEDED
    )
    assert result.claim_decision.decision_reasons[0].justification == "Too many"


def test_claim_decision_is_none_when_absent():
    use_case = _build_use_case(
        claim=_claim(), application=_application(), decision=None
    )

    result = use_case.execute("1", 1)

    assert result.claim_decision is None


def test_returns_stored_total_funds_remaining_from_claim():
    use_case = _build_use_case(
        claim=_claim(total_funds_remaining_after_claim=Decimal("8800.00")),
        application=_application(),
    )

    result = use_case.execute("1", 1)

    assert result.total_funds_remaining_after_claim == Decimal("8800.00")


def test_total_funds_remaining_defaults_to_certificate_amount_when_not_set():
    use_case = _build_use_case(
        claim=_claim(),
        application=_application(),
    )

    result = use_case.execute("1", 1)

    assert result.total_funds_remaining_after_claim == Decimal(
        SUBSTANTIVE_CERTIFICATE_AMOUNT
    )
