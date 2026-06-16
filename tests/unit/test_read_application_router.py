import asyncio
import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException

from app.use_cases.exceptions import ApplicationNotFoundError
from app.routers.applications import read_application


def test_200_read_application_returns_application_response():
    use_case = MagicMock()
    use_case.execute.return_value = MagicMock()

    asyncio.run(read_application("123456", use_case=use_case))

    use_case.execute.assert_called_once_with("123456")


def test_read_application_raises_404_when_use_case_raises_application_not_found_error():
    use_case = MagicMock()
    use_case.execute.side_effect = ApplicationNotFoundError("not found")

    with pytest.raises(HTTPException) as exc:
        asyncio.run(read_application("99999", use_case=use_case))

    assert exc.value.status_code == 404
