import pytest
from unittest.mock import MagicMock
import uuid

from app.domain.coroners_letter import CoronersLetter
from app.models.application.index import SDSUploadCoronersLetterResponse
from app.ports.sds_port import SdsPort
from app.ports.upload_coroners_letter_port import UploadCoronersLetterPort
from app.use_cases.upload_coroners_letter import UploadCoronersLetterUseCase
from app.use_cases.exceptions import CoronersLetterUploadError

request_body = {
    "coroners_letter": b"test",
    "file_name": "test_file.pdf",
}
sds_response_body = SDSUploadCoronersLetterResponse(
    sds_file_name="test_file.pdf", status="SUCCESS"
)


def test_execute_returns_coroners_letter_id_when_call_is_successful():
    port = MagicMock(spec=SdsPort)
    port.save_coroners_letter.return_value = sds_response_body
    upload_port = MagicMock(spec=UploadCoronersLetterPort)
    expected_id = uuid.uuid4()
    upload_port.save_uploaded_coroners_letter.return_value = expected_id

    use_case = UploadCoronersLetterUseCase(
        sds_port=port,
        upload_coroners_letter_port=upload_port,
    )
    coroners_letter_id = use_case.execute(
        request_body["coroners_letter"], request_body["file_name"]
    )

    assert coroners_letter_id == expected_id


def test_execute_stores_coroners_letter_in_database():
    port = MagicMock(spec=SdsPort)
    port.save_coroners_letter.return_value = sds_response_body
    upload_port = MagicMock(spec=UploadCoronersLetterPort)

    use_case = UploadCoronersLetterUseCase(
        sds_port=port,
        upload_coroners_letter_port=upload_port,
    )
    use_case.execute(request_body["coroners_letter"], request_body["file_name"])

    upload_port.save_uploaded_coroners_letter.assert_called_once()
    saved_coroners_letter = upload_port.save_uploaded_coroners_letter.call_args[0][0]
    assert isinstance(saved_coroners_letter, CoronersLetter)
    assert saved_coroners_letter.sds_file_name == sds_response_body.sds_file_name
    assert saved_coroners_letter.file_name == request_body["file_name"]


def test_execute_raises_an_error_when_sds_fails():
    port = MagicMock(spec=SdsPort)
    sds_failure_response_body = sds_response_body
    sds_failure_response_body.status = "FAILURE"
    port.save_coroners_letter.return_value = sds_failure_response_body

    use_case = UploadCoronersLetterUseCase(
        sds_port=port,
        upload_coroners_letter_port=MagicMock(spec=UploadCoronersLetterPort),
    )

    with pytest.raises(CoronersLetterUploadError):
        use_case.execute(request_body["coroners_letter"], request_body["file_name"])
