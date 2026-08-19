from unittest.mock import MagicMock, patch

import httpx as _httpx
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
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = _httpx.HTTPStatusError(
        "error", request=MagicMock(), response=MagicMock()
    )

    with (
        patch("httpx.get", return_value=mock_response),
        pytest.raises(ProviderDetailsRetrievalError) as exc_info,
    ):
        adapter.get_firm_name("0A123B")

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
        adapter.get_firm_name("0A123B")

    assert (
        str(exc_info.value)
        == "HTTP error occurred while retrieving provider details: connection failed"
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


class TestGetFirmsByIds:
    def test_returns_list_of_firms_from_successful_api_response(self, adapter):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "firms": [
                {"firmNumber": "0A123B", "firmName": "Smith & Co"},
                {"firmNumber": "0B456C", "firmName": "Jones LLP"},
            ]
        }

        with patch("httpx.post", return_value=mock_response):
            result = adapter.get_firms_by_ids(["0A123B", "0B456C"])

        assert len(result) == 2
        assert result[0]["firmNumber"] == "0A123B"
        assert result[0]["firmName"] == "Smith & Co"
        assert result[1]["firmNumber"] == "0B456C"
        assert result[1]["firmName"] == "Jones LLP"

    def test_calls_correct_url_with_firm_ids_payload(self, adapter):
        mock_response = MagicMock()
        mock_response.json.return_value = {"firms": []}

        with patch("httpx.post", return_value=mock_response) as mock_post:
            adapter.get_firms_by_ids(["0A123B", "0B456C"])

        mock_post.assert_called_once_with(
            "https://example.com/api/v1/provider-firms",
            json={"firmIds": ["0A123B", "0B456C"]},
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
            adapter.get_firms_by_ids(["0A123B"])

    def test_raises_provider_details_retrieval_error_on_request_error(self, adapter):
        with (
            patch("httpx.post", side_effect=_httpx.RequestError("connection failed")),
            pytest.raises(ProviderDetailsRetrievalError),
        ):
            adapter.get_firms_by_ids(["0A123B"])


class TestDoesOfficeExist:
    def test_does_not_raise_when_office_exists(self, adapter):
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
            adapter.does_office_exist("OFFICE123")

    def test_raises_provider_details_retrieval_error_when_api_returns_http_error(
        self, adapter
    ):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = _httpx.HTTPStatusError(
            "error", request=MagicMock(), response=MagicMock()
        )

        with (
            patch("httpx.get", return_value=mock_response),
            pytest.raises(ProviderDetailsRetrievalError),
        ):
            adapter.does_office_exist("OFFICE123")

    def test_raises_provider_details_retrieval_error_when_request_raises_exception(
        self, adapter
    ):
        with (
            patch("httpx.get", side_effect=_httpx.RequestError("connection failed")),
            pytest.raises(ProviderDetailsRetrievalError),
        ):
            adapter.does_office_exist("OFFICE123")

    def test_delegates_to_get_office_address_with_correct_office_id(self, adapter):
        with patch.object(adapter, "get_office_address") as mock_get:
            adapter.does_office_exist("0U651L")

        mock_get.assert_called_once_with("0U651L")

    def test_logs_success_when_office_exists(self, adapter, caplog):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "office": {
                "addressLine1": "123 Main St",
                "addressLine2": "",
                "city": "London",
                "county": "Greater London",
                "postCode": "AB12 3CD",
            }
        }

        with patch("httpx.get", return_value=mock_response):
            import logging

            with caplog.at_level(logging.INFO):
                adapter.does_office_exist("OFFICE123")

        assert "Provider office address lookup succeeded" in caplog.text

    def test_logs_error_when_office_lookup_fails(self, adapter, caplog):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = _httpx.HTTPStatusError(
            "error", request=MagicMock(), response=MagicMock()
        )

        import logging

        with (
            patch("httpx.get", return_value=mock_response),
            caplog.at_level(logging.ERROR),
            pytest.raises(ProviderDetailsRetrievalError),
        ):
            adapter.does_office_exist("OFFICE123")

        assert "Provider office address lookup failed" in caplog.text
