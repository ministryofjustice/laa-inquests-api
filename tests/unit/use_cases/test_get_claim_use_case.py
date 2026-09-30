import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.domain.constants.claims import SUBSTANTIVE_CERTIFICATE_AMOUNT
from app.models.application.index import Application
from app.models.claim.enums import (
    ClaimDecisionStatus,
    ClaimType,
    ReasonCode,
)
from app.models.claim.index import (
    Claim,
)
from app.ports.application_lookup_port import ApplicationLookupPort
from app.ports.claim.get_claim_by_id_port import GetClaimByIdPort
from app.ports.claim.get_claim_decision_port import GetClaimDecisionPort
from app.use_cases.exceptions import ApplicationNotFoundError, ClaimNotFoundError
from app.use_cases.get_claim import GetClaimUseCase
from tests.factories.builders import (
    build_claim_cost_template,
    build_claim_decision,
    build_decision_reason,
    build_granted_application,
    build_poa_claim,
)


def _claim(
    application: Application,
    claim_reference: str = "INQC-0000-0001",
    total_funds_remaining_after_claim: Decimal = Decimal(
        SUBSTANTIVE_CERTIFICATE_AMOUNT
    ),
) -> Claim:
    return build_poa_claim(
        claim_reference=claim_reference,
        application_id=application.application_id,
        submission_date=datetime.now(UTC),
        total_funds_remaining_after_claim=total_funds_remaining_after_claim,
    )


def _build_use_case(
    claim=None,
    application=None,
    decision=None,
):
    claim_port = MagicMock(spec=GetClaimByIdPort)
    claim_port.get_claim_by_reference.return_value = claim

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
    application = build_granted_application()
    use_case = _build_use_case(claim=_claim(application), application=application)

    result = use_case.execute("1", "INQC-0000-0001")

    assert result.claim_reference == "INQC-0000-0001"
    assert result.claim_type_id == ClaimType.PAYMENT_ON_ACCOUNT
    assert result.total_profit_cost_net == Decimal("1000.00")


def test_raises_application_not_found_when_application_missing():
    use_case = _build_use_case(
        claim=_claim(build_granted_application()), application=None
    )

    with pytest.raises(ApplicationNotFoundError):
        use_case.execute("999999", "INQC-0000-0001")


def test_raises_claim_not_found_when_claim_missing():
    use_case = _build_use_case(claim=None, application=build_granted_application())

    with pytest.raises(ClaimNotFoundError):
        use_case.execute("1", "INQC-9999-9999")


def test_raises_claim_not_found_when_claim_belongs_to_another_application():
    use_case = _build_use_case(
        claim=_claim(build_granted_application()),
        application=build_granted_application(),
    )

    with pytest.raises(ClaimNotFoundError):
        use_case.execute("2", "INQC-0000-0001")


def test_maps_substantive_cost_limitation_from_application():
    application = build_granted_application(substantive_cost_limitation=25000)
    use_case = _build_use_case(claim=_claim(application), application=application)

    result = use_case.execute("1", "INQC-0000-0001")

    assert result.substantive_cost_limitation == 25000


def test_includes_claim_decision_when_present():
    application = build_granted_application()
    claim = _claim(application)
    decision = build_claim_decision(
        claim_decision_id=7,
        claim_id=claim.claim_id,
        decision=ClaimDecisionStatus.REJECT,
        decision_reasons=[
            build_decision_reason(
                decision_reason_id=1,
                claim_decision_id=7,
                reason_code=ReasonCode.MAX_POA_CLAIMS_EXCEEDED,
                justification="Too many",
            )
        ],
    )
    use_case = _build_use_case(claim=claim, application=application, decision=decision)

    result = use_case.execute("1", "INQC-0000-0001")

    assert result.claim_decision is not None
    assert result.claim_decision.claim_decision_id == 7
    assert result.claim_decision.decision == ClaimDecisionStatus.REJECT
    assert result.claim_decision.decision_reasons[0].reason_code == (
        ReasonCode.MAX_POA_CLAIMS_EXCEEDED
    )
    assert result.claim_decision.decision_reasons[0].justification == "Too many"


def test_claim_decision_is_none_when_absent():
    application = build_granted_application()
    use_case = _build_use_case(
        claim=_claim(application), application=application, decision=None
    )

    result = use_case.execute("1", "INQC-0000-0001")

    assert result.claim_decision is None


def test_cost_template_file_is_populated_when_present():
    file_id = uuid.uuid4()
    application = build_granted_application()
    claim = _claim(application)
    claim.claim_cost_template = build_claim_cost_template(
        claim_id=claim.claim_id,
        claim_cost_template_file_id=file_id,
        claim_cost_template_file_name="final_bill_costs.xlsx",
    )
    use_case = _build_use_case(claim=claim, application=application)

    result = use_case.execute("1", "INQC-0000-0001")

    assert result.claim_cost_template_file is not None
    assert result.claim_cost_template_file.claim_cost_template_file_id == file_id
    assert (
        result.claim_cost_template_file.claim_cost_template_file_name
        == "final_bill_costs.xlsx"
    )


def test_cost_template_file_is_none_when_absent():
    application = build_granted_application()
    use_case = _build_use_case(claim=_claim(application), application=application)

    result = use_case.execute("1", "INQC-0000-0001")

    assert result.claim_cost_template_file is None


def test_returns_stored_total_funds_remaining_from_claim():
    application = build_granted_application()
    use_case = _build_use_case(
        claim=_claim(application, total_funds_remaining_after_claim=Decimal("8800.00")),
        application=application,
    )

    result = use_case.execute("1", "INQC-0000-0001")

    assert result.total_funds_remaining_after_claim == Decimal("8800.00")


def test_total_funds_remaining_defaults_to_certificate_amount_when_not_set():
    application = build_granted_application()
    use_case = _build_use_case(
        claim=_claim(application),
        application=application,
    )

    result = use_case.execute("1", "INQC-0000-0001")

    assert result.total_funds_remaining_after_claim == Decimal(
        SUBSTANTIVE_CERTIFICATE_AMOUNT
    )
