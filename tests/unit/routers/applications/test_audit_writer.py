from app.routers.dependencies.audit_writer import AuditWriter
from unittest.mock import MagicMock
from app.models.audit.enums import AuditType
import asyncio


def test_audit_writer_initialization():
    audit_writer = AuditWriter(report_type=AuditType.REPORTS_CLAIMS_BACKLOG)
    assert audit_writer.report_type == AuditType.REPORTS_CLAIMS_BACKLOG


def test_audit_writer_gets_user_email_address():
    entra_auth_port = MagicMock()
    audit_writer = AuditWriter(report_type=AuditType.REPORTS_CLAIMS_BACKLOG)
    asyncio.run(
        audit_writer(
            credentials=MagicMock(),
            entra_auth_port=entra_auth_port,
            audit_port=MagicMock(),
            request=MagicMock(),
        )
    )
    entra_auth_port.get_email_address.assert_called_once()


def test_audit_writer_calls_audit_port():
    audit_port = MagicMock()
    audit_writer = AuditWriter(report_type=AuditType.REPORTS_CLAIMS_BACKLOG)
    asyncio.run(
        audit_writer(
            credentials=MagicMock(),
            entra_auth_port=MagicMock(),
            audit_port=audit_port,
            request=MagicMock(),
        )
    )
    audit_port.audit_report_download.assert_called_once()
