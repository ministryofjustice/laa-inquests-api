import pytest
from fastapi import HTTPException
from fastapi.dependencies.utils import get_dependant

from app.auth.rbac import (
    ROLE_PERMISSIONS_MAP,
    Permission,
    Role,
    get_current_user_permissions,
    require_permission,
)
from app.ports.entra_auth_port import AuthenticatedUser
from app.routers.dependencies.entra_auth import verify_entra_token


def _user(app_roles: set[str]) -> AuthenticatedUser:
    return AuthenticatedUser(
        firm_code="0A123B",
        scopes=frozenset(),
        name="Test Name",
        app_roles=frozenset(app_roles),
    )


def test_get_current_user_permissions_resolves_provider_application_user_role():
    permissions = get_current_user_permissions(
        _user({Role.PROVIDER_APPLICATION_USER.value})
    )

    assert permissions == ROLE_PERMISSIONS_MAP[Role.PROVIDER_APPLICATION_USER.value]


def test_get_current_user_permissions_resolves_provider_claims_user_role():
    permissions = get_current_user_permissions(_user({Role.PROVIDER_CLAIMS_USER.value}))

    assert permissions == ROLE_PERMISSIONS_MAP[Role.PROVIDER_CLAIMS_USER.value]


def test_get_current_user_permissions_unions_multiple_roles():
    permissions = get_current_user_permissions(
        _user(
            {
                Role.PROVIDER_APPLICATION_USER.value,
                Role.PROVIDER_CLAIMS_USER.value,
            }
        )
    )

    assert permissions == ROLE_PERMISSIONS_MAP[
        Role.PROVIDER_APPLICATION_USER.value
    ].union(ROLE_PERMISSIONS_MAP[Role.PROVIDER_CLAIMS_USER.value])


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


def test_require_permission_depends_on_get_current_user_permissions():
    permission_checker = require_permission(Permission.CLAIM_CREATE)

    dependant = get_dependant(path="/test", call=permission_checker)

    # Confirms the DI wiring, not a runtime call - FastAPI resolves this
    # dependency itself; calling permission_checker directly bypasses it.
    assert [sub.call for sub in dependant.dependencies] == [
        get_current_user_permissions
    ]


def test_get_current_user_permissions_depends_on_verify_entra_token():
    dependant = get_dependant(path="/test", call=get_current_user_permissions)
    assert [sub.call for sub in dependant.dependencies] == [verify_entra_token]


def test_external_provider_application_user_permission_set():
    assert ROLE_PERMISSIONS_MAP[Role.PROVIDER_APPLICATION_USER.value] == {
        Permission.APPLICATION_CREATE,
        Permission.CORONERS_LETTER_UPLOAD,
        Permission.CORONERS_LETTER_DELETE,
        Permission.PROVIDER_OFFICES_READ,
    }


def test_external_provider_claims_user_permission_set():
    assert ROLE_PERMISSIONS_MAP[Role.PROVIDER_CLAIMS_USER.value] == {
        Permission.APPLICATION_SEARCH,
        Permission.CLAIM_CREATE,
        Permission.CLAIM_DELETE,
        Permission.CLAIM_EVIDENCE_UPLOAD,
        Permission.PROVIDER_OFFICES_READ,
    }


def test_internal_applications_caseworker_permission_set():
    assert ROLE_PERMISSIONS_MAP[Role.APPLICATIONS_CASEWORKER.value] == {
        Permission.APPLICATION_READ,
        Permission.APPLICATION_MANAGE,
        Permission.CERTIFICATE_READ,
        Permission.HISTORY_READ,
        Permission.CASE_NOTE_CREATE,
    }


def test_internal_claims_caseworker_permission_set():
    assert ROLE_PERMISSIONS_MAP[Role.CLAIMS_CASEWORKER.value] == {
        Permission.APPLICATION_READ,
        Permission.CLAIM_READ,
        Permission.CLAIM_MANAGE,
        Permission.CERTIFICATE_READ,
        Permission.HISTORY_READ,
        Permission.CASE_NOTE_CREATE,
    }


def test_internal_customer_service_agent_permission_set():
    assert ROLE_PERMISSIONS_MAP[Role.CUSTOMER_SERVICE_AGENT.value] == {
        Permission.APPLICATION_READ,
        Permission.CLAIM_READ,
        Permission.CERTIFICATE_READ,
        Permission.CASE_NOTE_CREATE,
        Permission.HISTORY_READ,
    }


def test_internal_assurance_permission_set():
    assert ROLE_PERMISSIONS_MAP[Role.ASSURANCE.value] == {
        Permission.APPLICATION_READ,
        Permission.CLAIM_READ,
        Permission.CERTIFICATE_READ,
        Permission.CASE_NOTE_CREATE,
        Permission.HISTORY_READ,
        Permission.REPORTS_MI_READ,
        Permission.REPORTS_PAYMENT_READ,
    }


def test_internal_application_workflow_reporting_permission_set():
    assert ROLE_PERMISSIONS_MAP[Role.APPLICATION_WORKFLOW_REPORTING.value] == {
        Permission.REPORTS_APPLICATION_WORKFLOW_READ,
    }


def test_internal_claim_workflow_reporting_permission_set():
    assert ROLE_PERMISSIONS_MAP[Role.CLAIM_WORKFLOW_REPORTING.value] == {
        Permission.REPORTS_CLAIM_WORKFLOW_READ,
    }


def test_internal_policy_permission_set():
    assert ROLE_PERMISSIONS_MAP[Role.POLICY.value] == {
        Permission.REPORTS_MI_READ,
    }


def test_internal_finance_permission_set():
    assert ROLE_PERMISSIONS_MAP[Role.FINANCE.value] == {
        Permission.REPORTS_MI_READ,
        Permission.REPORTS_PAYMENT_READ,
    }
