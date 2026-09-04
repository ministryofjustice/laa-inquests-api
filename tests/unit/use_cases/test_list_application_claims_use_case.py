from unittest.mock import MagicMock

import pytest

from app.models.claim.enums import ClaimDecisionStatus, ClaimStatus, ClaimType
from app.models.claim.index import Claim, ClaimDecision
from app.ports.application_lookup_port import ApplicationLookupPort
from app.ports.claim.get_claim_decision_port import GetClaimDecisionPort
from app.ports.claim.get_claims_for_application_port import (
    GetClaimsForApplicationPort,
)
from app.use_cases.exceptions import ApplicationNotFoundError
from app.use_cases.list_application_claims import ListApplicationClaimsUseCase


def _claim(claim_id: int, status: ClaimStatus) -> Claim:
    return Claim(
        claim_id=claim_id,
        application_id=1,
        claim_type_id=ClaimType.PAYMENT_ON_ACCOUNT,
        status_id=status,
    )


def _build_use_case(claims_port, lookup_port=None, decision_port=None):
    if lookup_port is None:
        lookup_port = MagicMock(spec=ApplicationLookupPort)
        application = MagicMock(application_id=1)
        lookup_port.get_application_by_laa_reference.return_value = application
    if decision_port is None:
        decision_port = MagicMock(spec=GetClaimDecisionPort)
        decision_port.get_claim_decision_by_claim_id.return_value = None
    return ListApplicationClaimsUseCase(
        get_claims_for_application_port=claims_port,
        get_claim_decision_port=decision_port,
        application_lookup_port=lookup_port,
    )


def test_assessed_true_returns_only_non_submitted_claims():
    port = MagicMock(spec=GetClaimsForApplicationPort)
    port.get_claims_by_application_id.return_value = [
        _claim(1, ClaimStatus.SUBMITTED),
        _claim(2, ClaimStatus.ACCEPTED),
    ]
    use_case = _build_use_case(port)

    result = use_case.execute("1", assessed=True)

    assert [c.claim_id for c in result] == [2]
    port.get_claims_by_application_id.assert_called_once_with(1)


def test_assessed_false_returns_only_submitted_claims():
    port = MagicMock(spec=GetClaimsForApplicationPort)
    port.get_claims_by_application_id.return_value = [
        _claim(1, ClaimStatus.SUBMITTED),
        _claim(2, ClaimStatus.ACCEPTED),
    ]
    use_case = _build_use_case(port)

    result = use_case.execute("1", assessed=False)

    assert [c.claim_id for c in result] == [1]


def test_returns_empty_list_when_no_claims():
    port = MagicMock(spec=GetClaimsForApplicationPort)
    port.get_claims_by_application_id.return_value = []
    use_case = _build_use_case(port)

    assert use_case.execute("1", assessed=True) == []


def test_raises_application_not_found_when_application_does_not_exist():
    port = MagicMock(spec=GetClaimsForApplicationPort)
    lookup_port = MagicMock(spec=ApplicationLookupPort)
    lookup_port.get_application_by_laa_reference.return_value = None
    use_case = _build_use_case(port, lookup_port)

    with pytest.raises(ApplicationNotFoundError):
        use_case.execute("999999", assessed=True)

    port.get_claims_by_application_id.assert_not_called()


def test_includes_claim_status_and_decision_status():
    port = MagicMock(spec=GetClaimsForApplicationPort)
    port.get_claims_by_application_id.return_value = [
        _claim(1, ClaimStatus.REJECTED),
    ]
    decision_port = MagicMock(spec=GetClaimDecisionPort)
    decision_port.get_claim_decision_by_claim_id.return_value = ClaimDecision(
        claim_decision_id=1,
        claim_id=1,
        decision=ClaimDecisionStatus.REJECT,
    )
    use_case = _build_use_case(port, decision_port=decision_port)

    result = use_case.execute("1", assessed=True)

    assert result[0].status_id == ClaimStatus.REJECTED
    assert result[0].claim_decision_status == ClaimDecisionStatus.REJECT
    decision_port.get_claim_decision_by_claim_id.assert_called_once_with(1)


def test_claim_decision_status_is_none_when_no_decision_exists():
    port = MagicMock(spec=GetClaimsForApplicationPort)
    port.get_claims_by_application_id.return_value = [
        _claim(2, ClaimStatus.ACCEPTED),
    ]
    use_case = _build_use_case(port)

    result = use_case.execute("1", assessed=True)

    assert result[0].status_id == ClaimStatus.ACCEPTED
    assert result[0].claim_decision_status is None
