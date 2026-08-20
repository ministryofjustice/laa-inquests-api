import uuid
from unittest.mock import MagicMock

import pytest

from app.domain.claim_evidence import ClaimEvidence
from app.ports.claim.get_claim_evidence_port import GetClaimEvidencePort
from app.ports.sds_port import SdsPort
from app.use_cases.exceptions import (
    ClaimEvidenceNotFoundError,
    ClaimEvidenceRetrievalError,
    InvalidClaimEvidenceDocumentIdError,
    SDSClaimEvidenceRetrievalError,
)


def _make_claim_evidence(
    sds_file_name: str = "claim-evidence_abc123.pdf",
    file_name: str = "test-document.pdf",
) -> ClaimEvidence:
    return ClaimEvidence(sds_file_name=sds_file_name, file_name=file_name)


def _make_use_case(get_claim_evidence_port: MagicMock, sds_port: MagicMock):
    from app.use_cases.retrieve_claim_evidence import RetrieveClaimEvidenceUseCase

    return RetrieveClaimEvidenceUseCase(
        get_claim_evidence_port=get_claim_evidence_port,
        sds_port=sds_port,
    )


def test_execute_calls_sds_port_with_sds_file_name():
    get_claim_evidence_port = MagicMock(spec=GetClaimEvidencePort)
    get_claim_evidence_port.get_claim_evidence_by_id.return_value = (
        _make_claim_evidence(
            sds_file_name="claim-evidence_abc123.pdf", file_name="test-document.pdf"
        )
    )
    sds_port = MagicMock(spec=SdsPort)
    sds_port.retrieve_claim_evidence.return_value = iter([])

    use_case = _make_use_case(get_claim_evidence_port, sds_port)
    use_case.execute(uuid.uuid4())

    sds_port.retrieve_claim_evidence.assert_called_once_with(
        "claim-evidence_abc123.pdf"
    )


def test_execute_result_contains_file_name():
    get_claim_evidence_port = MagicMock(spec=GetClaimEvidencePort)
    get_claim_evidence_port.get_claim_evidence_by_id.return_value = (
        _make_claim_evidence(
            sds_file_name="claim-evidence_abc123.pdf", file_name="test-document.pdf"
        )
    )
    sds_port = MagicMock(spec=SdsPort)
    sds_port.retrieve_claim_evidence.return_value = iter([])

    use_case = _make_use_case(get_claim_evidence_port, sds_port)
    result = use_case.execute(uuid.uuid4())

    assert result.file_name == "test-document.pdf"


def test_execute_returns_iterator_from_port():
    get_claim_evidence_port = MagicMock(spec=GetClaimEvidencePort)
    get_claim_evidence_port.get_claim_evidence_by_id.return_value = (
        _make_claim_evidence(sds_file_name="claim-evidence_abc.pdf")
    )
    sds_port = MagicMock(spec=SdsPort)

    expected_content = iter([b"chunk1", b"chunk2"])
    sds_port.retrieve_claim_evidence.return_value = expected_content

    use_case = _make_use_case(get_claim_evidence_port, sds_port)
    response = use_case.execute(uuid.uuid4()).content

    assert response == expected_content


def test_execute_raises_error_when_claim_evidence_is_none():
    get_claim_evidence_port = MagicMock(spec=GetClaimEvidencePort)
    get_claim_evidence_port.get_claim_evidence_by_id.return_value = None
    sds_port = MagicMock(spec=SdsPort)
    use_case = _make_use_case(get_claim_evidence_port, sds_port)

    with pytest.raises(ClaimEvidenceNotFoundError):
        use_case.execute(uuid.uuid4())

    sds_port.retrieve_claim_evidence.assert_not_called()


def test_execute_raises_error_when_port_raises_invalid_id():
    get_claim_evidence_port = MagicMock(spec=GetClaimEvidencePort)
    get_claim_evidence_port.get_claim_evidence_by_id.return_value = (
        _make_claim_evidence(sds_file_name="claim-evidence_abc123.pdf")
    )
    sds_port = MagicMock(spec=SdsPort)
    sds_port.retrieve_claim_evidence.side_effect = InvalidClaimEvidenceDocumentIdError()
    use_case = _make_use_case(get_claim_evidence_port, sds_port)

    with pytest.raises(ClaimEvidenceRetrievalError):
        use_case.execute(uuid.uuid4())


def test_execute_raises_error_when_port_raises_retrieval_error():
    get_claim_evidence_port = MagicMock(spec=GetClaimEvidencePort)
    get_claim_evidence_port.get_claim_evidence_by_id.return_value = (
        _make_claim_evidence(sds_file_name="claim-evidence_abc123.pdf")
    )
    sds_port = MagicMock(spec=SdsPort)
    sds_port.retrieve_claim_evidence.side_effect = SDSClaimEvidenceRetrievalError()
    use_case = _make_use_case(get_claim_evidence_port, sds_port)

    with pytest.raises(ClaimEvidenceRetrievalError):
        use_case.execute(uuid.uuid4())
