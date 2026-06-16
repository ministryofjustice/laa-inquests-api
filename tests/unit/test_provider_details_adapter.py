from unittest.mock import MagicMock, patch


def test_get_firm_name_returns_firm_name_from_successful_api_response():
    from app.adapters.provider_details_adapter import ProviderDetailsAdapter

    mock_response = MagicMock()
    mock_response.json.return_value = {"firm": {"firmName": "Smith & Co"}}

    with patch("httpx.get", return_value=mock_response):
        adapter = ProviderDetailsAdapter(
            base_url="https://example.com", api_key="test-key"
        )
        result = adapter.get_firm_name("0A123B")

    assert result == "Smith & Co"


def test_get_firm_name_calls_correct_url_with_api_key_header():
    from app.adapters.provider_details_adapter import ProviderDetailsAdapter

    mock_response = MagicMock()
    mock_response.json.return_value = {"firm": {"firmName": "Smith & Co"}}

    with patch("httpx.get", return_value=mock_response) as mock_get:
        adapter = ProviderDetailsAdapter(
            base_url="https://example.com", api_key="test-key"
        )
        adapter.get_firm_name("0A123B")

    mock_get.assert_called_once_with(
        "https://example.com/api/v1/provider-firms/0A123B",
        headers={"X-Authorization": "test-key"},
    )


def test_get_office_email_returns_email_from_successful_api_response():
    from app.adapters.provider_details_adapter import ProviderDetailsAdapter

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "offices": [{"emailAddress": "test@example.com"}]
    }

    with patch("httpx.get", return_value=mock_response):
        adapter = ProviderDetailsAdapter(
            base_url="https://example.com", api_key="test-key"
        )
        result = adapter.get_office_email("0A123B", "001")

    assert result == "test@example.com"


def test_get_office_email_calls_correct_url_with_api_key_header():
    from app.adapters.provider_details_adapter import ProviderDetailsAdapter

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "offices": [{"emailAddress": "test@example.com"}]
    }

    with patch("httpx.get", return_value=mock_response) as mock_get:
        adapter = ProviderDetailsAdapter(
            base_url="https://example.com", api_key="test-key"
        )
        adapter.get_office_email("0A123B", "001")

    mock_get.assert_called_once_with(
        "https://example.com/api/v1/provider-firms/0A123B/provider-offices/001",
        headers={"X-Authorization": "test-key"},
    )


def test_get_firm_name_returns_none_when_api_returns_http_error():
    import httpx as _httpx
    from app.adapters.provider_details_adapter import ProviderDetailsAdapter

    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = _httpx.HTTPStatusError(
        "error", request=MagicMock(), response=MagicMock()
    )

    with patch("httpx.get", return_value=mock_response):
        adapter = ProviderDetailsAdapter(
            base_url="https://example.com", api_key="test-key"
        )
        result = adapter.get_firm_name("0A123B")

    assert result is None


def test_get_office_email_returns_none_when_api_returns_http_error():
    import httpx as _httpx
    from app.adapters.provider_details_adapter import ProviderDetailsAdapter

    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = _httpx.HTTPStatusError(
        "error", request=MagicMock(), response=MagicMock()
    )

    with patch("httpx.get", return_value=mock_response):
        adapter = ProviderDetailsAdapter(
            base_url="https://example.com", api_key="test-key"
        )
        result = adapter.get_office_email("0A123B", "001")

    assert result is None


def test_get_firm_name_returns_none_when_request_raises_exception():
    import httpx as _httpx
    from app.adapters.provider_details_adapter import ProviderDetailsAdapter

    with patch("httpx.get", side_effect=_httpx.RequestError("connection failed")):
        adapter = ProviderDetailsAdapter(
            base_url="https://example.com", api_key="test-key"
        )
        result = adapter.get_firm_name("0A123B")

    assert result is None


def test_get_office_email_returns_none_when_request_raises_exception():
    import httpx as _httpx
    from app.adapters.provider_details_adapter import ProviderDetailsAdapter

    with patch("httpx.get", side_effect=_httpx.RequestError("connection failed")):
        adapter = ProviderDetailsAdapter(
            base_url="https://example.com", api_key="test-key"
        )
        result = adapter.get_office_email("0A123B", "001")

    assert result is None
