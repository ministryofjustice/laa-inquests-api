from unittest.mock import MagicMock

import pytest
from sqlmodel import select

from app.adapters.audit_repository_adapter import AuditRepositoryAdapter
from app.auth.rbac import Role
from app.models.audit.index import ViewApplicationAudit
from app.routers.dependencies import audited_permission_checker
from app.use_cases.exceptions import AuditError

# Get application is audited before permission is enforced:
#
# | Permission | Audit                          | Outcome                           |
# | ---------- | ------------------------------ | --------------------------------- |
# | Granted    | Succeeds                       | 200, ApplicationResponse returned |
# | Denied     | Succeeds                       | 403, audit persisted              |
# | Granted    | Fails (setup, write or commit) | 500, no application response      |
# | Denied     | Fails (setup, write or commit) | 403, no application response      |

LAA_REFERENCE = "INQ-123-456"

# (has_permission, audit_failure, expected_status)
AUDIT_OUTCOMES = [
    pytest.param(True, None, 200, id="permitted-audit_succeeds"),
    pytest.param(False, None, 403, id="denied-audit_succeeds"),
    pytest.param(True, "setup", 500, id="permitted-setup_fails"),
    pytest.param(False, "setup", 403, id="denied-setup_fails"),
    pytest.param(True, "write", 500, id="permitted-write_fails"),
    pytest.param(False, "write", 403, id="denied-write_fails"),
    pytest.param(True, "commit", 500, id="permitted-commit_fails"),
    pytest.param(False, "commit", 403, id="denied-commit_fails"),
]


def _assert_application_returned(response):
    assert response.json()["laaReference"] == LAA_REFERENCE


def _assert_application_blocked(response, expected_status):
    assert "laaReference" not in response.json()
    if expected_status == 403:
        assert response.json() == {"detail": "Forbidden: Missing required permission"}


def _assert_audit_persisted(session):
    audit_entries = session.exec(select(ViewApplicationAudit)).all()
    assert len(audit_entries) == 1
    assert audit_entries[0].user_email_address == "test@example.com"
    assert audit_entries[0].laa_reference == LAA_REFERENCE


@pytest.mark.parametrize("has_permission,audit_failure,expected_status", AUDIT_OUTCOMES)
def test_get_application_outcome_depends_on_permission_and_audit(
    client,
    session,
    monkeypatch,
    has_permission,
    audit_failure,
    expected_status,
):
    audit_repository = MagicMock(wraps=AuditRepositoryAdapter(session=session))
    audit_factory = MagicMock(return_value=audit_repository)
    if audit_failure == "setup":
        audit_factory.side_effect = RuntimeError("Audit setup failed")
    elif audit_failure == "write":
        audit_repository.audit_event.side_effect = AuditError("Audit write failed")
    elif audit_failure == "commit":
        audit_repository.commit.side_effect = AuditError("Audit commit failed")

    monkeypatch.setattr(
        audited_permission_checker, "AuditRepositoryAdapter", audit_factory
    )
    user_role = (
        Role.APPLICATIONS_CASEWORKER
        if has_permission
        else Role.PROVIDER_APPLICATION_USER
    )

    response = client.get(
        f"/applications/{LAA_REFERENCE}",
        headers={"Authorization": f"Bearer {user_role.value}"},
    )

    assert response.status_code == expected_status
    if expected_status == 200:
        _assert_application_returned(response)
    else:
        _assert_application_blocked(response, expected_status)

    if audit_failure is None:
        _assert_audit_persisted(session)
    else:
        assert session.exec(select(ViewApplicationAudit)).all() == []
