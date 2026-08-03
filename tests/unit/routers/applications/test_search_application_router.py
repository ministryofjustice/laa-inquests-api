import asyncio
from unittest.mock import MagicMock

from app.routers.applications import search_application


def test_search_application_calls_use_case_with_the_laa_reference():
    use_case = MagicMock()
    use_case.execute.return_value = [MagicMock()]

    asyncio.run(search_application("  1  ", firm_code="0A123B", use_case=use_case))

    use_case.execute.assert_called_once_with("  1  ", "0A123B")


def test_search_application_returns_empty_list_when_use_case_returns_empty():
    use_case = MagicMock()
    use_case.execute.return_value = []

    result = asyncio.run(
        search_application("99999", firm_code="0A123B", use_case=use_case)
    )

    assert result == []
