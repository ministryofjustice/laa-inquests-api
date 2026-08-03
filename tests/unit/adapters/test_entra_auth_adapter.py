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


def test_verify_token_returns_user_with_firm_code_when_token_is_valid(adapter):
    mock_signing_key = MagicMock()
    adapter._jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key

    with patch(
        "app.adapters.entra_auth_adapter.jwt.decode",
        return_value={
            "sub": "user",
            "scp": "User.Provider",
            "FIRM_CODE": "0A123B",
        },
    ):
        user = adapter.verify_token("valid.jwt.token")

    assert user.firm_code == "0A123B"
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
