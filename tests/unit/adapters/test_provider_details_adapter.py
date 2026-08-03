from unittest.mock import MagicMock, patch

import pytest

from app.adapters.provider_details_adapter import ProviderDetailsAdapter
from app.use_cases.exceptions import ProviderDetailsRetrievalError


@pytest.fixture
def adapter() -> ProviderDetailsAdapter:
    return ProviderDetailsAdapter(base_url="https://example.com", api_key="test-key")


def test_get_firm_name_returns_firm_name_from_successful_api_response(adapter):
    mock_response = MagicMock()
    mock_response.json.return_value = {"firm": {"firmName": "Smith & Co"}}

    with patch("httpx.get", return_value=mock_response):
        result = adapter.get_firm_name("0A123B")

    assert result == "Smith & Co"


def test_get_firm_name_calls_correct_url_with_api_key_header(adapter):
    mock_response = MagicMock()
    mock_response.json.return_value = {"firm": {"firmName": "Smith & Co"}}

    with patch("httpx.get", return_value=mock_response) as mock_get:
        adapter.get_firm_name("0A123B")

    mock_get.assert_called_once_with(
        "https://example.com/api/v1/provider-firms/0A123B",
        headers={"X-Authorization": "test-key"},
    )


def test_get_firm_name_raises_provider_details_retrieval_error_when_api_returns_http_error(
    adapter,
):
    import httpx as _httpx

    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = _httpx.HTTPStatusError(
        "error", request=MagicMock(), response=MagicMock()
    )

    with patch("httpx.get", return_value=mock_response):
        with pytest.raises(ProviderDetailsRetrievalError) as exc_info:
            adapter.get_firm_name("0A123B")

    assert (
        str(exc_info.value) == "HTTP error occurred while retrieving provider details"
    )


def test_get_firm_name_raises_provider_details_retrieval_error_when_request_raises_exception(
    adapter,
):
    import httpx as _httpx

    with patch("httpx.get", side_effect=_httpx.RequestError("connection failed")):
        with pytest.raises(ProviderDetailsRetrievalError) as exc_info:
            adapter.get_firm_name("0A123B")

    assert (
        str(exc_info.value) == "HTTP error occurred while retrieving provider details"
    )


def test_get_office_address_returns_full_address_from_successful_api_response(adapter):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "office": {
            "addressLine1": "123 Main St",
            "addressLine2": "Suite 100",
            "city": "London",
            "county": "Greater London",
            "postCode": "AB12 3CD",
        }
    }

    with patch("httpx.get", return_value=mock_response):
        result = adapter.get_office_address("OFFICE123")

    assert result is not None
    assert result.address_line_1 == "123 Main St"
    assert result.address_line_2 == "Suite 100"
    assert result.town_or_city == "London"
    assert result.county == "Greater London"
    assert result.postcode == "AB12 3CD"


def test_get_office_address_raises_provider_details_retrieval_error_when_request_raises_exception(
    adapter,
):
    import httpx as _httpx

    with patch("httpx.get", side_effect=_httpx.RequestError("connection failed")):
        with pytest.raises(ProviderDetailsRetrievalError) as exc_info:
            adapter.get_office_address("OFFICE123")

    assert (
        str(exc_info.value) == "HTTP error occurred while retrieving provider details"
    )


def test_get_office_address_raises_provider_details_retrieval_error_when_api_returns_http_error(
    adapter,
):
    import httpx as _httpx

    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = _httpx.HTTPStatusError(
        "error", request=MagicMock(), response=MagicMock()
    )

    with patch("httpx.get", return_value=mock_response):
        with pytest.raises(ProviderDetailsRetrievalError) as exc_info:
            adapter.get_office_address("0U651L")

    assert (
        str(exc_info.value) == "HTTP error occurred while retrieving provider details"
    )
