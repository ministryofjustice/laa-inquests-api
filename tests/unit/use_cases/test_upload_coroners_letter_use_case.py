import uuid
from unittest.mock import MagicMock

import pytest

from app.domain.coroners_letter import CoronersLetter
from app.models.application.index import SDSUploadCoronersLetterResponse
from app.ports.sds_port import SdsPort
from app.ports.upload_coroners_letter_port import UploadCoronersLetterPort
from app.use_cases.exceptions import (
    CoronersLetterUploadError,
    CoronersLetterVirusCheckError,
    CoronersLetterVirusDetectedError,
    ProviderOfficeMismatchError,
)
from app.use_cases.upload_coroners_letter import UploadCoronersLetterUseCase

CORONERS_LETTER: bytes = b"test"
FILE_NAME = "test_file.pdf"
OFFICE_ID = "0U651L"
USER_OFFICE_CODES = frozenset({OFFICE_ID})

sds_response_body = SDSUploadCoronersLetterResponse(
    sds_file_name="test_file.pdf", status="SUCCESS"
)


def test_execute_returns_coroners_letter_id_when_call_is_successful():
    port = MagicMock(spec=SdsPort)
    port.virus_check_coroners_letter.return_value = True
    port.save_coroners_letter.return_value = sds_response_body
    upload_port = MagicMock(spec=UploadCoronersLetterPort)
    expected_id = uuid.uuid4()
    upload_port.save_uploaded_coroners_letter.return_value = expected_id

    use_case = UploadCoronersLetterUseCase(
        sds_port=port,
        upload_coroners_letter_port=upload_port,
    )
    coroners_letter_id = use_case.execute(
        coroners_letter=CORONERS_LETTER,
        file_name=FILE_NAME,
        office_id=OFFICE_ID,
        user_office_codes=USER_OFFICE_CODES,
    )

    assert coroners_letter_id == expected_id


def test_execute_stores_coroners_letter_in_database():
    port = MagicMock(spec=SdsPort)
    port.virus_check_coroners_letter.return_value = True
    port.save_coroners_letter.return_value = sds_response_body
    upload_port = MagicMock(spec=UploadCoronersLetterPort)

    use_case = UploadCoronersLetterUseCase(
        sds_port=port,
        upload_coroners_letter_port=upload_port,
    )
    use_case.execute(
        coroners_letter=CORONERS_LETTER,
        file_name=FILE_NAME,
        office_id=OFFICE_ID,
        user_office_codes=USER_OFFICE_CODES,
    )

    upload_port.save_uploaded_coroners_letter.assert_called_once()
    saved_coroners_letter = upload_port.save_uploaded_coroners_letter.call_args[0][0]
    assert isinstance(saved_coroners_letter, CoronersLetter)
    assert saved_coroners_letter.sds_file_name == sds_response_body.sds_file_name
    assert saved_coroners_letter.file_name == FILE_NAME


def test_execute_stores_coroners_letter_with_submitted_office_id():
    port = MagicMock(spec=SdsPort)
    port.virus_check_coroners_letter.return_value = True
    port.save_coroners_letter.return_value = sds_response_body
    upload_port = MagicMock(spec=UploadCoronersLetterPort)

    use_case = UploadCoronersLetterUseCase(
        sds_port=port,
        upload_coroners_letter_port=upload_port,
    )
    use_case.execute(
        coroners_letter=CORONERS_LETTER,
        file_name=FILE_NAME,
        office_id=OFFICE_ID,
        user_office_codes=USER_OFFICE_CODES,
    )

    upload_port.save_uploaded_coroners_letter.assert_called_once()
    assert upload_port.save_uploaded_coroners_letter.call_args.args == (
        CoronersLetter(
            sds_file_name=sds_response_body.sds_file_name,
            file_name=FILE_NAME,
            office_id=OFFICE_ID,
        ),
    )


def test_execute_raises_an_error_when_sds_fails():
    port = MagicMock(spec=SdsPort)
    port.virus_check_coroners_letter.return_value = True
    sds_failure_response_body = SDSUploadCoronersLetterResponse(
        sds_file_name="test_file.pdf", status="FAILURE"
    )
    port.save_coroners_letter.return_value = sds_failure_response_body

    use_case = UploadCoronersLetterUseCase(
        sds_port=port,
        upload_coroners_letter_port=MagicMock(spec=UploadCoronersLetterPort),
    )

    with pytest.raises(CoronersLetterUploadError):
        use_case.execute(
            coroners_letter=CORONERS_LETTER,
            file_name=FILE_NAME,
            office_id=OFFICE_ID,
            user_office_codes=USER_OFFICE_CODES,
        )


def test_execute_raises_an_error_when_virus_check_fails():
    port = MagicMock(spec=SdsPort)
    port.virus_check_coroners_letter.return_value = False
    port.save_coroners_letter.return_value = sds_response_body
    upload_port = MagicMock(spec=UploadCoronersLetterPort)

    use_case = UploadCoronersLetterUseCase(
        sds_port=port,
        upload_coroners_letter_port=upload_port,
    )

    with pytest.raises(CoronersLetterVirusDetectedError):
        use_case.execute(
            coroners_letter=CORONERS_LETTER,
            file_name=FILE_NAME,
            office_id=OFFICE_ID,
            user_office_codes=USER_OFFICE_CODES,
        )

    port.save_coroners_letter.assert_not_called()
    upload_port.save_uploaded_coroners_letter.assert_not_called()


def test_execute_raises_an_error_when_virus_check_returns_server_error():
    port = MagicMock(spec=SdsPort)
    port.virus_check_coroners_letter.side_effect = CoronersLetterUploadError(
        "SDS server error"
    )
    upload_port = MagicMock(spec=UploadCoronersLetterPort)

    use_case = UploadCoronersLetterUseCase(
        sds_port=port,
        upload_coroners_letter_port=upload_port,
    )

    with pytest.raises(CoronersLetterVirusCheckError):
        use_case.execute(
            coroners_letter=CORONERS_LETTER,
            file_name=FILE_NAME,
            office_id=OFFICE_ID,
            user_office_codes=USER_OFFICE_CODES,
        )

    port.save_coroners_letter.assert_not_called()
    upload_port.save_uploaded_coroners_letter.assert_not_called()


def test_execute_raises_an_error_when_office_id_is_not_in_user_office_codes():
    port = MagicMock(spec=SdsPort)
    upload_port = MagicMock(spec=UploadCoronersLetterPort)

    use_case = UploadCoronersLetterUseCase(
        sds_port=port,
        upload_coroners_letter_port=upload_port,
    )

    with pytest.raises(ProviderOfficeMismatchError):
        use_case.execute(
            coroners_letter=CORONERS_LETTER,
            file_name=FILE_NAME,
            office_id="1A234B",
            user_office_codes=USER_OFFICE_CODES,
        )

    port.virus_check_coroners_letter.assert_not_called()
    port.save_coroners_letter.assert_not_called()
    upload_port.save_uploaded_coroners_letter.assert_not_called()
