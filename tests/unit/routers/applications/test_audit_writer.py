import asyncio
from unittest.mock import MagicMock

from app.models.audit.enums import AuditType
from app.routers.dependencies.audit_writer import AuditWriter
from app.use_cases.audit_report_download import AuditReportDownloadUseCase


def test_audit_writer_initialization():
    audit_writer = AuditWriter(report_type=AuditType.REPORTS_CLAIMS_BACKLOG)
    assert audit_writer.report_type == AuditType.REPORTS_CLAIMS_BACKLOG


def test_audit_writer_calls_audit_port_with_user_email_address():
    audit_port = MagicMock()
    audit_writer = AuditWriter(report_type=AuditType.REPORTS_CLAIMS_BACKLOG)
    asyncio.run(
        audit_writer(
            user_email_address="user@example.com",
            use_case=AuditReportDownloadUseCase(audit_port=audit_port),
            request=MagicMock(),
        )
    )
    audit_port.audit_report_download.assert_called_once_with(
        user_email_address="user@example.com",
        report_type=AuditType.REPORTS_CLAIMS_BACKLOG,
        parameters=None,
    )
