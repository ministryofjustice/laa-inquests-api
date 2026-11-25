from unittest.mock import MagicMock

import pytest

from app.domain.caller import CaseworkerCaller, ProviderCaller
from app.ports.claim.get_claim_by_id_port import GetClaimByIdPort
from app.use_cases.exceptions import ClaimNotFoundError
from app.use_cases.retrieve_application_for_claim import (
    RetrieveApplicationForClaimUseCase,
)

PROVIDER = ProviderCaller(office_codes=frozenset({"0U651L"}))


def _claim(office_id: str = "0U651L"):
    claim = MagicMock()
    claim.application.laa_reference = "INQ-123-456"
    claim.application.provider.office_id = office_id
    return claim


def _build_use_case(claim):
    claim_port = MagicMock(spec=GetClaimByIdPort)
    claim_port.get_claim_by_reference.return_value = claim

    return (
        RetrieveApplicationForClaimUseCase(claim_port),
        claim_port,
    )


def test_returns_application_reference_for_existing_claim():
    use_case, claim_port = _build_use_case(_claim())

    result = use_case.execute("INQC-0000-0001", PROVIDER)

    assert result == "INQ-123-456"
    claim_port.get_claim_by_reference.assert_called_once_with("INQC-0000-0001")


def test_raises_claim_not_found_when_claim_does_not_exist():
    use_case, _ = _build_use_case(None)

    with pytest.raises(ClaimNotFoundError):
        use_case.execute("INQC-ZZZZ-ZZZZ", PROVIDER)


def test_raises_claim_not_found_when_application_belongs_to_another_office():
    use_case, _ = _build_use_case(_claim(office_id="not-providers-office"))

    with pytest.raises(ClaimNotFoundError):
        use_case.execute("INQC-0000-0001", PROVIDER)


def test_caseworker_gets_application_reference_for_any_office():
    use_case, _ = _build_use_case(_claim(office_id="any-office"))

    result = use_case.execute("INQC-0000-0001", CaseworkerCaller())

    assert result == "INQ-123-456"
