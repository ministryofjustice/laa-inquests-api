from unittest.mock import MagicMock

import pytest

from app.ports.claim.get_claim_by_id_port import GetClaimByIdPort
from app.use_cases.exceptions import ClaimNotFoundError
from app.use_cases.retrieve_application_for_claim import (
    RetrieveApplicationForClaimUseCase,
)


def _build_use_case(claim):
    claim_port = MagicMock(spec=GetClaimByIdPort)
    claim_port.get_claim_by_reference.return_value = claim

    return (
        RetrieveApplicationForClaimUseCase(claim_port),
        claim_port,
    )


def test_returns_application_reference_for_existing_claim():
    claim = MagicMock()
    claim.application.laa_reference = "INQ-123-456"
    use_case, claim_port = _build_use_case(claim)

    result = use_case.execute("INQC-0000-0001")

    assert result == "INQ-123-456"
    claim_port.get_claim_by_reference.assert_called_once_with("INQC-0000-0001")


def test_raises_claim_not_found_when_claim_does_not_exist():
    use_case, _ = _build_use_case(None)

    with pytest.raises(ClaimNotFoundError):
        use_case.execute("INQC-ZZZZ-ZZZZ")
