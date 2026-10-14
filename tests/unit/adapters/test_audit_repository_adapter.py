from datetime import UTC, datetime

from app.adapters.audit_repository_adapter import AuditRepositoryAdapter
from app.models.audit.enums import AuditType
from app.models.audit.index import ReportDownloadAudit


def test_audit_report_download_persists_event_with_expected_values(session):
    adapter = AuditRepositoryAdapter(session)

    created = adapter.audit_report_download(
        user_email_address="test_user@example.com",
        report_type=AuditType.REPORTS_CLAIMS_BACKLOG,
    )

    stored = session.get(ReportDownloadAudit, created.id)

    assert created.id is not None
    assert stored is not None
    assert stored.user_email_address == "test_user@example.com"
    assert stored.report_type == AuditType.REPORTS_CLAIMS_BACKLOG
    assert stored.parameters is None


def test_audit_report_download_sets_timestamp_automatically(session):
    adapter = AuditRepositoryAdapter(session)

    before_creation = datetime.now(UTC)
    created = adapter.audit_report_download(
        user_email_address="test_user@example.com",
        report_type=AuditType.REPORTS_CLAIMS_BACKLOG,
    )
    after_creation = datetime.now(UTC)

    assert created.timestamp is not None
    timestamp = (
        created.timestamp.replace(tzinfo=UTC)
        if created.timestamp.tzinfo is None
        else created.timestamp
    )
    assert before_creation <= timestamp <= after_creation


def test_audit_report_download_requires_user_email_address(session):
    adapter = AuditRepositoryAdapter(session)

    try:
        adapter.audit_report_download(
            user_email_address="",
            report_type=AuditType.REPORTS_CLAIMS_BACKLOG,
        )
    except ValueError as e:
        assert (
            str(e)
            == "User email address must be provided for report download audit creation."
        )
    else:
        assert False, "Expected ValueError for missing user email address"


def test_commit_commits_transaction(session):
    adapter = AuditRepositoryAdapter(session)

    created = adapter.audit_report_download(
        user_email_address="test_user@example.com",
        report_type=AuditType.REPORTS_CLAIMS_BACKLOG,
    )
    assert session.get_transaction() is not None
    adapter.commit()
    assert session.get_transaction() is None

    stored = session.get(ReportDownloadAudit, created.id)
    assert stored is not None


def test_rollback_rolls_back_transaction(session):
    adapter = AuditRepositoryAdapter(session)

    created = adapter.audit_report_download(
        user_email_address="test_user@example.com",
        report_type=AuditType.REPORTS_CLAIMS_BACKLOG,
    )
    assert session.get_transaction() is not None
    adapter.rollback()
    assert session.get_transaction() is None

    stored = session.get(ReportDownloadAudit, created.id)
    assert stored is None
