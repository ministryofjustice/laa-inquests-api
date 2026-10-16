from unittest.mock import ANY, MagicMock, call

from app.models.audit.index import ViewApplicationAudit
import pytest

from app.ports.audit_port import AuditPort
from app.use_cases.exceptions import AuditError
from app.use_cases.audit.view_application_audit import ViewApplicationAuditUseCase


def test_view_application_audit_writes_and_commits_the_entry():
    audit_port = MagicMock(spec=AuditPort)
    use_case = ViewApplicationAuditUseCase(audit_port=audit_port)
    page = "overview"
    laa_reference = "LAA123456"

    use_case.execute(
        user_email_address="test@example.com",
        laa_reference=laa_reference,
        page=page,
    )

    assert audit_port.mock_calls == [
        call.audit_event(
            ViewApplicationAudit(
                timestamp=ANY,
                user_email_address="test@example.com",
                laa_reference=laa_reference,
                page=page,
            ),
        ),
        call.commit(),
    ]


def test_view_application_audit_requires_user_email_address():
    audit_port = MagicMock(spec=AuditPort)
    use_case = ViewApplicationAuditUseCase(audit_port=audit_port)
    laa_reference = "LAA123456"

    try:
        use_case.execute(
            user_email_address=None,
            laa_reference=laa_reference,
            page="overview",
        )
    except ValueError as e:
        assert (
            str(e)
            == "User email address must be provided for view application audit creation."
        )
    else:
        assert False, "Expected ValueError for missing user email address"


def test_view_application_audit_requires_non_empty_user_email_address():
    audit_port = MagicMock(spec=AuditPort)
    use_case = ViewApplicationAuditUseCase(audit_port=audit_port)
    laa_reference = "LAA123456"

    try:
        use_case.execute(
            user_email_address="   ",
            laa_reference=laa_reference,
            page="overview",
        )
    except ValueError as e:
        assert (
            str(e)
            == "User email address must be provided for view application audit creation."
        )
    else:
        assert False, "Expected ValueError for missing user email address"


def test_view_application_audit_requires_laa_reference():
    audit_port = MagicMock(spec=AuditPort)
    use_case = ViewApplicationAuditUseCase(audit_port=audit_port)
    try:
        use_case.execute(
            user_email_address="test@example.com",
            laa_reference=None,
            page="overview",
        )
    except ValueError as e:
        assert (
            str(e)
            == "LAA reference must be provided for view application audit creation."
        )
    else:
        assert False, "Expected ValueError for missing LAA reference"


def test_view_application_audit_requires_non_empty_laa_reference():
    audit_port = MagicMock(spec=AuditPort)
    use_case = ViewApplicationAuditUseCase(audit_port=audit_port)

    try:
        use_case.execute(
            user_email_address="test@example.com",
            laa_reference="   ",
            page="overview",
        )
    except ValueError as e:
        assert (
            str(e)
            == "LAA reference must be provided for view application audit creation."
        )
    else:
        assert False, "Expected ValueError for missing LAA reference"


@pytest.mark.parametrize("failing_operation", ["audit_event", "commit"])
def test_view_application_audit_rolls_back_and_propagates_audit_failure(
    failing_operation,
):
    audit_port = MagicMock(spec=AuditPort)
    error = AuditError("Audit storage unavailable")
    getattr(audit_port, failing_operation).side_effect = error
    use_case = ViewApplicationAuditUseCase(audit_port=audit_port)

    with pytest.raises(AuditError) as exc_info:
        use_case.execute(
            user_email_address="test@example.com",
            laa_reference="LAA123456",
            page="overview",
        )

    assert exc_info.value is error
    audit_port.rollback.assert_called_once_with()
    if failing_operation == "audit_event":
        audit_port.commit.assert_not_called()
