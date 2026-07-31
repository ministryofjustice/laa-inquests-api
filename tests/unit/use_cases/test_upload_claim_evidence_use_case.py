import uuid
from unittest.mock import MagicMock

import pytest

from app.domain.claim_evidence import ClaimEvidence
from app.models.application.index import SDSUploadClaimEvidenceResponse
from app.ports.claim.upload_claim_evidence_port import UploadClaimEvidencePort
from app.ports.sds_port import SdsPort
from app.use_cases.exceptions import (
    ClaimEvidenceUploadError,
    ClaimEvidenceVirusCheckError,
    ClaimEvidenceVirusDetectedError,
)
from app.use_cases.upload_claim_evidence import UploadClaimEvidenceUseCase

request_body = {
    "claim_evidence": b"test",
    "file_name": "test_file.pdf",
}
sds_response_body = SDSUploadClaimEvidenceResponse(
    sds_file_name="test_file.pdf", status="SUCCESS"
)


def test_execute_returns_claim_evidence_id_when_call_is_successful():
    sds_port = MagicMock(spec=SdsPort)
    sds_port.virus_check_claim_evidence.return_value = True
    sds_port.save_claim_evidence.return_value = sds_response_body

    upload_port = MagicMock(spec=UploadClaimEvidencePort)
    expected_id = uuid.uuid4()
    upload_port.save_uploaded_claim_evidence.return_value = expected_id

    use_case = UploadClaimEvidenceUseCase(
        sds_port=sds_port,
        upload_claim_evidence_port=upload_port,
    )

    claim_evidence_id = use_case.execute(
        request_body["claim_evidence"], request_body["file_name"]
    )

    assert claim_evidence_id == expected_id


def test_execute_stores_claim_evidence_in_database():
    sds_port = MagicMock(spec=SdsPort)
    sds_port.virus_check_claim_evidence.return_value = True
    sds_port.save_claim_evidence.return_value = sds_response_body

    upload_port = MagicMock(spec=UploadClaimEvidencePort)

    use_case = UploadClaimEvidenceUseCase(
        sds_port=sds_port,
        upload_claim_evidence_port=upload_port,
    )

    use_case.execute(request_body["claim_evidence"], request_body["file_name"])

    upload_port.save_uploaded_claim_evidence.assert_called_once()
    saved_claim_evidence = upload_port.save_uploaded_claim_evidence.call_args[0][0]
    assert isinstance(saved_claim_evidence, ClaimEvidence)
    assert saved_claim_evidence.sds_file_name == sds_response_body.sds_file_name
    assert saved_claim_evidence.file_name == request_body["file_name"]


def test_execute_raises_an_error_when_virus_check_fails():
    sds_port = MagicMock(spec=SdsPort)
    sds_port.virus_check_claim_evidence.return_value = False
    sds_port.save_claim_evidence.return_value = sds_response_body
    upload_port = MagicMock(spec=UploadClaimEvidencePort)

    use_case = UploadClaimEvidenceUseCase(
        sds_port=sds_port,
        upload_claim_evidence_port=upload_port,
    )

    with pytest.raises(ClaimEvidenceVirusDetectedError):
        use_case.execute(request_body["claim_evidence"], request_body["file_name"])

    sds_port.save_claim_evidence.assert_not_called()
    upload_port.save_uploaded_claim_evidence.assert_not_called()


def test_execute_raises_an_error_when_sds_save_fails():
    sds_port = MagicMock(spec=SdsPort)
    sds_port.virus_check_claim_evidence.return_value = True
    sds_failure_response = SDSUploadClaimEvidenceResponse(
        sds_file_name="test_file.pdf", status="FAILURE"
    )
    sds_port.save_claim_evidence.return_value = sds_failure_response
    upload_port = MagicMock(spec=UploadClaimEvidencePort)

    use_case = UploadClaimEvidenceUseCase(
        sds_port=sds_port,
        upload_claim_evidence_port=upload_port,
    )

    with pytest.raises(ClaimEvidenceUploadError):
        use_case.execute(request_body["claim_evidence"], request_body["file_name"])

    upload_port.save_uploaded_claim_evidence.assert_not_called()


def test_execute_raises_an_error_when_virus_check_returns_server_error():
    sds_port = MagicMock(spec=SdsPort)
    sds_port.virus_check_claim_evidence.side_effect = ClaimEvidenceUploadError(
        "SDS server error"
    )
    upload_port = MagicMock(spec=UploadClaimEvidencePort)

    use_case = UploadClaimEvidenceUseCase(
        sds_port=sds_port,
        upload_claim_evidence_port=upload_port,
    )

    with pytest.raises(ClaimEvidenceVirusCheckError):
        use_case.execute(request_body["claim_evidence"], request_body["file_name"])

    sds_port.save_claim_evidence.assert_not_called()
    upload_port.save_uploaded_claim_evidence.assert_not_called()
