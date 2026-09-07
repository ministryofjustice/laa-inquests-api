import asyncio
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.routers.applications import list_provider_offices
from app.use_cases.exceptions import ProviderDetailsRetrievalError


def test_list_provider_offices_calls_use_case_with_firm_id():
    use_case = MagicMock()
    use_case.execute.return_value = []

    asyncio.run(
        list_provider_offices(
            firm_id="123",
            use_case=use_case,
        )
    )

    use_case.execute.assert_called_once_with("123")


def test_list_provider_offices_returns_required_data():
    use_case = MagicMock()
    use_case.execute.return_value = [
        {
            "office_code": "0A123A",
            "address": {
                "address_line_1": "1 Test Street",
                "address_line_2": "",
                "town_or_city": "London",
                "county": "",
                "postcode": "SW1A 1AA",
            },
        }
    ]

    result = asyncio.run(
        list_provider_offices(
            firm_id="123",
            use_case=use_case,
        )
    )

    assert result == [
        {
            "office_code": "0A123A",
            "address": {
                "address_line_1": "1 Test Street",
                "address_line_2": "",
                "town_or_city": "London",
                "county": "",
                "postcode": "SW1A 1AA",
            },
        }
    ]


def test_list_provider_offices_raises_500_when_provider_details_lookup_fails():
    use_case = MagicMock()
    use_case.execute.side_effect = ProviderDetailsRetrievalError()

    with pytest.raises(HTTPException) as exception:
        asyncio.run(
            list_provider_offices(
                firm_id="123",
                use_case=use_case,
            )
        )

    assert exception.value.status_code == 500
    assert (
        exception.value.detail
        == "Failed to retrieve provider offices from provider details service"
    )
