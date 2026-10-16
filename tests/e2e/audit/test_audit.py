from app.auth.rbac import Role
from app.models.audit.enums import ReportType
from app.models.audit.index import ReportAudit


class TestAuditReports:
    """E2e tests for audit functionality on report downloads"""

    def test_claims_backlog_download_creates_an_audit_entry(self, client, session):
        response = client.get(
            "/reports/claims/backlog",
            headers={"Authorization": f"Bearer {Role.CLAIM_WORKFLOW_REPORTING.value}"},
        )

        assert response.status_code == 200

        audit_entry = (
            session.query(ReportAudit).order_by(ReportAudit.timestamp.desc()).first()
        )
        assert audit_entry is not None
        assert audit_entry.report_type == ReportType.CLAIMS_BACKLOG
        assert audit_entry.timestamp is not None
        assert audit_entry.user_email_address == "test@example.com"
        assert audit_entry.parameters is None

    def test_applications_backlog_download_creates_an_audit_entry(
        self, client, session
    ):
        response = client.get(
            "/reports/applications/backlog",
            headers={
                "Authorization": f"Bearer {Role.APPLICATION_WORKFLOW_REPORTING.value}"
            },
        )

        assert response.status_code == 200

        audit_entry = (
            session.query(ReportAudit).order_by(ReportAudit.timestamp.desc()).first()
        )
        assert audit_entry is not None
        assert audit_entry.report_type == ReportType.APPLICATIONS_BACKLOG
        assert audit_entry.timestamp is not None
        assert audit_entry.user_email_address == "test@example.com"
        assert audit_entry.parameters is None

    def test_payment_extract_download_creates_an_audit_entry(self, client, session):
        response = client.get(
            "/reports/payment-extract?from=2024-01-01&to=2024-01-31",
            headers={"Authorization": f"Bearer {Role.FINANCE.value}"},
        )

        assert response.status_code == 200

        audit_entry = (
            session.query(ReportAudit).order_by(ReportAudit.timestamp.desc()).first()
        )
        assert audit_entry is not None
        assert audit_entry.report_type == ReportType.PAYMENT_EXTRACT
        assert audit_entry.timestamp is not None
        assert audit_entry.user_email_address == "test@example.com"
        assert audit_entry.parameters == {"from": "2024-01-01", "to": "2024-01-31"}
