import asyncio
import logging
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials

from app.auth.rbac import Permission, PermissionChecker
from app.routers.dependencies import auditer_permission_checker
from app.routers.dependencies.auditer_permission_checker import (
    AuditFailureHandler,
    audit_and_require_permission,
)
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


def test_denied_mi_report_request_emits_error_log_after_successful_audit(
    monkeypatch, caplog
):
    audit_use_case = MagicMock()
    monkeypatch.setattr(
        auditer_permission_checker, "AuditRepositoryAdapter", MagicMock()
    )
    monkeypatch.setattr(
        auditer_permission_checker,
        "RecordAuditEventUseCase",
        MagicMock(return_value=audit_use_case),
    )
    checker = audit_and_require_permission(
        Permission.REPORTS_MI_READ, audit_event_factory=MagicMock()
    )
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/reports/mi-test",
            "headers": [],
        }
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            checker(
                permissions=set(),
                credentials=HTTPAuthorizationCredentials(
                    scheme="Bearer", credentials="test-token"
                ),
                entra_auth_port=MagicMock(),
                session=MagicMock(),
                request=request,
            )
        )

    assert exc_info.value.status_code == 403
    audit_use_case.execute.assert_called_once()
    denial_logs = [
        record
        for record in caplog.records
        if getattr(record, "extra", {}).get("event") == "report_access_denied"
    ]
    assert len(denial_logs) == 1
    assert denial_logs[0].levelno == logging.ERROR
    assert denial_logs[0].extra["route"] == "/reports/mi-test"
    assert denial_logs[0].extra["method"] == "GET"
    assert denial_logs[0].extra["status_code"] == 403
