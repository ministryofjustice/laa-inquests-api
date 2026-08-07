from unittest.mock import MagicMock

import pytest

from app.models.claim.enums import ClaimStatus, ClaimType
from app.models.claim.index import Claim
from app.ports.application_lookup_port import ApplicationLookupPort
from app.ports.claim.get_claims_for_application_port import (
    GetClaimsForApplicationPort,
)
from app.use_cases.exceptions import ApplicationNotFoundError
from app.use_cases.list_application_claims import ListApplicationClaimsUseCase


def _claim(claim_id: int, status: ClaimStatus) -> Claim:
    return Claim(
        claim_id=claim_id,
        laa_reference=1,
        claim_type_id=ClaimType.PAYMENT_ON_ACCOUNT,
        status_id=status,
    )


def _build_use_case(claims_port, lookup_port=None):
    if lookup_port is None:
        lookup_port = MagicMock(spec=ApplicationLookupPort)
        lookup_port.get_application_by_laa_reference.return_value = MagicMock()
    return ListApplicationClaimsUseCase(
        get_claims_for_application_port=claims_port,
        application_lookup_port=lookup_port,
    )


def test_assessed_true_returns_only_non_submitted_claims():
    port = MagicMock(spec=GetClaimsForApplicationPort)
    port.get_claims_by_laa_reference.return_value = [
        _claim(1, ClaimStatus.SUBMITTED),
        _claim(2, ClaimStatus.ACCEPTED),
    ]
    use_case = _build_use_case(port)

    result = use_case.execute("1", assessed=True)

    assert [c.claim_id for c in result] == [2]
    port.get_claims_by_laa_reference.assert_called_once_with("1")


def test_assessed_false_returns_only_submitted_claims():
    port = MagicMock(spec=GetClaimsForApplicationPort)
    port.get_claims_by_laa_reference.return_value = [
        _claim(1, ClaimStatus.SUBMITTED),
        _claim(2, ClaimStatus.ACCEPTED),
    ]
    use_case = _build_use_case(port)

    result = use_case.execute("1", assessed=False)

    assert [c.claim_id for c in result] == [1]


def test_returns_empty_list_when_no_claims():
    port = MagicMock(spec=GetClaimsForApplicationPort)
    port.get_claims_by_laa_reference.return_value = []
    use_case = _build_use_case(port)

    assert use_case.execute("1", assessed=True) == []


def test_raises_application_not_found_when_application_does_not_exist():
    port = MagicMock(spec=GetClaimsForApplicationPort)
    lookup_port = MagicMock(spec=ApplicationLookupPort)
    lookup_port.get_application_by_laa_reference.return_value = None
    use_case = _build_use_case(port, lookup_port)

    with pytest.raises(ApplicationNotFoundError):
        use_case.execute("999999", assessed=True)

    port.get_claims_by_laa_reference.assert_not_called()
