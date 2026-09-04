import uuid
from unittest.mock import MagicMock

import pytest

from app.domain.coroners_letter import CoronersLetter
from app.ports.delete_coroners_letter_port import DeleteCoronersLetterPort
from app.ports.get_coroners_letter_port import GetCoronersLetterPort
from app.ports.sds_port import SdsPort
from app.use_cases.delete_coroners_letter import DeleteCoronersLetterUseCase
from app.use_cases.exceptions import (
    CoronersLetterDeleteError,
    CoronersLetterNotFoundError,
)


def _make_coroners_letter(
    sds_file_name: str = "coroners-letter_abc123.pdf",
    file_name: str = "test-coroners-letter.pdf",
) -> CoronersLetter:
    return CoronersLetter(sds_file_name=sds_file_name, file_name=file_name)


def test_execute_deletes_file_from_sds_and_db():
    get_coroners_letter_port = MagicMock(spec=GetCoronersLetterPort)
    get_coroners_letter_port.get_coroners_letter_by_id.return_value = (
        _make_coroners_letter()
    )

    delete_coroners_letter_port = MagicMock(spec=DeleteCoronersLetterPort)
    delete_coroners_letter_port.delete_coroners_letter_by_id.return_value = True

    sds_port = MagicMock(spec=SdsPort)

    use_case = DeleteCoronersLetterUseCase(
        get_coroners_letter_port=get_coroners_letter_port,
        delete_coroners_letter_port=delete_coroners_letter_port,
        sds_port=sds_port,
    )

    coroners_letter_id = uuid.uuid4()
    use_case.execute(coroners_letter_id)

    sds_port.delete_coroners_letter.assert_called_once_with(
        "coroners-letter_abc123.pdf"
    )
    delete_coroners_letter_port.delete_coroners_letter_by_id.assert_called_once_with(
        coroners_letter_id
    )


def test_execute_raises_not_found_when_coroners_letter_missing():
    get_coroners_letter_port = MagicMock(spec=GetCoronersLetterPort)
    get_coroners_letter_port.get_coroners_letter_by_id.return_value = None

    delete_coroners_letter_port = MagicMock(spec=DeleteCoronersLetterPort)
    sds_port = MagicMock(spec=SdsPort)

    use_case = DeleteCoronersLetterUseCase(
        get_coroners_letter_port=get_coroners_letter_port,
        delete_coroners_letter_port=delete_coroners_letter_port,
        sds_port=sds_port,
    )

    with pytest.raises(CoronersLetterNotFoundError):
        use_case.execute(uuid.uuid4())

    sds_port.delete_coroners_letter.assert_not_called()
    delete_coroners_letter_port.delete_coroners_letter_by_id.assert_not_called()


def test_execute_raises_delete_error_when_sds_delete_fails():
    get_coroners_letter_port = MagicMock(spec=GetCoronersLetterPort)
    get_coroners_letter_port.get_coroners_letter_by_id.return_value = (
        _make_coroners_letter()
    )

    delete_coroners_letter_port = MagicMock(spec=DeleteCoronersLetterPort)
    sds_port = MagicMock(spec=SdsPort)
    sds_port.delete_coroners_letter.side_effect = Exception("SDS failed")

    use_case = DeleteCoronersLetterUseCase(
        get_coroners_letter_port=get_coroners_letter_port,
        delete_coroners_letter_port=delete_coroners_letter_port,
        sds_port=sds_port,
    )

    with pytest.raises(CoronersLetterDeleteError):
        use_case.execute(uuid.uuid4())


def test_execute_raises_not_found_when_db_delete_returns_false():
    get_coroners_letter_port = MagicMock(spec=GetCoronersLetterPort)
    get_coroners_letter_port.get_coroners_letter_by_id.return_value = (
        _make_coroners_letter()
    )

    delete_coroners_letter_port = MagicMock(spec=DeleteCoronersLetterPort)
    delete_coroners_letter_port.delete_coroners_letter_by_id.return_value = False

    sds_port = MagicMock(spec=SdsPort)

    use_case = DeleteCoronersLetterUseCase(
        get_coroners_letter_port=get_coroners_letter_port,
        delete_coroners_letter_port=delete_coroners_letter_port,
        sds_port=sds_port,
    )

    with pytest.raises(CoronersLetterNotFoundError):
        use_case.execute(uuid.uuid4())
