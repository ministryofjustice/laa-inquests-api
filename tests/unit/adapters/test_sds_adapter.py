import uuid
from unittest.mock import MagicMock, patch

from httpx import HTTPStatusError
import pytest

from app.use_cases.exceptions import (
    InvalidCoronersLetterDocumentIdError,
    SDSLetterRetrievalError,
)


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
    mock.status_code = 200
    mock.json.return_value = {"access_token": token, "expires_in": 3599}
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


def _mock_retrieve_metadata_response(
    status_code: int = 200, file_url: str = "https://signed.example.com/letter.pdf"
) -> MagicMock:
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = {"fileURL": file_url}
    return mock


def test_get_token_returns_access_token():
    adapter = _make_adapter()

    with patch("httpx.post", return_value=_mock_token_response("my-token")):
        result = adapter._get_token()

    assert result == "my-token"


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


def test_get_token_raises_http_exception_on_unsuccessful_status_code():
    adapter = _make_adapter()
    with patch("httpx.post", return_value=_mock_save_failure_response()):
        with pytest.raises(HTTPStatusError):
            adapter._get_token()


def test_get_token_caches_token_and_does_not_call_post_again():
    adapter = _make_adapter()
    with patch(
        "httpx.post", return_value=_mock_token_response("cached-token")
    ) as mock_post:
        first = adapter._get_token()
        second = adapter._get_token()

    assert mock_post.call_count == 1
    assert first == "cached-token"
    assert second == "cached-token"


def test_get_token_refreshes_token_when_expired():
    adapter = _make_adapter()
    with patch("httpx.post", return_value=_mock_token_response()) as mock_post:
        # First _get_token: self._token is None so cache check is short-circuited;
        # time.time() called once to set expiry → 1000.0, expiry = 4539.0.
        # Second _get_token: time.time() called for check → 5000.0 > 4539.0 → refresh;
        # time.time() called again to set new expiry → 5000.0.

        first_time = 1000.0  # time on first call expiry set
        second_time = 5000.0  # time on second call expiry check. So is above first one
        third_time = 5000.0  # time on third call expiry set

        with patch("time.time", side_effect=[first_time, second_time, third_time]):
            adapter._get_token()
            adapter._get_token()

    assert mock_post.call_count == 2


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

    # Second save reuses the cached token, so only 3 post calls: token, save, save.
    with patch(
        "httpx.post",
        side_effect=[
            _mock_token_response(),
            _mock_save_response(),
            _mock_save_response(),
        ],
    ) as mock_post:
        adapter.save_coroners_letter(b"content", "letter.pdf")
        adapter.save_coroners_letter(b"content", "letter.pdf")

    name_1 = mock_post.call_args_list[1].kwargs["files"]["file"][0]
    name_2 = mock_post.call_args_list[2].kwargs["files"]["file"][0]
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

    mock_get_file_response = _mock_retrieve_metadata_response()

    mock_stream = MagicMock()
    mock_stream.__enter__ = MagicMock(
        return_value=MagicMock(iter_bytes=lambda: iter([]))
    )
    mock_stream.__exit__ = MagicMock(return_value=False)

    with (
        patch("httpx.post", return_value=_mock_token_response()),
        patch("httpx.get", return_value=mock_get_file_response),
        patch("httpx.stream", return_value=mock_stream) as mock_stream,
    ):
        list(adapter.retrieve_coroners_letter("letter.pdf"))

    mock_stream.assert_called_once_with("GET", "https://signed.example.com/letter.pdf")


def test_retrieve_coroners_letter_returns_response_bytes():
    adapter = _make_adapter()

    mock_get_file_response = _mock_retrieve_metadata_response()

    mock_stream_response = MagicMock()
    mock_stream_response.iter_bytes.return_value = iter([b"chunk1", b"chunk2"])

    mock_stream = MagicMock()
    mock_stream.__enter__ = MagicMock(return_value=mock_stream_response)
    mock_stream.__exit__ = MagicMock(return_value=False)

    with (
        patch("httpx.post", return_value=_mock_token_response()),
        patch("httpx.get", return_value=mock_get_file_response),
        patch("httpx.stream", return_value=mock_stream),
    ):
        result = b"".join(adapter.retrieve_coroners_letter("letter.pdf"))

    assert result == b"chunk1chunk2"


