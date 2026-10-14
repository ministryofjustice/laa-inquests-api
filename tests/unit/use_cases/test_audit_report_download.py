from unittest.mock import MagicMock, call

import pytest

from app.models.audit.enums import AuditType
from app.ports.create_audit_event_port import AuditPort
from app.use_cases.audit_report_download import AuditReportDownloadUseCase
from app.use_cases.exceptions import AuditError


def test_audit_report_download_writes_and_commits_the_entry():
    audit_port = MagicMock(spec=AuditPort)
    use_case = AuditReportDownloadUseCase(audit_port=audit_port)
    parameters = {"from": "2024-01-01", "to": "2024-01-31"}

    use_case.execute(
        user_email_address="test@example.com",
        report_type=AuditType.REPORTS_PAYMENT_EXTRACT,
        parameters=parameters,
    )

    assert audit_port.mock_calls == [
        call.audit_report_download(
            user_email_address="test@example.com",
            report_type=AuditType.REPORTS_PAYMENT_EXTRACT,
            parameters=parameters,
        ),
        call.commit(),
    ]


@pytest.mark.parametrize("failing_operation", ["audit_report_download", "commit"])
def test_audit_report_download_rolls_back_and_propagates_audit_failure(
    failing_operation,
):
    audit_port = MagicMock(spec=AuditPort)
    error = AuditError("Audit storage unavailable")
    getattr(audit_port, failing_operation).side_effect = error
    use_case = AuditReportDownloadUseCase(audit_port=audit_port)

    with pytest.raises(AuditError) as exc_info:
        use_case.execute(
            user_email_address="test@example.com",
            report_type=AuditType.REPORTS_CLAIMS_BACKLOG,
        )

    assert exc_info.value is error
    audit_port.rollback.assert_called_once_with()
    if failing_operation == "audit_report_download":
        audit_port.commit.assert_not_called()
