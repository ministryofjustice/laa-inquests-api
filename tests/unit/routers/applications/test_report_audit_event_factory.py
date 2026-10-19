from unittest.mock import ANY, MagicMock

import pytest

from app.models.audit.enums import ReportType
from app.models.audit.index import ReportAudit
from app.routers.dependencies.report_audit_event_factory import ReportAuditEventFactory


def test_builds_report_audit_event_for_the_report_type():
    audit_event = ReportAuditEventFactory(report_type=ReportType.CLAIMS_BACKLOG)(
        user_email_address="user@example.com",
        request=MagicMock(query_params={}),
    )

    assert audit_event == ReportAudit(
        timestamp=ANY,
        user_email_address="user@example.com",
        report_type=ReportType.CLAIMS_BACKLOG,
        parameters=None,
    )


def test_payment_extract_audit_event_records_query_parameters():
    query_params = {"from": "2024-01-01", "to": "2024-01-31"}

    audit_event = ReportAuditEventFactory(report_type=ReportType.PAYMENT_EXTRACT)(
        user_email_address="user@example.com",
        request=MagicMock(query_params=query_params),
    )

    assert audit_event.parameters == query_params


@pytest.mark.parametrize(
    "report_type", [ReportType.APPLICATIONS_BACKLOG, ReportType.CLAIMS_BACKLOG]
)
def test_backlog_audit_events_ignore_query_parameters(report_type):
    audit_event = ReportAuditEventFactory(report_type=report_type)(
        user_email_address="user@example.com",
        request=MagicMock(query_params={"unexpected": "value"}),
    )

    assert audit_event.parameters is None
