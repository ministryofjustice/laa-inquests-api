import asyncio
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.models.application.enums import MeritsDecision
from app.routers.applications import search_application
from app.use_cases.exceptions import ProviderDetailsRetrievalError

# TODO: Add required tests for office codes


def test_search_application_calls_use_case_with_the_laa_reference():
    use_case = MagicMock()
    use_case.execute.return_value = [MagicMock()]

    asyncio.run(
        search_application(
            "  1  ",
            merits_decision=None,
            firm_code="0A123B",
            office_codes=frozenset(["0U651L"]),
            use_case=use_case,
        )
    )

    use_case.execute.assert_called_once_with(
        "  1  ", "0A123B", frozenset(["0U651L"]), None
    )


def test_search_application_calls_use_case_with_merits_decision_when_provided():
    use_case = MagicMock()
    use_case.execute.return_value = [MagicMock()]

    asyncio.run(
        search_application(
            "1",
            merits_decision=MeritsDecision.GRANTED,
            firm_code="0A123B",
            office_codes=frozenset(["0U651L"]),
            use_case=use_case,
        )
    )

    use_case.execute.assert_called_once_with(
        "1", "0A123B", frozenset(["0U651L"]), MeritsDecision.GRANTED
    )


def test_search_application_returns_empty_list_when_use_case_returns_empty():
    use_case = MagicMock()
    use_case.execute.return_value = []

    result = asyncio.run(
        search_application(
            "99999",
            merits_decision=None,
            firm_code="0A123B",
            office_codes=frozenset(["0U651L"]),
            use_case=use_case,
        )
    )

    assert result == []


def test_search_application_raises_500_when_provider_details_lookup_fails():
    use_case = MagicMock()
    use_case.execute.side_effect = ProviderDetailsRetrievalError()

    with pytest.raises(HTTPException) as exception:
        asyncio.run(
            search_application(
                "1",
                merits_decision=None,
                firm_code="0A123B",
                office_codes=frozenset(["0U651L"]),
                use_case=use_case,
            )
        )

    assert exception.value.status_code == 500
    assert (
        exception.value.detail
        == "Failed to retrieve firm name from provider details service"
    )
