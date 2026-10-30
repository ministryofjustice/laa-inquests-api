import logging
from unittest.mock import ANY, MagicMock

import pytest
from sqlmodel import select

from app import api
from app.adapters.audit_repository_adapter import AuditRepositoryAdapter
from app.auth.rbac import Role
from app.models.audit.enums import ReportType
from app.models.audit.index import ReportAudit
from app.routers.dependencies import auditer_permission_checker
from app.routers.reports import (
    get_generate_application_backlog_report_use_case,
    get_generate_claim_backlog_report_use_case,
    get_generate_decisions_report_use_case,
    get_generate_ogd_costs_report_use_case,
    get_generate_payment_extract_report_use_case,
)
from app.use_cases.exceptions import AuditError

# Report downloads are audited before permission is enforced:
#
# | Permission | Audit                          | Outcome                |
# | ---------- | ------------------------------ | ---------------------- |
# | Granted    | Succeeds                       | 200, report downloaded |
# | Denied     | Succeeds                       | 403, audit persisted   |
# | Granted    | Fails (setup, write or commit) | 500, no report         |
# | Denied     | Fails (setup, write or commit) | 403, no report         |

REPORT_ENDPOINTS = [
    (
        "/reports/applications/backlog",
        Role.APPLICATION_WORKFLOW_REPORTING,
        ReportType.APPLICATIONS_BACKLOG,
        get_generate_application_backlog_report_use_case,
        None,
    ),
    (
        "/reports/claims/backlog",
        Role.CLAIM_WORKFLOW_REPORTING,
        ReportType.CLAIMS_BACKLOG,
        get_generate_claim_backlog_report_use_case,
        None,
    ),
    (
        "/reports/payment-extract",
        Role.FINANCE,
        ReportType.PAYMENT_EXTRACT,
        get_generate_payment_extract_report_use_case,
        {"from": "2024-01-01", "to": "2024-01-31"},
    ),
    (
        "/reports/decisions",
        Role.APPLICATION_WORKFLOW_REPORTING,
        ReportType.DECISIONS,
        get_generate_decisions_report_use_case,
        {"from": "2024-01-01", "to": "2024-01-31"},
    ),
    (
        "/reports/ogd-costs",
        Role.ASSURANCE,
        ReportType.OGD_COSTS,
        get_generate_ogd_costs_report_use_case,
        {"from": "2024-01-01", "to": "2024-01-31"},
    ),
]

# Payment extract streams chunks; every other report returns the whole body.
STREAMING_ENDPOINTS = {"/reports/payment-extract"}

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


def _assert_report_downloaded(response, report_use_case):
    report_use_case.execute.assert_called_once()
    assert response.content == b"report data"
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]


def _assert_report_blocked(response, report_use_case, expected_status):
    report_use_case.execute.assert_not_called()
    assert "content-disposition" not in response.headers
    if expected_status == 403:
        assert response.json() == {"detail": "Forbidden: Missing required permission"}


def _assert_audit_persisted(session, audit_type, parameters):
    audit_entries = session.exec(select(ReportAudit)).all()
    assert len(audit_entries) == 1
    assert audit_entries[0].report_type == audit_type
    assert audit_entries[0].user_email_address == "test@example.com"
    assert audit_entries[0].parameters == parameters


@pytest.mark.parametrize(
    "endpoint,role,audit_type,report_dependency,parameters", REPORT_ENDPOINTS
)
@pytest.mark.parametrize("has_permission,audit_failure,expected_status", AUDIT_OUTCOMES)
def test_report_download_outcome_depends_on_permission_and_audit(
    client,
    session,
    monkeypatch,
    endpoint,
    role,
    audit_type,
    report_dependency,
    parameters,
    has_permission,
    audit_failure,
    expected_status,
):
    session.expire_on_commit = False
    audit_repository = MagicMock(wraps=AuditRepositoryAdapter(session=session))
    audit_factory = MagicMock(return_value=audit_repository)
    if audit_failure == "setup":
        audit_factory.side_effect = RuntimeError("Audit setup failed")
    elif audit_failure == "write":
        audit_repository.audit_event.side_effect = AuditError("Audit write failed")
    elif audit_failure == "commit":
        audit_repository.commit.side_effect = AuditError("Audit commit failed")

    report_use_case = MagicMock()
    report_use_case.execute.return_value = (
        iter([b"report data"]) if endpoint in STREAMING_ENDPOINTS else b"report data"
    )

    monkeypatch.setattr(
        auditer_permission_checker, "AuditRepositoryAdapter", audit_factory
    )
    api.dependency_overrides[report_dependency] = lambda: report_use_case
    user_role = role if has_permission else Role.PROVIDER_APPLICATION_USER

    response = client.get(
        endpoint,
        params=parameters,
        headers={"Authorization": f"Bearer {user_role.value}"},
    )

    assert response.status_code == expected_status
    audit_factory.assert_called_once()
    if audit_failure != "setup":
        audit_repository.audit_event.assert_called_once_with(
            ReportAudit(
                id=ANY,
                timestamp=ANY,
                user_email_address="test@example.com",
                report_type=audit_type,
                parameters=parameters,
            )
        )

    if expected_status == 200:
        _assert_report_downloaded(response, report_use_case)
    else:
        _assert_report_blocked(response, report_use_case, expected_status)

    if audit_failure is None:
        _assert_audit_persisted(session, audit_type, parameters)
    else:
        assert session.exec(select(ReportAudit)).all() == []


@pytest.mark.parametrize(
    "endpoint,role,audit_type,report_dependency,parameters", REPORT_ENDPOINTS
)
def test_denied_report_download_emits_error_log_without_generating_report(
    client,
    session,
    caplog,
    endpoint,
    role,
    audit_type,
    report_dependency,
    parameters,
):
    report_use_case = MagicMock()
    api.dependency_overrides[report_dependency] = lambda: report_use_case
    caplog.set_level(logging.ERROR)

    response = client.get(
        endpoint,
        params=parameters,
        headers={"Authorization": f"Bearer {Role.APPLICATIONS_CASEWORKER.value}"},
    )

    assert response.status_code == 403
    report_use_case.execute.assert_not_called()
    _assert_audit_persisted(session, audit_type, parameters)
    denial_logs = [
        record
        for record in caplog.records
        if getattr(record, "extra", {}).get("event") == "report_access_denied"
    ]
    assert len(denial_logs) == 1
    assert denial_logs[0].levelno == logging.ERROR
    assert denial_logs[0].extra["route"] == endpoint
    assert denial_logs[0].extra["method"] == "GET"
    assert denial_logs[0].extra["status_code"] == 403
