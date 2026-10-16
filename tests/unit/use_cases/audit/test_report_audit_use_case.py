from unittest.mock import ANY, MagicMock, call

from app.models.audit.index import ReportAudit
import pytest

from app.models.audit.enums import ReportType
from app.ports.audit_port import AuditPort
from app.use_cases.exceptions import AuditError
from app.use_cases.audit.report_audit import ReportAuditUseCase


def test_audit_report_writes_and_commits_the_entry():
    audit_port = MagicMock(spec=AuditPort)
    use_case = ReportAuditUseCase(audit_port=audit_port)
    parameters = {"from": "2024-01-01", "to": "2024-01-31"}

    use_case.execute(
        user_email_address="test@example.com",
        report_type=ReportType.PAYMENT_EXTRACT,
        parameters=parameters,
    )

    assert audit_port.mock_calls == [
        call.audit_event(
            ReportAudit(
                timestamp=ANY,
                user_email_address="test@example.com",
                report_type=ReportType.PAYMENT_EXTRACT,
                parameters=parameters,
            ),
        ),
        call.commit(),
    ]


def test_audit_report_requires_user_email_address():
    audit_port = MagicMock(spec=AuditPort)
    use_case = ReportAuditUseCase(audit_port=audit_port)
    parameters = {"from": "2024-01-01", "to": "2024-01-31"}

    try:
        use_case.execute(
            user_email_address=None,
            report_type=ReportType.PAYMENT_EXTRACT,
            parameters=parameters,
        )
    except ValueError as e:
        assert (
            str(e) == "User email address must be provided for report audit creation."
        )
    else:
        assert False, "Expected ValueError for missing user email address"


def test_audit_report_requires_non_empty_user_email_address():
    audit_port = MagicMock(spec=AuditPort)
    use_case = ReportAuditUseCase(audit_port=audit_port)
    parameters = {"from": "2024-01-01", "to": "2024-01-31"}

    try:
        use_case.execute(
            user_email_address="   ",
            report_type=ReportType.PAYMENT_EXTRACT,
            parameters=parameters,
        )
    except ValueError as e:
        assert (
            str(e) == "User email address must be provided for report audit creation."
        )
    else:
        assert False, "Expected ValueError for missing user email address"


@pytest.mark.parametrize("failing_operation", ["audit_event", "commit"])
def test_audit_report_rolls_back_and_propagates_audit_failure(
    failing_operation,
):
    audit_port = MagicMock(spec=AuditPort)
    error = AuditError("Audit storage unavailable")
    getattr(audit_port, failing_operation).side_effect = error
    use_case = ReportAuditUseCase(audit_port=audit_port)

    with pytest.raises(AuditError) as exc_info:
        use_case.execute(
            user_email_address="test@example.com",
            report_type=ReportType.CLAIMS_BACKLOG,
        )

    assert exc_info.value is error
    audit_port.rollback.assert_called_once_with()
    if failing_operation == "audit_event":
        audit_port.commit.assert_not_called()
