from unittest.mock import MagicMock

from app import api
from app.routers.applications import get_provider_details_port
from app.use_cases.exceptions import ProviderDetailsRetrievalError


def override_provider_details_port_with_provider_offices() -> None:
    def get_provider_details_port_override():
        mock_port = MagicMock()
        mock_port.get_provider_offices_by_firm_id.return_value = [
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
        return mock_port

    api.dependency_overrides[get_provider_details_port] = (
        get_provider_details_port_override
    )


def override_provider_details_port_with_error() -> None:
    def get_provider_details_port_override_with_error():
        mock_port = MagicMock()
        mock_port.get_provider_offices_by_firm_id.side_effect = (
            ProviderDetailsRetrievalError()
        )
        return mock_port

    api.dependency_overrides[get_provider_details_port] = (
        get_provider_details_port_override_with_error
    )
