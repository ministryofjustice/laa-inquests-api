import logging
from unittest.mock import MagicMock

import pytest

from app.ports.provider_details_port import ProviderDetailsPort
from app.use_cases.exceptions import ProviderDetailsRetrievalError
from app.use_cases.list_provider_offices import ListProviderOfficesUseCase


def test_execute_returns_provider_offices_for_firm_id():
    provider_details_port = MagicMock(spec=ProviderDetailsPort)
    provider_details_port.get_provider_offices_by_firm_id.return_value = [
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

    result = ListProviderOfficesUseCase(provider_details_port).execute("123")

    provider_details_port.get_provider_offices_by_firm_id.assert_called_once_with("123")
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


def test_execute_raises_when_provider_details_lookup_fails():
    provider_details_port = MagicMock(spec=ProviderDetailsPort)
    provider_details_port.get_provider_offices_by_firm_id.side_effect = (
        ProviderDetailsRetrievalError("upstream error")
    )

    use_case = ListProviderOfficesUseCase(provider_details_port)

    with pytest.raises(ProviderDetailsRetrievalError):
        use_case.execute("123")


def test_execute_logs_success(caplog):
    provider_details_port = MagicMock(spec=ProviderDetailsPort)
    provider_details_port.get_provider_offices_by_firm_id.return_value = [
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

    use_case = ListProviderOfficesUseCase(provider_details_port)

    with caplog.at_level(logging.INFO):
        use_case.execute("123")

    assert "Provider offices listed" in caplog.text
