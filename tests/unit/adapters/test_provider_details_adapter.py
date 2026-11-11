from unittest.mock import MagicMock, patch

import httpx as _httpx
import pytest

from app.adapters.provider_details_adapter import ProviderDetailsAdapter
from app.use_cases.exceptions import (
    ProviderDetailsRetrievalError,
    ProviderOfficeNotFoundError,
)


@pytest.fixture
def adapter() -> ProviderDetailsAdapter:
    return ProviderDetailsAdapter(base_url="https://example.com", api_key="test-key")


def test_get_firm_name_returns_firm_name_from_successful_api_response(adapter):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"firm": {"firmName": "Smith & Co"}}

    with patch("httpx.get", return_value=mock_response):
        result = adapter.get_firm_name("1234", "OFFICE123")

    assert result == "Smith & Co"


def test_get_firm_name_calls_correct_url_with_api_key_header(adapter):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"firm": {"firmName": "Smith & Co"}}

    with patch("httpx.get", return_value=mock_response) as mock_get:
        adapter.get_firm_name("1234", "OFFICE123")

    mock_get.assert_called_once_with(
        "https://example.com/api/v1/provider-firms/1234",
        headers={"X-Authorization": "test-key"},
    )


def test_get_firm_name_raises_provider_details_retrieval_error_when_api_returns_http_error(
    adapter,
):
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.raise_for_status.side_effect = _httpx.HTTPStatusError(
        "error", request=MagicMock(), response=MagicMock()
    )

    with (
        patch("httpx.get", return_value=mock_response),
        pytest.raises(ProviderDetailsRetrievalError) as exc_info,
    ):
        adapter.get_firm_name("1234", "OFFICE123")

    assert (
        str(exc_info.value)
        == "HTTP error occurred while retrieving provider details: error"
    )


def test_get_firm_name_raises_provider_details_retrieval_error_when_request_raises_exception(
    adapter,
):
    with (
        patch("httpx.get", side_effect=_httpx.RequestError("connection failed")),
        pytest.raises(ProviderDetailsRetrievalError) as exc_info,
    ):
        adapter.get_firm_name("1234", "OFFICE123")

    assert (
        str(exc_info.value)
        == "HTTP error occurred while retrieving provider details: connection failed"
    )


def test_get_firm_name_accepts_null_firm_name_on_200_response(adapter):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"firm": {"firmName": None}}

    with patch("httpx.get", return_value=mock_response):
        result = adapter.get_firm_name("1234", "OFFICE123")

    assert result is None


def test_get_firm_name_falls_back_to_office_lookup_on_204(adapter):
    firm_response = MagicMock()
    firm_response.status_code = 204
    office_response = MagicMock()
    office_response.status_code = 200
    office_response.json.return_value = {"firm": {"firmName": "Smith & Co"}}

    with patch("httpx.get", side_effect=[firm_response, office_response]) as mock_get:
        result = adapter.get_firm_name("1234", "OFFICE123")

    assert result == "Smith & Co"
    mock_get.assert_any_call(
        "https://example.com/api/v1/provider-firms/1234",
        headers={"X-Authorization": "test-key"},
    )
    mock_get.assert_any_call(
        "https://example.com/api/v1/provider-offices/OFFICE123",
        headers={"X-Authorization": "test-key"},
    )


def test_get_firm_name_fallback_accepts_null_firm_name(adapter):
    firm_response = MagicMock()
    firm_response.status_code = 204
    office_response = MagicMock()
    office_response.status_code = 200
    office_response.json.return_value = {"firm": {"firmName": None}}

    with patch("httpx.get", side_effect=[firm_response, office_response]):
        result = adapter.get_firm_name("1234", "OFFICE123")

    assert result is None


def test_get_firm_name_raises_provider_office_not_found_when_both_lookups_give_204(
    adapter,
):
    firm_response = MagicMock()
    firm_response.status_code = 204
    office_response = MagicMock()
    office_response.status_code = 204

    with (
        patch("httpx.get", side_effect=[firm_response, office_response]),
        pytest.raises(ProviderOfficeNotFoundError) as exc_info,
    ):
        adapter.get_firm_name("1234", "OFFICE123")

    assert str(exc_info.value) == "Office OFFICE123 details not found for firm 1234"


