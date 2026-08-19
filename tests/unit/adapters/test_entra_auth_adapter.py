"""Unit tests for EntraAuthAdapter."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from jwt.exceptions import (
    ExpiredSignatureError,
    InvalidAudienceError,
    InvalidSignatureError,
    PyJWKClientError,
)

from app.adapters.entra_auth_adapter import EntraAuthAdapter


@pytest.fixture
def adapter():
    with patch("app.adapters.entra_auth_adapter.PyJWKClient"):
        yield EntraAuthAdapter(tenant_id="test-tenant", client_id="test-client-id")


def test_verify_token_returns_user_with_firm_code_and_name_when_token_is_valid(adapter):
    mock_signing_key = MagicMock()
    adapter._jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key

    with patch(
        "app.adapters.entra_auth_adapter.jwt.decode",
        return_value={
            "sub": "user",
            "scp": "User.Provider",
            "FIRM_CODE": "0A123B",
            "name": "Test Name",
            "oid": "some-entra-object-id",
        },
    ):
        user = adapter.verify_token("valid.jwt.token")

    assert user.firm_code == "0A123B"
    assert user.name == "Test Name"
    assert user.entra_object_id == "some-entra-object-id"
    assert "User.Provider" in user.scopes


def test_verify_token_returns_none_firm_code_when_claim_absent(adapter):
    mock_signing_key = MagicMock()
    adapter._jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key

    with patch(
        "app.adapters.entra_auth_adapter.jwt.decode",
        return_value={"sub": "user", "scp": "User.Provider"},
    ):
        user = adapter.verify_token("valid.jwt.token")

    assert user.firm_code is None


def test_verify_token_raises_403_when_required_scope_missing(adapter):
    mock_signing_key = MagicMock()
    adapter._jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key

    with (
        patch(
            "app.adapters.entra_auth_adapter.jwt.decode",
            return_value={"sub": "user", "scp": "User.Other"},
        ),
        pytest.raises(HTTPException) as exc_info,
    ):
        adapter.verify_token("valid.jwt.token", {"User.Provider"})

    assert exc_info.value.status_code == 403


def test_verify_token_allows_required_scope_via_roles_claim(adapter):
    mock_signing_key = MagicMock()
    adapter._jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key

    with patch(
        "app.adapters.entra_auth_adapter.jwt.decode",
        return_value={"sub": "service", "roles": ["User.Caseworker"]},
    ):
        adapter.verify_token("valid.jwt.token", {"User.Caseworker"})


@pytest.mark.parametrize(
    "side_effect",
    [
        ExpiredSignatureError("token expired"),
        InvalidSignatureError("bad signature"),
        InvalidAudienceError("wrong audience"),
        PyJWKClientError("kid not found"),
    ],
    ids=["expired", "invalid_signature", "wrong_audience", "kid_not_found"],
)
def test_verify_token_raises_401_for_invalid_token(adapter, side_effect):
    adapter._jwks_client.get_signing_key_from_jwt.side_effect = side_effect

    with pytest.raises(HTTPException) as exc_info:
        adapter.verify_token("bad.jwt.token")

    assert exc_info.value.status_code == 401


class TestFormatName:
    def test_returns_none_when_name_is_none(self, adapter):
        assert adapter._format_name(None) == ""

    def test_returns_plain_name_unchanged(self, adapter):
        assert adapter._format_name("John Doe") == "John Doe"

    def test_strips_trailing_bracketed_tag(self, adapter):
        assert adapter._format_name("John Doe [LAA]") == "John Doe"

    def test_strips_leading_bracketed_tags_with_dash_separator(self, adapter):
        assert adapter._format_name("[MOJUSER] - [INTSILAS] John Doe") == "John Doe"

    def test_strips_leading_and_trailing_bracketed_tags(self, adapter):
        assert (
            adapter._format_name("[MOJUSER] - [INTSILAS] John Doe [Test]") == "John Doe"
        )

    def test_preserves_hyphenated_surnames(self, adapter):
        assert (
            adapter._format_name("[MOJUSER] - [INTSILAS] Smith-Jones") == "Smith-Jones"
        )

    def test_returns_none_for_name_with_only_tags(self, adapter):
        assert adapter._format_name("[TAG1] - [TAG2]") == ""

    def test_returns_none_for_empty_string(self, adapter):
        assert adapter._format_name("") == ""