def test_retrieve_coroners_letter_id_with_None_filename_raises_InvalidCoronersLetterDocumentIdError():
    adapter = _make_adapter()

    with (
        patch("httpx.post", return_value=_mock_token_response()),
        pytest.raises(
            InvalidCoronersLetterDocumentIdError,
            match="file_name must be a non-empty string",
        ),
    ):
        list(adapter.retrieve_coroners_letter(None))


def test_retrieve_coroners_letter_id_with_blank_filename_raises_InvalidCoronersLetterDocumentIdError():
    adapter = _make_adapter()

    with (
        patch("httpx.post", return_value=_mock_token_response()),
        pytest.raises(
            InvalidCoronersLetterDocumentIdError,
            match="file_name must be a non-empty string",
        ),
    ):
        list(adapter.retrieve_coroners_letter(""))


def test_retrieve_coroners_letter_raises_not_found_for_sds_404(caplog):
    adapter = _make_adapter()

    with (
        patch("httpx.post", return_value=_mock_token_response()),
        patch("httpx.get", return_value=_mock_retrieve_metadata_response(404)),
        pytest.raises(
            SDSLetterRetrievalError,
            match="SDS returned 404 while retrieving coroner's letter for file key missing.pdf",
        ),
    ):
        list(adapter.retrieve_coroners_letter("missing.pdf"))

    assert "SDS returned 404" in caplog.text


def test_retrieve_coroners_letter_raises_invalid_id_for_sds_400(caplog):
    adapter = _make_adapter()

    with (
        patch("httpx.post", return_value=_mock_token_response()),
        patch("httpx.get", return_value=_mock_retrieve_metadata_response(400)),
        pytest.raises(
            SDSLetterRetrievalError,
            match="SDS returned 400 while retrieving coroner's letter for file key bad-id",
        ),
    ):
        list(adapter.retrieve_coroners_letter("bad-id"))

    assert "SDS returned 400" in caplog.text


def test_retrieve_coroners_letter_logs_and_raises_for_other_sds_4xx(caplog):
    adapter = _make_adapter()

    with (
        patch("httpx.post", return_value=_mock_token_response()),
        patch("httpx.get", return_value=_mock_retrieve_metadata_response(403)),
        pytest.raises(
            SDSLetterRetrievalError,
            match="SDS returned 403 while retrieving coroner's letter for file key forbidden.pdf",
        ),
    ):
        list(adapter.retrieve_coroners_letter("forbidden.pdf"))

    assert "SDS returned 403" in caplog.text


def test_retrieve_coroners_letter_raises_error_when_stream_fails():
    adapter = _make_adapter()

    with (
        patch("httpx.post", return_value=_mock_token_response()),
        patch("httpx.get", return_value=_mock_retrieve_metadata_response()),
        patch("httpx.stream", side_effect=RuntimeError("stream failed")),
        pytest.raises(
            SDSLetterRetrievalError,
            match="Failed to stream coroners letter: \n stream failed",
        ),
    ):
        list(adapter.retrieve_coroners_letter("letter.pdf"))


def test_retrieve_coroners_letter_raises_error_when_file_url_missing():
    adapter = _make_adapter()

    bad_metadata = MagicMock()
    bad_metadata.status_code = 200
    bad_metadata.json.return_value = {}

    with (
        patch("httpx.post", return_value=_mock_token_response()),
        patch("httpx.get", return_value=bad_metadata),
        pytest.raises(
            SDSLetterRetrievalError, match="Failed to retrieve coroners letter"
        ),
    ):
        list(adapter.retrieve_coroners_letter("letter.pdf"))
