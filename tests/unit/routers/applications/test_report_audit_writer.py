import asyncio
from unittest.mock import MagicMock

from app.models.audit.enums import ReportType
from app.routers.dependencies.report_audit_writer import ReportAuditWriter
from app.use_cases.report_audit import ReportAuditUseCase


def test_audit_writer_initialization():
    audit_writer = ReportAuditWriter(report_type=ReportType.CLAIMS_BACKLOG)
    assert audit_writer.report_type == ReportType.CLAIMS_BACKLOG


def test_audit_writer_calls_audit_port_with_user_email_address():
    audit_port = MagicMock()
    audit_writer = ReportAuditWriter(report_type=ReportType.CLAIMS_BACKLOG)
    asyncio.run(
        audit_writer(
            user_email_address="user@example.com",
            use_case=ReportAuditUseCase(audit_port=audit_port),
            request=MagicMock(),
        )
    )
    audit_port.audit_report.assert_called_once_with(
        user_email_address="user@example.com",
        report_type=ReportType.CLAIMS_BACKLOG,
        parameters=None,
    )
