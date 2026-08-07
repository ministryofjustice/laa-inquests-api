from unittest.mock import MagicMock

from app.models.claim.enums import ClaimStatus, ClaimType
from app.models.claim.index import Claim
from app.ports.claim.get_claims_for_application_port import (
    GetClaimsForApplicationPort,
)
from app.use_cases.list_application_claims import ListApplicationClaimsUseCase


def _claim(claim_id: int, status: ClaimStatus) -> Claim:
    return Claim(
        claim_id=claim_id,
        laa_reference=1,
        claim_type_id=ClaimType.PAYMENT_ON_ACCOUNT,
        status_id=status,
    )


def test_assessed_true_returns_only_non_submitted_claims():
    port = MagicMock(spec=GetClaimsForApplicationPort)
    port.get_claims_by_laa_reference.return_value = [
        _claim(1, ClaimStatus.SUBMITTED),
        _claim(2, ClaimStatus.ACCEPTED),
    ]
    use_case = ListApplicationClaimsUseCase(get_claims_for_application_port=port)

    result = use_case.execute("1", assessed=True)

    assert [c.claim_id for c in result] == [2]
    port.get_claims_by_laa_reference.assert_called_once_with("1")


def test_assessed_false_returns_only_submitted_claims():
    port = MagicMock(spec=GetClaimsForApplicationPort)
    port.get_claims_by_laa_reference.return_value = [
        _claim(1, ClaimStatus.SUBMITTED),
        _claim(2, ClaimStatus.ACCEPTED),
    ]
    use_case = ListApplicationClaimsUseCase(get_claims_for_application_port=port)

    result = use_case.execute("1", assessed=False)

    assert [c.claim_id for c in result] == [1]


def test_returns_empty_list_when_no_claims():
    port = MagicMock(spec=GetClaimsForApplicationPort)
    port.get_claims_by_laa_reference.return_value = []
    use_case = ListApplicationClaimsUseCase(get_claims_for_application_port=port)

    assert use_case.execute("1", assessed=True) == []
