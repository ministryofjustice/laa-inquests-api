from unittest.mock import MagicMock, call

import pytest

from app.models.audit.enums import ReportType
from app.models.audit.index import ReportAudit
from app.ports.audit_port import AuditPort
from app.use_cases.audit.record_audit_event import RecordAuditEventUseCase
from app.use_cases.exceptions import AuditError


def _audit_event(user_email_address: str | None = "test@example.com") -> ReportAudit:
    return ReportAudit(
        user_email_address=user_email_address,
        report_type=ReportType.CLAIMS_BACKLOG,
    )


def test_record_audit_event_writes_and_commits_the_entry():
    audit_port = MagicMock(spec=AuditPort)
    audit_event = _audit_event()

    RecordAuditEventUseCase(audit_port=audit_port).execute(audit_event)

    assert audit_port.mock_calls == [call.audit_event(audit_event), call.commit()]


@pytest.mark.parametrize("user_email_address", [None, "", "   "])
def test_record_audit_event_requires_user_email_address(user_email_address):
    audit_port = MagicMock(spec=AuditPort)
    use_case = RecordAuditEventUseCase(audit_port=audit_port)

    with pytest.raises(
        ValueError, match="User email address must be provided for audit creation."
    ):
        use_case.execute(_audit_event(user_email_address))

    audit_port.audit_event.assert_not_called()


@pytest.mark.parametrize("failing_operation", ["audit_event", "commit"])
def test_record_audit_event_rolls_back_and_propagates_audit_failure(
    failing_operation,
):
    audit_port = MagicMock(spec=AuditPort)
    error = AuditError("Audit storage unavailable")
    getattr(audit_port, failing_operation).side_effect = error
    use_case = RecordAuditEventUseCase(audit_port=audit_port)

    with pytest.raises(AuditError) as exc_info:
        use_case.execute(_audit_event())

    assert exc_info.value is error
    audit_port.rollback.assert_called_once_with()
    if failing_operation == "audit_event":
        audit_port.commit.assert_not_called()
