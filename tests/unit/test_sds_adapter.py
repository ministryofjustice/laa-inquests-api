import uuid
from unittest.mock import MagicMock, patch

import httpx


def _make_adapter():
    from app.adapters.sds_adapter import SdsAdapter

    return SdsAdapter(
        base_url="https://sds.example.com",
        tenant_id="tenant-123",
        client_id="client-id",
        client_secret="client-secret",
        scope="https://sds.example.com/.default",
    )


def _mock_token_response(token: str = "test-token") -> MagicMock:
    mock = MagicMock()
    mock.json.return_value = {"access_token": token}
    return mock


def _mock_save_response() -> MagicMock:
    mock = MagicMock()
    mock.status_code = 201
    mock.json.return_value = {
        "success": "File saved successfully in laa-sds-inquests-uat with key letter.pdf",
        "checksum": "abc123checksum",
    }
    return mock


def _mock_save_failure_response() -> MagicMock:
    mock = MagicMock()
    mock.status_code = 500
    mock.json.return_value = {
        "error": "Internal Server Error",
        "message": "File could not be saved",
    }
    return mock


def test_get_token_posts_client_credentials_to_correct_url():
    adapter = _make_adapter()
    token_response = _mock_token_response()

    with patch("httpx.post", return_value=token_response) as mock_post:
        adapter._get_token()

    mock_post.assert_called_once_with(
        "https://login.microsoftonline.com/tenant-123/oauth2/v2.0/token",
        data={
            "grant_type": "client_credentials",
            "client_id": "client-id",
            "client_secret": "client-secret",
            "scope": "https://sds.example.com/.default",
        },
    )


def test_get_token_returns_access_token():
    adapter = _make_adapter()

    with patch("httpx.post", return_value=_mock_token_response("my-token")):
        result = adapter._get_token()

    assert result == "my-token"


def test_save_coroners_letter_posts_to_correct_url_with_bearer_token():
    adapter = _make_adapter()

    with patch(
        "httpx.post", side_effect=[_mock_token_response(), _mock_save_response()]
    ) as mock_post:
        adapter.save_coroners_letter(b"file content", "letter.pdf")

    save_call = mock_post.call_args_list[1]
    assert save_call.args[0] == "https://sds.example.com/save_file"
    assert save_call.kwargs["headers"] == {"Authorization": "Bearer test-token"}


def test_save_coroners_letter_sends_file_bytes_in_multipart():
    adapter = _make_adapter()

    with patch(
        "httpx.post", side_effect=[_mock_token_response(), _mock_save_response()]
    ) as mock_post:
        adapter.save_coroners_letter(b"pdf bytes here", "letter.pdf")

    save_call = mock_post.call_args_list[1]
    file_tuple = save_call.kwargs["files"]["file"]
    assert file_tuple[1] == b"pdf bytes here"
    assert file_tuple[2] == "application/octet-stream"


def test_save_coroners_letter_generates_unique_file_name_with_readable_stem():
    adapter = _make_adapter()

    with patch(
        "httpx.post", side_effect=[_mock_token_response(), _mock_save_response()]
    ) as mock_post:
        adapter.save_coroners_letter(b"content", "coroners_letter.pdf")

    save_call = mock_post.call_args_list[1]
    stored_name = save_call.kwargs["files"]["file"][0]

    stem, suffix = stored_name.rsplit(".", 1)
    readable_part, uuid_part = stem.rsplit("_", 1)
    assert readable_part == "coroners_letter"
    assert suffix == "pdf"
    uuid.UUID(uuid_part)  # raises ValueError if not a valid UUID


def test_save_coroners_letter_two_calls_produce_different_file_names():
    adapter = _make_adapter()

    with patch(
        "httpx.post",
        side_effect=[
            _mock_token_response(),
            _mock_save_response(),
            _mock_token_response(),
            _mock_save_response(),
        ],
    ) as mock_post:
        adapter.save_coroners_letter(b"content", "letter.pdf")
        adapter.save_coroners_letter(b"content", "letter.pdf")

    name_1 = mock_post.call_args_list[1].kwargs["files"]["file"][0]
    name_2 = mock_post.call_args_list[3].kwargs["files"]["file"][0]
    assert name_1 != name_2


def test_save_coroners_letter_returns_response_with_correct_fields():
    adapter = _make_adapter()

    with patch(
        "httpx.post",
        side_effect=[_mock_token_response(), _mock_save_response()],
    ):
        result = adapter.save_coroners_letter(b"content", "letter.pdf")

    assert result.status == "SUCCESS"
    assert result.sds_file_name.startswith("letter_")
    assert result.sds_file_name.endswith(".pdf")


def test_save_coroners_letter_returns_failure_when_sds_fails():
    adapter = _make_adapter()

    with patch(
        "httpx.post",
        side_effect=[_mock_token_response(), _mock_save_failure_response()],
    ):
        result = adapter.save_coroners_letter(b"content", "letter.pdf")

    assert result.status == "FAILURE"
    assert result.sds_file_name.startswith("letter_")
    assert result.sds_file_name.endswith(".pdf")


def test_retrieve_coroners_letter_gets_correct_url_with_file_key_param():
    adapter = _make_adapter()

    with patch("httpx.post", return_value=_mock_token_response()), patch(
        "httpx.get", return_value=MagicMock(status_code=200, content=b"file bytes")
    ) as mock_get:
        adapter.retrieve_coroners_letter("test-document.rtf")

    mock_get.assert_called_once_with(
        "https://sds.example.com/get_file",
        params={"file_key": "test-document.rtf"},
        headers={"Authorization": "Bearer test-token"},
    )


def test_retrieve_coroners_letter_returns_response_bytes():
    adapter = _make_adapter()
    expected_bytes = b"rtf file content here"

    mock_response = MagicMock(status_code=200, content=expected_bytes)
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.post", return_value=_mock_token_response()), patch(
        "httpx.get", return_value=mock_response
    ):
        result = adapter.retrieve_coroners_letter("letter.rtf")

    assert result == expected_bytes


def test_retrieve_coroners_letter_raises_on_non_200_response():
    adapter = _make_adapter()

    mock_response = MagicMock(status_code=404)
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "404", request=MagicMock(), response=MagicMock()
    )

    with patch("httpx.post", return_value=_mock_token_response()), patch(
        "httpx.get", return_value=mock_response
    ):
        try:
            adapter.retrieve_coroners_letter("missing-file.rtf")
            assert False, "Expected HTTPStatusError to be raised"
        except httpx.HTTPStatusError:
            pass
