import asyncio
from unittest.mock import MagicMock, ANY

from app.models.audit.index import ViewApplicationAudit
from app.routers.dependencies.view_application_audit_writer import (
    ViewApplicationAuditWriter,
)
from app.use_cases.audit.view_application_audit import ViewApplicationAuditUseCase


def test_audit_writer_initialization():
    audit_writer = ViewApplicationAuditWriter(page="overview")
    assert audit_writer.page == "overview"


def test_audit_writer_calls_audit_port_with_user_email_address():
    audit_port = MagicMock()
    audit_writer = ViewApplicationAuditWriter(page="overview")
    asyncio.run(
        audit_writer(
            user_email_address="user@example.com",
            laa_reference="LAA123",
            use_case=ViewApplicationAuditUseCase(audit_port=audit_port),
        )
    )
    audit_port.audit_event.assert_called_once_with(
        ViewApplicationAudit(
            timestamp=ANY,
            user_email_address="user@example.com",
            laa_reference="LAA123",
            page="overview",
        )
    )
