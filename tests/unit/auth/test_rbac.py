import pytest
from fastapi import HTTPException

from app.auth.rbac import (
    Permission,
    get_current_user_permissions,
    require_permission,
)
from app.ports.entra_auth_port import AuthenticatedUser


def _user(scopes: set[str]) -> AuthenticatedUser:
    return AuthenticatedUser(
        firm_code="0A123B",
        scopes=frozenset(scopes),
        name="Test Name",
    )


def test_get_current_user_permissions_resolves_known_role():
    permissions = get_current_user_permissions(_user({"Provider.ApplicationUser"}))

    assert permissions == {
        Permission.APPLICATION_READ,
        Permission.APPLICATION_CREATE,
        Permission.CORONERS_LETTER_UPLOAD,
    }


def test_get_current_user_permissions_unions_multiple_roles():
    permissions = get_current_user_permissions(
        _user({"Provider.ApplicationUser", "Provider.ClaimsUser"})
    )

    assert permissions == {
        Permission.APPLICATION_READ,
        Permission.APPLICATION_CREATE,
        Permission.CORONERS_LETTER_UPLOAD,
        Permission.CLAIM_READ,
        Permission.CLAIM_CREATE,
    }


def test_get_current_user_permissions_ignores_unmapped_role():
    permissions = get_current_user_permissions(_user({"Some.UnknownRole"}))

    assert permissions == set()


def test_get_current_user_permissions_returns_empty_set_for_no_roles():
    permissions = get_current_user_permissions(_user(set()))

    assert permissions == set()


def test_require_permission_allows_access_when_permission_present():
    permission_checker = require_permission(Permission.CLAIM_CREATE)

    assert permission_checker(permissions={Permission.CLAIM_CREATE}) is None


def test_require_permission_raises_403_when_permission_missing():
    permission_checker = require_permission(Permission.CLAIM_CREATE)

    with pytest.raises(HTTPException) as exc_info:
        permission_checker(permissions={Permission.CLAIM_READ})

    assert exc_info.value.status_code == 403
    assert "claim:create" in exc_info.value.detail
