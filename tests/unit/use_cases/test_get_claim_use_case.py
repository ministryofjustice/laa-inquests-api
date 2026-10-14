import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.domain.claim_evidence import ClaimEvidence as DomainClaimEvidence
from app.domain.constants.claims import SUBSTANTIVE_CERTIFICATE_AMOUNT
from app.models.claim.enums import (
    ClaimDecisionStatus,
    ClaimStatus,
    ClaimType,
    POAType,
    ReasonCode,
)
from app.models.claim.index import (
    Claim,
    ClaimCostTemplate,
    ClaimDecision,
    ClaimDecisionAmount,
    DecisionReason,
)
from app.ports.application_lookup_port import ApplicationLookupPort
from app.ports.claim.get_claim_by_id_port import GetClaimByIdPort
from app.ports.claim.get_claim_decision_amount_port import (
    GetClaimDecisionAmountPort,
)
from app.ports.claim.get_claim_decision_port import GetClaimDecisionPort
from app.ports.claim.get_claim_evidence_port import GetClaimEvidencePort
from app.use_cases.exceptions import ApplicationNotFoundError, ClaimNotFoundError
from app.use_cases.get_claim import GetClaimUseCase


def _claim(
    claim_id: int = 1,
    application_id: int = 1,
    claim_reference: str = "INQC-0000-0001",
    total_funds_remaining_after_claim: Decimal = Decimal(
        SUBSTANTIVE_CERTIFICATE_AMOUNT
    ),
) -> Claim:
    return Claim(
        claim_id=claim_id,
        claim_reference=claim_reference,
        application_id=application_id,
        claim_type_id=ClaimType.PAYMENT_ON_ACCOUNT,
        status_id=ClaimStatus.SUBMITTED,
        submission_date=datetime.now(UTC),
        total_profit_cost_net=Decimal("1000.00"),
        total_profit_cost_gross=Decimal("1200.00"),
        total_profit_cost_vat_zero=Decimal("500.00"),
        total_funds_remaining_after_claim=total_funds_remaining_after_claim,
        poa_type_id=POAType.PROFIT_COST,
    )


def _application(application_id: int = 1, substantive_cost_limitation: int = 10000):
    application = MagicMock()
    application.application_id = application_id
    application.proceeding.substantive_cost_limitation = substantive_cost_limitation
    return application


def _build_use_case(
    claim=None,
    application=None,
    decision=None,
    claim_evidence=None,
    decision_amount=None,
):
    claim_port = MagicMock(spec=GetClaimByIdPort)
    claim_port.get_claim_by_reference.return_value = claim

    decision_port = MagicMock(spec=GetClaimDecisionPort)
    decision_port.get_claim_decision_by_claim_id.return_value = decision

    lookup_port = MagicMock(spec=ApplicationLookupPort)
    lookup_port.get_application_by_laa_reference.return_value = application

    evidence_port = MagicMock(spec=GetClaimEvidencePort)
    evidence_port.get_claim_evidence_by_id.return_value = claim_evidence

    decision_amount_port = MagicMock(spec=GetClaimDecisionAmountPort)
    decision_amount_port.get_claim_decision_amount_by_decision_id.return_value = (
        decision_amount
    )

    return GetClaimUseCase(
        get_claim_by_id_port=claim_port,
        get_claim_evidence_port=evidence_port,
        get_claim_decision_amount_port=decision_amount_port,
        get_claim_decision_port=decision_port,
        application_lookup_port=lookup_port,
    )


def test_returns_response_for_valid_application_and_claim():
    use_case = _build_use_case(claim=_claim(), application=_application())

    result = use_case.execute("1", "INQC-0000-0001")

    assert result.claim_reference == "INQC-0000-0001"
    assert result.claim_type_id == ClaimType.PAYMENT_ON_ACCOUNT
    assert result.total_profit_cost_net == Decimal("1000.00")


def test_raises_application_not_found_when_application_missing():
    use_case = _build_use_case(claim=_claim(), application=None)

    with pytest.raises(ApplicationNotFoundError):
        use_case.execute("999999", "INQC-0000-0001")


def test_raises_claim_not_found_when_claim_missing():
    use_case = _build_use_case(claim=None, application=_application())

    with pytest.raises(ClaimNotFoundError):
        use_case.execute("1", "INQC-9999-9999")


def test_raises_claim_not_found_when_claim_belongs_to_another_application():
    use_case = _build_use_case(
        claim=_claim(claim_id=1, application_id=1),
        application=_application(application_id=2),
    )

    with pytest.raises(ClaimNotFoundError):
        use_case.execute("2", "INQC-0000-0001")


def test_maps_substantive_cost_limitation_from_application():
    use_case = _build_use_case(
        claim=_claim(),
        application=_application(substantive_cost_limitation=25000),
    )

    result = use_case.execute("1", "INQC-0000-0001")

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

    result = use_case.execute("1", "INQC-0000-0001")

    assert result.claim_decision is not None
    assert result.claim_decision.claim_decision_id == 7
    assert result.claim_decision.decision == ClaimDecisionStatus.REJECT
    assert result.claim_decision.decision_reasons[0].reason_code == (
        ReasonCode.MAX_POA_CLAIMS_EXCEEDED
    )
    assert result.claim_decision.decision_reasons[0].justification == "Too many"


