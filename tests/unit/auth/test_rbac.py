import pytest
from fastapi import HTTPException

from app.auth.rbac import (
    Permission,
    get_current_user_permissions,
    require_permission,
    ROLE_PERMISSIONS_MAP,
)
from app.ports.entra_auth_port import AuthenticatedUser


def _user(app_roles: set[str]) -> AuthenticatedUser:
    return AuthenticatedUser(
        firm_code="0A123B",
        scopes=frozenset(),
        name="Test Name",
        app_roles=frozenset(app_roles),
    )


def test_get_current_user_permissions_resolves_known_role():
    permissions = get_current_user_permissions(
        _user({"Inquests - Provider Application User"})
    )

    assert permissions == ROLE_PERMISSIONS_MAP["Inquests - Provider Application User"]


def test_get_current_user_permissions_unions_multiple_roles():
    permissions = get_current_user_permissions(
        _user(
            {
                "Inquests - Provider Application User",
                "Inquests - Provider Claims User",
            }
        )
    )

    assert permissions == ROLE_PERMISSIONS_MAP[
        "Inquests - Provider Application User"
    ].union(ROLE_PERMISSIONS_MAP["Inquests - Provider Claims User"])


def test_get_current_user_permissions_ignores_unmapped_role():
    permissions = get_current_user_permissions(_user({"Some Unknown Role"}))

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
