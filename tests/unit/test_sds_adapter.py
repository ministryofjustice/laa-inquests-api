import re
from unittest.mock import MagicMock, patch


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

    # name should be <stem>_<uuid>.pdf
    assert re.match(
        r"^coroners_letter_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.pdf$",
        stored_name,
    )


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

    assert result.status == 201
    assert result.id.startswith("letter_")
    assert result.id.endswith(".pdf")
    assert result.file_name == result.id
