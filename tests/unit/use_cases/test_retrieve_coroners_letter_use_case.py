import uuid
from unittest.mock import MagicMock

import pytest

from app.models.application.index import Application, CoronersLetter
from app.ports.application_lookup_port import ApplicationLookupPort
from app.ports.sds_port import SdsPort
from app.use_cases.exceptions import (
    CoronersLetterNotFoundError,
    CoronersLetterRetrievalError,
    InvalidCoronersLetterDocumentIdError,
    SDSLetterRetrievalError,
)


def _make_coroners_letter(
    coroners_letter_id: uuid.UUID | None = None,
    sds_file_name: str = "letter_abc123.pdf",
    file_name: str = "test-document.pdf",
) -> CoronersLetter:
    return CoronersLetter(
        coroners_letter_id=coroners_letter_id or uuid.uuid4(),
        sds_file_name=sds_file_name,
        file_name=file_name,
    )


def _make_application(coroners_letter: CoronersLetter | None = None) -> Application:
    app = MagicMock(spec=Application)
    app.coroners_letter = coroners_letter
    return app


def _make_use_case(application: Application | None, sds_port: MagicMock):
    from app.use_cases.retrieve_coroners_letter import RetrieveCoronersLetterUseCase

    application_lookup_port = MagicMock(spec=ApplicationLookupPort)
    application_lookup_port.get_application_by_laa_reference.return_value = application
    return RetrieveCoronersLetterUseCase(
        application_lookup_port=application_lookup_port, sds_port=sds_port
    )


def test_execute_calls_sds_port_with_sds_file_name():
    application = _make_application(
        coroners_letter=_make_coroners_letter(
            coroners_letter_id=uuid.uuid4(),
            sds_file_name="letter_abc123.pdf",
            file_name="test-document.pdf",
        )
    )
    sds_port = MagicMock(spec=SdsPort)
    sds_port.retrieve_coroners_letter.return_value = iter([])

    use_case = _make_use_case(application, sds_port)
    use_case.execute("1")

    sds_port.retrieve_coroners_letter.assert_called_once_with("letter_abc123.pdf")


def test_execute_result_contains_file_name():
    application = _make_application(
        coroners_letter=_make_coroners_letter(
            sds_file_name="letter_abc123.pdf", file_name="test-document.pdf"
        )
    )
    sds_port = MagicMock(spec=SdsPort)
    sds_port.retrieve_coroners_letter.return_value = iter([])

    use_case = _make_use_case(application, sds_port)
    result = use_case.execute("1")

    assert result.file_name == "test-document.pdf"


def test_execute_returns_iterator_from_port():
    application = _make_application(
        coroners_letter=_make_coroners_letter(sds_file_name="letter_abc.pdf")
    )
    sds_port = MagicMock(spec=SdsPort)

    expected_content = iter([b"chunk1", b"chunk2"])
    sds_port.retrieve_coroners_letter.return_value = expected_content

    use_case = _make_use_case(application, sds_port)
    response = use_case.execute("1").content

    assert response == expected_content


def test_execute_raises_error_when_application_is_none():
    application = None
    sds_port = MagicMock(spec=SdsPort)
    use_case = _make_use_case(application, sds_port)

    with pytest.raises(CoronersLetterNotFoundError):
        use_case.execute("1")

    sds_port.retrieve_coroners_letter.assert_not_called()


def test_execute_raises_error_when_application_coroners_letter_is_none():
    application = _make_application(coroners_letter=None)
    sds_port = MagicMock(spec=SdsPort)
    use_case = _make_use_case(application, sds_port)

    with pytest.raises(CoronersLetterNotFoundError):
        use_case.execute("1")

    sds_port.retrieve_coroners_letter.assert_not_called()


def test_execute_raises_error_when_port_raises_invalid_id():
    application = _make_application(
        coroners_letter=_make_coroners_letter(sds_file_name="letter_abc123.pdf")
    )
    sds_port = MagicMock(spec=SdsPort)
    sds_port.retrieve_coroners_letter.side_effect = (
        InvalidCoronersLetterDocumentIdError()
    )
    use_case = _make_use_case(application, sds_port)

    with pytest.raises(CoronersLetterRetrievalError):
        use_case.execute("1")


def test_execute_raises_error_when_port_raises_retrieval_error():
    application = _make_application(
        coroners_letter=_make_coroners_letter(sds_file_name="letter_abc123.pdf")
    )
    sds_port = MagicMock(spec=SdsPort)
    sds_port.retrieve_coroners_letter.side_effect = SDSLetterRetrievalError()
    use_case = _make_use_case(application, sds_port)

    with pytest.raises(CoronersLetterRetrievalError):
        use_case.execute("1")
