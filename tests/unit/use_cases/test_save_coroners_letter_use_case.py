import pytest
from unittest.mock import MagicMock

from app.ports.sds_port import SdsPort
from app.use_cases.save_coroners_letter import SaveCoronersLetterUseCase
from app.models.application.index import SDSUploadCoronersLetterResponse
from app.use_cases.exceptions import CoronersLetterSaveError

request_body = {
    "coroners_letter": b"test",
    "file_name": "test_file.pdf",
}
body = SDSUploadCoronersLetterResponse(sds_file_name="test_file.pdf", status="SUCCESS")


def test_execute_returns_response_body_when_call_is_successful():
    port = MagicMock(spec=SdsPort)
    port.save_coroners_letter.return_value = body

    use_case = SaveCoronersLetterUseCase(sds_port=port)
    result = use_case.execute(
        request_body["coroners_letter"], request_body["file_name"]
    )

    assert result.sds_file_name == "test_file.pdf"


def test_execute_raises_an_error_when_sds_fails():
    port = MagicMock(spec=SdsPort)
    body.status = "FAILURE"
    port.save_coroners_letter.return_value = body

    use_case = SaveCoronersLetterUseCase(sds_port=port)

    with pytest.raises(CoronersLetterSaveError):
        use_case.execute(request_body["coroners_letter"], request_body["file_name"])
