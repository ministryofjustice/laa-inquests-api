import pytest
from fastapi import HTTPException

from app.domain.caller import CaseworkerCaller, ProviderCaller
from app.ports.entra_auth_port import AuthenticatedUser
from app.routers.dependencies import get_caller


def _user(scopes, office_codes=frozenset({"0U651L"})):
    return AuthenticatedUser(
        firm_code="0A123B",
        scopes=frozenset(scopes),
        name="Test Name",
        office_codes=office_codes,
    )


def test_returns_provider_caller_for_provider_token():
    caller = get_caller(_user({"User.Provider"}))

    assert caller == ProviderCaller(office_codes=frozenset({"0U651L"}))


def test_returns_caseworker_caller_for_caseworker_token():
    assert get_caller(_user({"User.Caseworker"})) == CaseworkerCaller()


def test_raises_403_for_token_with_neither_scope():
    with pytest.raises(HTTPException) as exc_info:
        get_caller(_user({"Some.Other"}))

    assert exc_info.value.status_code == 403


def test_raises_403_for_provider_token_missing_office_codes():
    with pytest.raises(HTTPException) as exc_info:
        get_caller(_user({"User.Provider"}, office_codes=frozenset()))

    assert exc_info.value.status_code == 403