def test_includes_decision_amount_when_the_decision_has_one():
    decision = ClaimDecision(
        claim_decision_id=7, claim_id=1, decision=ClaimDecisionStatus.PAY_IN_FULL
    )
    amount = ClaimDecisionAmount(
        claim_decision_id=7,
        profit_cost_net=Decimal("1000.00"),
        profit_cost_gross=Decimal("1200.00"),
        disbursement_net=Decimal("100.00"),
        disbursement_gross=Decimal("120.00"),
    )
    use_case = _build_use_case(
        claim=_claim(),
        application=_application(),
        decision=decision,
        decision_amount=amount,
    )

    result = use_case.execute("1", "INQC-0000-0001")

    assert result.claim_decision.decision_amount is not None
    assert result.claim_decision.decision_amount.profit_cost_net == Decimal("1000.00")
    assert result.claim_decision.decision_amount.profit_cost_gross == Decimal("1200.00")
    assert result.claim_decision.decision_amount.disbursement_net == Decimal("100.00")
    assert result.claim_decision.decision_amount.disbursement_gross == Decimal("120.00")


def test_decision_amount_is_none_when_the_decision_has_none():
    decision = ClaimDecision(
        claim_decision_id=7, claim_id=1, decision=ClaimDecisionStatus.REJECT
    )
    use_case = _build_use_case(
        claim=_claim(), application=_application(), decision=decision
    )

    result = use_case.execute("1", "INQC-0000-0001")

    assert result.claim_decision is not None
    assert result.claim_decision.decision_amount is None


def test_does_not_look_up_a_decision_amount_when_there_is_no_decision():
    use_case = _build_use_case(claim=_claim(), application=_application())

    use_case.execute("1", "INQC-0000-0001")

    use_case.get_claim_decision_amount_port.get_claim_decision_amount_by_decision_id.assert_not_called()


def test_claim_decision_is_none_when_absent():
    use_case = _build_use_case(
        claim=_claim(), application=_application(), decision=None
    )

    result = use_case.execute("1", "INQC-0000-0001")

    assert result.claim_decision is None


def test_cost_template_file_is_populated_when_present():
    file_id = uuid.uuid4()
    claim = _claim()
    claim.claim_cost_template = ClaimCostTemplate(
        claim_id=claim.claim_id,
        claim_cost_template_file_id=file_id,
        claim_cost_template_file_name="final_bill_costs.xlsx",
    )
    use_case = _build_use_case(claim=claim, application=_application())

    result = use_case.execute("1", "INQC-0000-0001")

    assert result.claim_cost_template_file is not None
    assert result.claim_cost_template_file.claim_cost_template_file_id == file_id
    assert (
        result.claim_cost_template_file.claim_cost_template_file_name
        == "final_bill_costs.xlsx"
    )


def test_cost_template_file_includes_file_size_from_stored_evidence():
    file_id = uuid.uuid4()
    claim = _claim()
    claim.claim_cost_template = ClaimCostTemplate(
        claim_id=1,
        claim_cost_template_file_id=file_id,
        claim_cost_template_file_name="final_bill_costs.xlsx",
    )
    use_case = _build_use_case(
        claim=claim,
        application=_application(),
        claim_evidence=DomainClaimEvidence(
            sds_file_name="template_abc123.xlsx",
            file_name="final_bill_costs.xlsx",
            file_size=20480,
        ),
    )

    result = use_case.execute("1", "INQC-0000-0001")

    assert result.claim_cost_template_file.file_size == 20480


def test_cost_template_file_size_is_none_when_evidence_not_found():
    claim = _claim()
    claim.claim_cost_template = ClaimCostTemplate(
        claim_id=1,
        claim_cost_template_file_id=uuid.uuid4(),
        claim_cost_template_file_name="final_bill_costs.xlsx",
    )
    use_case = _build_use_case(claim=claim, application=_application())

    result = use_case.execute("1", "INQC-0000-0001")

    assert result.claim_cost_template_file.file_size is None


def test_cost_template_file_is_none_when_absent():
    use_case = _build_use_case(claim=_claim(), application=_application())

    result = use_case.execute("1", "INQC-0000-0001")

    assert result.claim_cost_template_file is None


def test_returns_stored_total_funds_remaining_from_claim():
    use_case = _build_use_case(
        claim=_claim(total_funds_remaining_after_claim=Decimal("8800.00")),
        application=_application(),
    )

    result = use_case.execute("1", "INQC-0000-0001")

    assert result.total_funds_remaining_after_claim == Decimal("8800.00")


def test_total_funds_remaining_defaults_to_certificate_amount_when_not_set():
    use_case = _build_use_case(
        claim=_claim(),
        application=_application(),
    )

    result = use_case.execute("1", "INQC-0000-0001")

    assert result.total_funds_remaining_after_claim == Decimal(
        SUBSTANTIVE_CERTIFICATE_AMOUNT
    )
