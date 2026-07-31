import uuid
from unittest.mock import MagicMock

import pytest

from app.domain.claim_evidence import ClaimEvidence
from app.ports.claim.delete_claim_evidence_port import DeleteClaimEvidencePort
from app.ports.claim.get_claim_evidence_port import GetClaimEvidencePort
from app.ports.sds_port import SdsPort
from app.use_cases.delete_claim_evidence import DeleteClaimEvidenceUseCase
from app.use_cases.exceptions import (
    ClaimEvidenceDeleteError,
    ClaimEvidenceNotFoundError,
)


def _make_claim_evidence(
    sds_file_name: str = "claim-evidence_abc123.pdf",
    file_name: str = "test-document.pdf",
) -> ClaimEvidence:
    return ClaimEvidence(sds_file_name=sds_file_name, file_name=file_name)


def test_execute_deletes_file_from_sds_and_db():
    get_claim_evidence_port = MagicMock(spec=GetClaimEvidencePort)
    get_claim_evidence_port.get_claim_evidence_by_id.return_value = _make_claim_evidence()

    delete_claim_evidence_port = MagicMock(spec=DeleteClaimEvidencePort)
    delete_claim_evidence_port.delete_claim_evidence_by_id.return_value = True

    sds_port = MagicMock(spec=SdsPort)

    use_case = DeleteClaimEvidenceUseCase(
        get_claim_evidence_port=get_claim_evidence_port,
        delete_claim_evidence_port=delete_claim_evidence_port,
        sds_port=sds_port,
    )

    claim_evidence_id = uuid.uuid4()
    use_case.execute(claim_evidence_id)

    sds_port.delete_claim_evidence.assert_called_once_with("claim-evidence_abc123.pdf")
    delete_claim_evidence_port.delete_claim_evidence_by_id.assert_called_once_with(
        claim_evidence_id
    )


def test_execute_raises_not_found_when_claim_evidence_missing():
    get_claim_evidence_port = MagicMock(spec=GetClaimEvidencePort)
    get_claim_evidence_port.get_claim_evidence_by_id.return_value = None

    delete_claim_evidence_port = MagicMock(spec=DeleteClaimEvidencePort)
    sds_port = MagicMock(spec=SdsPort)

    use_case = DeleteClaimEvidenceUseCase(
        get_claim_evidence_port=get_claim_evidence_port,
        delete_claim_evidence_port=delete_claim_evidence_port,
        sds_port=sds_port,
    )

    with pytest.raises(ClaimEvidenceNotFoundError):
        use_case.execute(uuid.uuid4())

    sds_port.delete_claim_evidence.assert_not_called()
    delete_claim_evidence_port.delete_claim_evidence_by_id.assert_not_called()


def test_execute_raises_delete_error_when_sds_delete_fails():
    get_claim_evidence_port = MagicMock(spec=GetClaimEvidencePort)
    get_claim_evidence_port.get_claim_evidence_by_id.return_value = _make_claim_evidence()

    delete_claim_evidence_port = MagicMock(spec=DeleteClaimEvidencePort)
    sds_port = MagicMock(spec=SdsPort)
    sds_port.delete_claim_evidence.side_effect = Exception("SDS failed")

    use_case = DeleteClaimEvidenceUseCase(
        get_claim_evidence_port=get_claim_evidence_port,
        delete_claim_evidence_port=delete_claim_evidence_port,
        sds_port=sds_port,
    )

    with pytest.raises(ClaimEvidenceDeleteError):
        use_case.execute(uuid.uuid4())


def test_execute_raises_not_found_when_db_delete_returns_false():
    get_claim_evidence_port = MagicMock(spec=GetClaimEvidencePort)
    get_claim_evidence_port.get_claim_evidence_by_id.return_value = _make_claim_evidence()

    delete_claim_evidence_port = MagicMock(spec=DeleteClaimEvidencePort)
    delete_claim_evidence_port.delete_claim_evidence_by_id.return_value = False

    sds_port = MagicMock(spec=SdsPort)

    use_case = DeleteClaimEvidenceUseCase(
        get_claim_evidence_port=get_claim_evidence_port,
        delete_claim_evidence_port=delete_claim_evidence_port,
        sds_port=sds_port,
    )

    with pytest.raises(ClaimEvidenceNotFoundError):
        use_case.execute(uuid.uuid4())
