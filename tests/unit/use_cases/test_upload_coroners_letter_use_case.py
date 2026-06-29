import pytest
from unittest.mock import MagicMock

from app.ports.sds_port import SdsPort
from app.use_cases.upload_coroners_letter import UploadCoronersLetterUseCase
from app.models.application.index import SDSUploadCoronersLetterResponse
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

    use_case = UploadCoronersLetterUseCase(sds_port=port, session=MagicMock())
    coroners_letter_id = use_case.execute(
        request_body["coroners_letter"], request_body["file_name"]
    )

    assert coroners_letter_id is not None


def test_execute_stores_coroners_letter_in_database():
    port = MagicMock(spec=SdsPort)
    port.save_coroners_letter.return_value = sds_response_body

    session_mock = MagicMock()
    use_case = UploadCoronersLetterUseCase(sds_port=port, session=session_mock)
    use_case.execute(request_body["coroners_letter"], request_body["file_name"])

    assert session_mock.add.called_with_args(
        session_mock.add.call_args[0][0].file_name == request_body["file_name"],
        session_mock.add.call_args[0][0].sds_file_name
        == sds_response_body.sds_file_name,
    )
    assert session_mock.commit.called


def test_execute_raises_an_error_when_sds_fails():
    port = MagicMock(spec=SdsPort)
    sds_failure_response_body = sds_response_body
    sds_failure_response_body.status = "FAILURE"
    port.save_coroners_letter.return_value = sds_failure_response_body

    use_case = UploadCoronersLetterUseCase(sds_port=port, session=MagicMock())

    with pytest.raises(CoronersLetterUploadError):
        use_case.execute(request_body["coroners_letter"], request_body["file_name"])