def test_get_firm_name_raises_provider_details_retrieval_error_when_office_fallback_http_errors(
    adapter,
):
    firm_response = MagicMock()
    firm_response.status_code = 204
    office_response = MagicMock()
    office_response.raise_for_status.side_effect = _httpx.HTTPStatusError(
        "error", request=MagicMock(), response=MagicMock()
    )

    with (
        patch("httpx.get", side_effect=[firm_response, office_response]),
        pytest.raises(ProviderDetailsRetrievalError) as exc_info,
    ):
        adapter.get_firm_name("1234", "OFFICE123")

    assert (
        str(exc_info.value)
        == "HTTP error occurred while retrieving provider details: error"
    )


def test_get_firm_name_logs_fallback_used_on_204(adapter, caplog):
    import logging

    firm_response = MagicMock()
    firm_response.status_code = 204
    office_response = MagicMock()
    office_response.status_code = 200
    office_response.json.return_value = {"firm": {"firmName": "Smith & Co"}}

    with (
        patch("httpx.get", side_effect=[firm_response, office_response]),
        caplog.at_level(logging.INFO),
    ):
        adapter.get_firm_name("1234", "OFFICE123")

    assert "No offices found for firm 1234" in caplog.text


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
    with (
        patch("httpx.get", side_effect=_httpx.RequestError("connection failed")),
        pytest.raises(ProviderDetailsRetrievalError) as exc_info,
    ):
        adapter.get_office_address("OFFICE123")

    assert (
        str(exc_info.value)
        == "HTTP error occurred while retrieving provider details: connection failed"
    )


def test_get_office_address_raises_provider_details_retrieval_error_when_api_returns_http_error(
    adapter,
):
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = _httpx.HTTPStatusError(
        "error", request=MagicMock(), response=MagicMock()
    )

    with (
        patch("httpx.get", return_value=mock_response),
        pytest.raises(ProviderDetailsRetrievalError) as exc_info,
    ):
        adapter.get_office_address("0U651L")

    assert (
        str(exc_info.value)
        == "HTTP error occurred while retrieving provider details: error"
    )


def test_get_office_address_raises_provider_office_not_found_on_204(adapter):
    mock_response = MagicMock()
    mock_response.status_code = 204

    with (
        patch("httpx.get", return_value=mock_response),
        pytest.raises(ProviderOfficeNotFoundError) as exc_info,
    ):
        adapter.get_office_address("OFFICE123")

    assert str(exc_info.value) == "Office OFFICE123 not found"


def test_provider_office_not_found_error_is_a_provider_details_retrieval_error():
    assert issubclass(ProviderOfficeNotFoundError, ProviderDetailsRetrievalError)


class TestGetFirmsByIds:
    def test_returns_list_of_firms_from_successful_api_response(self, adapter):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "firms": [
                {"firmNumber": "1234", "firmName": "Smith & Co"},
                {"firmNumber": "4567", "firmName": "Jones LLP"},
            ]
        }

        with patch("httpx.post", return_value=mock_response):
            result = adapter.get_firms_by_ids(["1234", "4567"])

        assert len(result) == 2
        assert result[0]["firmNumber"] == "1234"
        assert result[0]["firmName"] == "Smith & Co"
        assert result[1]["firmNumber"] == "4567"
        assert result[1]["firmName"] == "Jones LLP"

    def test_calls_correct_url_with_firm_ids_payload(self, adapter):
        mock_response = MagicMock()
        mock_response.json.return_value = {"firms": []}

        with patch("httpx.post", return_value=mock_response) as mock_post:
            adapter.get_firms_by_ids(["1234", "4567"])

        mock_post.assert_called_once_with(
            "https://example.com/api/v1/provider-firms",
            json={"firmIds": ["1234", "4567"]},
            headers={"X-Authorization": "test-key"},
        )

    def test_returns_empty_list_when_firm_ids_is_empty(self, adapter):
        result = adapter.get_firms_by_ids([])

        assert result == []

    def test_raises_provider_details_retrieval_error_on_http_error(self, adapter):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = _httpx.HTTPStatusError(
            "error", request=MagicMock(), response=MagicMock()
        )

        with (
            patch("httpx.post", return_value=mock_response),
            pytest.raises(ProviderDetailsRetrievalError),
        ):
            adapter.get_firms_by_ids(["1234"])

    def test_raises_provider_details_retrieval_error_on_request_error(self, adapter):
        with (
            patch("httpx.post", side_effect=_httpx.RequestError("connection failed")),
            pytest.raises(ProviderDetailsRetrievalError),
        ):
            adapter.get_firms_by_ids(["1234"])


