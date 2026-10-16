import pytest
from fastapi import HTTPException, Request

from app.auth.rbac import Permission, PermissionChecker
from app.routers.dependencies.audited_permission_checker import AuditFailureHandler
from app.use_cases.exceptions import AuditError


def test_audit_failure_returns_403_when_user_lacks_permission(caplog):
    handler = AuditFailureHandler(
        PermissionChecker(Permission.REPORTS_CLAIM_WORKFLOW_READ)
    )
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/reports/claims/backlog",
            "headers": [],
        }
    )

    with (
        pytest.raises(HTTPException) as exc_info,
        handler.handle_failure(permissions=set(), request=request),
    ):
        raise AuditError("Audit write failed")

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Forbidden: Missing required permission"
    assert isinstance(exc_info.value.__cause__, AuditError)
    failure_log = next(
        record.extra
        for record in caplog.records
        if getattr(record, "extra", {}).get("event") == "report_audit_failed"
    )
    assert failure_log["status_code"] == 403
    assert failure_log["error_type"] == "AuditError"


def test_audit_failure_returns_500_when_user_has_permission(caplog):
    handler = AuditFailureHandler(
        PermissionChecker(Permission.REPORTS_CLAIM_WORKFLOW_READ)
    )
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/reports/claims/backlog",
            "headers": [],
        }
    )

    with (
        pytest.raises(HTTPException) as exc_info,
        handler.handle_failure(
            permissions={Permission.REPORTS_CLAIM_WORKFLOW_READ}, request=request
        ),
    ):
        raise AuditError("Audit write failed")

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Failed to audit report request"
    assert isinstance(exc_info.value.__cause__, AuditError)
    failure_log = next(
        record.extra
        for record in caplog.records
        if getattr(record, "extra", {}).get("event") == "report_audit_failed"
    )
    assert failure_log["status_code"] == 500
