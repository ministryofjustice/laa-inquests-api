from unittest.mock import MagicMock

import pytest
from sqlmodel import select

from app import api
from app.adapters.audit_repository_adapter import AuditRepositoryAdapter
from app.auth.rbac import Role
from app.models.audit.enums import ReportType
from app.models.audit.index import ReportAudit
from app.routers.dependencies.report_audit_writer import report_audit_use_case_factory
from app.routers.reports import (
    get_generate_application_backlog_report_use_case,
    get_generate_claim_backlog_report_use_case,
    get_generate_payment_extract_report_use_case,
)
from app.use_cases.report_audit import ReportAuditUseCase
from app.use_cases.exceptions import AuditError

# This file contains end-to-end tests for audit and permissions truth table scenarios.
# Audit log X, Permission Y => 500
# Audit log X, Permission X => 403
# Audit log Y, Permission Y => 200
# Audit log Y, Permission X => 403


def test_200_audit_log_y_permission_y_returns_200(client):
    response = client.get(
        "/reports/claims/backlog",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Role.CLAIM_WORKFLOW_REPORTING.value}",
        },
    )

    assert response.status_code == 200


def test_403_audit_log_y_permission_x_returns_403(client):
    response = client.get(
        "/reports/claims/backlog",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}",
        },
    )

    assert response.status_code == 403


def _raise_audit_log_exception():
    raise RuntimeError("Audit log X")


def test_403_audit_log_x_permission_x_returns_403(client):
    api.dependency_overrides[report_audit_use_case_factory] = lambda: (
        _raise_audit_log_exception
    )
    response = client.get(
        "/reports/claims/backlog",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}",
        },
    )

    assert response.status_code == 403


@pytest.mark.parametrize(
    "endpoint,role,audit_type,report_dependency,parameters",
    [
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
    ],
)
@pytest.mark.parametrize("has_permission", [True, False])
@pytest.mark.parametrize("audit_failure", [None, "setup", "write", "commit"])
def test_report_download_requires_permission_and_successful_audit(
    client,
    session,
    endpoint,
    role,
    audit_type,
    report_dependency,
    parameters,
    has_permission,
    audit_failure,
):
    audit_repository = MagicMock(wraps=AuditRepositoryAdapter(session=session))
    audit_factory = MagicMock(return_value=audit_repository)
    if audit_failure == "setup":
        audit_factory.side_effect = RuntimeError("Audit setup failed")
    elif audit_failure == "write":
        audit_repository.audit_report.side_effect = AuditError("Audit write failed")
    elif audit_failure == "commit":
        audit_repository.commit.side_effect = AuditError("Audit commit failed")

    report_use_case = MagicMock()
    report_use_case.execute.return_value = (
        iter([b"report data"]) if parameters else b"report data"
    )

    def create_audit_use_case():
        return ReportAuditUseCase(audit_port=audit_factory())

    api.dependency_overrides[report_audit_use_case_factory] = lambda: (
        create_audit_use_case
    )
    api.dependency_overrides[report_dependency] = lambda: report_use_case
    user_role = role if has_permission else Role.PROVIDER_APPLICATION_USER

    response = client.get(
        endpoint,
        params=parameters,
        headers={"Authorization": f"Bearer {user_role.value}"},
    )

    expected_status = 403 if not has_permission else 500 if audit_failure else 200
    assert response.status_code == expected_status
    audit_factory.assert_called_once()
    if audit_failure != "setup":
        audit_repository.audit_report.assert_called_once_with(
            user_email_address="test@example.com",
            report_type=audit_type,
            parameters=parameters,
        )

    if expected_status == 200:
        report_use_case.execute.assert_called_once()
        assert response.content == b"report data"
        assert response.headers["content-type"].startswith("text/csv")
        assert "attachment" in response.headers["content-disposition"]
    else:
        report_use_case.execute.assert_not_called()
        assert "content-disposition" not in response.headers
        if expected_status == 403:
            assert response.json() == {
                "detail": "Forbidden: Missing required permission"
            }

    audit_entries = session.exec(select(ReportAudit)).all()
    if audit_failure is None:
        assert len(audit_entries) == 1
        assert audit_entries[0].report_type == audit_type
        assert audit_entries[0].user_email_address == "test@example.com"
        assert audit_entries[0].parameters == parameters
    else:
        assert audit_entries == []
