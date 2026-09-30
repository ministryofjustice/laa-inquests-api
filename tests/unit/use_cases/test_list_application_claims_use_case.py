from unittest.mock import MagicMock

import pytest

from app.models.application.index import Application
from app.models.claim.enums import ClaimDecisionStatus, ClaimStatus
from app.models.claim.index import Claim
from app.ports.application_lookup_port import ApplicationLookupPort
from app.ports.claim.get_claim_decision_port import GetClaimDecisionPort
from app.ports.claim.get_claims_for_application_port import (
    GetClaimsForApplicationPort,
)
from app.use_cases.exceptions import ApplicationNotFoundError
from app.use_cases.list_application_claims import ListApplicationClaimsUseCase
from tests.factories.builders import (
    build_application,
    build_claim_decision,
    build_poa_claim,
)


def _claim(application: Application, status: ClaimStatus) -> Claim:
    return build_poa_claim(
        application_id=application.application_id,
        status_id=status,
    )


def _build_use_case(
    claims_port, lookup_port=None, decision_port=None, application=None
):
    if lookup_port is None:
        lookup_port = MagicMock(spec=ApplicationLookupPort)
        lookup_port.get_application_by_laa_reference.return_value = (
            build_application() if application is None else application
        )
    if decision_port is None:
        decision_port = MagicMock(spec=GetClaimDecisionPort)
        decision_port.get_claim_decision_by_claim_id.return_value = None
    return ListApplicationClaimsUseCase(
        get_claims_for_application_port=claims_port,
        get_claim_decision_port=decision_port,
        application_lookup_port=lookup_port,
    )


def test_assessed_true_returns_only_non_submitted_claims():
    application = build_application()
    accepted = _claim(application, ClaimStatus.ACCEPTED)
    port = MagicMock(spec=GetClaimsForApplicationPort)
    port.get_claims_by_application_id.return_value = [
        _claim(application, ClaimStatus.SUBMITTED),
        accepted,
    ]
    use_case = _build_use_case(port, application=application)

    result = use_case.execute("1", assessed=True)

    assert [c.claim_reference for c in result] == [accepted.claim_reference]
    port.get_claims_by_application_id.assert_called_once_with(
        application.application_id
    )


def test_assessed_false_returns_only_submitted_claims():
    application = build_application()
    submitted = _claim(application, ClaimStatus.SUBMITTED)
    port = MagicMock(spec=GetClaimsForApplicationPort)
    port.get_claims_by_application_id.return_value = [
        submitted,
        _claim(application, ClaimStatus.ACCEPTED),
    ]
    use_case = _build_use_case(port, application=application)

    result = use_case.execute("1", assessed=False)

    assert [c.claim_reference for c in result] == [submitted.claim_reference]


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
    application = build_application()
    claim = _claim(application, ClaimStatus.REJECTED)
    port = MagicMock(spec=GetClaimsForApplicationPort)
    port.get_claims_by_application_id.return_value = [claim]
    decision_port = MagicMock(spec=GetClaimDecisionPort)
    decision_port.get_claim_decision_by_claim_id.return_value = build_claim_decision(
        claim_decision_id=1,
        claim_id=claim.claim_id,
        decision=ClaimDecisionStatus.REJECT,
    )
    use_case = _build_use_case(
        port, decision_port=decision_port, application=application
    )

    result = use_case.execute("1", assessed=True)

    assert result[0].status_id == ClaimStatus.REJECTED
    assert result[0].claim_decision_status == ClaimDecisionStatus.REJECT
    decision_port.get_claim_decision_by_claim_id.assert_called_once_with(claim.claim_id)


def test_claim_decision_status_is_none_when_no_decision_exists():
    application = build_application()
    port = MagicMock(spec=GetClaimsForApplicationPort)
    port.get_claims_by_application_id.return_value = [
        _claim(application, ClaimStatus.ACCEPTED),
    ]
    use_case = _build_use_case(port, application=application)

    result = use_case.execute("1", assessed=True)

    assert result[0].status_id == ClaimStatus.ACCEPTED
    assert result[0].claim_decision_status is None
