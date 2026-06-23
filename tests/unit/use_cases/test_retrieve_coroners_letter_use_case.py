from unittest.mock import MagicMock

from app.models.application.index import Application, CoronersLetter
from app.ports.sds_port import SdsPort


def _make_coroners_letter(
    sds_id: str = "letter_abc123.pdf", file_name: str = "test-document.pdf"
) -> CoronersLetter:
    return CoronersLetter(sds_id=sds_id, file_name=file_name)


def _make_application(coroners_letter: CoronersLetter | None = None) -> Application:
    app = MagicMock(spec=Application)
    app.coroners_letter = coroners_letter
    return app


def _make_use_case(session: MagicMock, sds_port: MagicMock):
    from app.use_cases.retrieve_coroners_letter import RetrieveCoronersLetterUseCase

    return RetrieveCoronersLetterUseCase(session=session, sds_port=sds_port)


def test_execute_calls_sds_port_with_sds_id():
    session = MagicMock()
    session.get.return_value = _make_application(
        coroners_letter=_make_coroners_letter(
            sds_id="letter_abc123.pdf", file_name="test-document.pdf"
        )
    )
    sds_port = MagicMock(spec=SdsPort)
    sds_port.retrieve_coroners_letter.return_value = iter([])

    use_case = _make_use_case(session, sds_port)
    use_case.execute("1")

    sds_port.retrieve_coroners_letter.assert_called_once_with("letter_abc123.pdf")


def test_execute_result_contains_file_name():
    session = MagicMock()
    session.get.return_value = _make_application(
        coroners_letter=_make_coroners_letter(
            sds_id="letter_abc123.pdf", file_name="test-document.pdf"
        )
    )
    sds_port = MagicMock(spec=SdsPort)
    sds_port.retrieve_coroners_letter.return_value = iter([])

    use_case = _make_use_case(session, sds_port)
    result = use_case.execute("1")

    assert result.file_name == "test-document.pdf"


def test_execute_returns_iterator_from_port():
    session = MagicMock()
    session.get.return_value = _make_application(
        coroners_letter=_make_coroners_letter("letter_abc.pdf")
    )
    sds_port = MagicMock(spec=SdsPort)
    sds_port.retrieve_coroners_letter.return_value = iter([b"chunk1", b"chunk2"])

    use_case = _make_use_case(session, sds_port)
    result = b"".join(use_case.execute("1").content)

    assert result == b"chunk1chunk2"