class TestGetProviderOfficesByFirmId:
    def test_returns_required_data_from_successful_api_response(self, adapter):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "offices": [
                {
                    "firmOfficeCode": "0A123A",
                    "addressLine1": "1 Test Street",
                    "addressLine2": "Suite 2",
                    "city": "London",
                    "county": "Greater London",
                    "postCode": "SW1A 1AA",
                },
                {
                    "firmOfficeCode": "0A456A",
                    "addressLine1": "2 Test Street",
                    "addressLine2": "Suite 3",
                    "city": "Manchester",
                    "county": "Greater Manchester",
                    "postCode": "M1A 1AA",
                },
            ]
        }

        with patch("httpx.get", return_value=mock_response):
            result = adapter.get_provider_offices_by_firm_id("1234")

        assert result == [
            {
                "office_code": "0A123A",
                "address": {
                    "address_line_1": "1 Test Street",
                    "address_line_2": "Suite 2",
                    "town_or_city": "London",
                    "county": "Greater London",
                    "postcode": "SW1A 1AA",
                },
            },
            {
                "office_code": "0A456A",
                "address": {
                    "address_line_1": "2 Test Street",
                    "address_line_2": "Suite 3",
                    "town_or_city": "Manchester",
                    "county": "Greater Manchester",
                    "postcode": "M1A 1AA",
                },
            },
        ]

    def test_calls_correct_provider_offices_url_with_api_key_header(self, adapter):
        mock_response = MagicMock()
        mock_response.json.return_value = {"offices": []}

        with patch("httpx.get", return_value=mock_response) as mock_get:
            adapter.get_provider_offices_by_firm_id("1234")

        mock_get.assert_called_once_with(
            "https://example.com/api/v1/provider-firms/1234/provider-offices",
            headers={"X-Authorization": "test-key"},
        )

    def test_raises_provider_details_retrieval_error_on_http_error(self, adapter):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = _httpx.HTTPStatusError(
            "error", request=MagicMock(), response=MagicMock()
        )

        with (
            patch("httpx.get", return_value=mock_response),
            pytest.raises(ProviderDetailsRetrievalError),
        ):
            adapter.get_provider_offices_by_firm_id("1234")

    def test_raises_provider_details_retrieval_error_with_message_on_http_error(
        self, adapter
    ):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = _httpx.HTTPStatusError(
            "error", request=MagicMock(), response=MagicMock()
        )

        with (
            patch("httpx.get", return_value=mock_response),
            pytest.raises(ProviderDetailsRetrievalError) as exc_info,
        ):
            adapter.get_provider_offices_by_firm_id("1234")

        assert (
            str(exc_info.value)
            == "HTTP error occurred while retrieving provider details: error"
        )

    def test_raises_provider_details_retrieval_error_on_invalid_payload(self, adapter):
        mock_response = MagicMock()
        mock_response.json.return_value = {"unexpected": []}

        with (
            patch("httpx.get", return_value=mock_response),
            pytest.raises(ProviderDetailsRetrievalError) as exc_info,
        ):
            adapter.get_provider_offices_by_firm_id("1234")

        assert (
            str(exc_info.value) == "Unexpected provider-offices response for firm 1234"
        )
