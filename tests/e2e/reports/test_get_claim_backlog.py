from datetime import UTC, datetime

from sqlmodel import select

from app.auth.rbac import Role
from app.models.application.index import Application
from app.models.claim.enums import ClaimStatus
from app.models.claim.index import Claim
from tests.e2e.factories import create_claim_in_db
from tests.helpers.csv_helpers import parse_csv_fieldnames, parse_csv_rows

CLAIMS_BACKLOG_REPORT_HEADERS = [
    "Case reference",
    "Firm Name",
    "Firm Account Number",
    "Submission date",
    "Claim status",
    "Total 0% VAT claim value",
    "Net total claim value",
    "Gross total claim value",
    "Claim type",
]


class TestGetClaimBacklogReport:
    """E2E tests for GET /reports/claims/backlog."""

    def test_200_csv_has_good_data_quality(self, session, client):
        application = session.exec(select(Application)).first()
        claim = create_claim_in_db(
            session,
            application_id=application.application_id,
            status=ClaimStatus.SUBMITTED,
            submission_date=datetime(2026, 1, 1, tzinfo=UTC),
        )

        response = client.get(
            "/reports/claims/backlog",
            headers={"Authorization": f"Bearer {Role.CLAIM_WORKFLOW_REPORTING.value}"},
        )

        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        assert "attachment" in response.headers["content-disposition"]
        assert "claims_backlog_report.csv" in response.headers["content-disposition"]
        assert parse_csv_fieldnames(response.text) == CLAIMS_BACKLOG_REPORT_HEADERS

        rows = parse_csv_rows(response.text)
        assert len(rows) == 1
        row = rows[0]
        assert row["Case reference"] == claim.claim_reference
        assert row["Firm Account Number"] == application.provider.firm_code
        assert row["Firm Name"] == f"Firm {application.provider.firm_code}"
        assert row["Submission date"] == "2026-01-01 00:00:00"
        assert row["Claim status"] == ClaimStatus.SUBMITTED
        assert row["Total 0% VAT claim value"] == "0.00"
        assert row["Net total claim value"] == "100.00"
        assert row["Gross total claim value"] == "120.00"
        assert row["Claim type"] == "FINAL_BILL"

    def test_200_csv_excludes_non_open_claims(self, session, client):
        application = session.exec(select(Application)).first()

        create_claim_in_db(
            session,
            application_id=application.application_id,
            status=ClaimStatus.SUBMITTED,
            submission_date=datetime(2026, 4, 2, tzinfo=UTC),
        )
        create_claim_in_db(
            session,
            application_id=application.application_id,
            status=ClaimStatus.REJECTED,
            submission_date=datetime(2026, 4, 2, tzinfo=UTC),
        )
        create_claim_in_db(
            session,
            application_id=application.application_id,
            status=ClaimStatus.SUBMITTED,
            submission_date=datetime(2026, 4, 1, tzinfo=UTC),
        )

        response = client.get(
            "/reports/claims/backlog",
            headers={"Authorization": f"Bearer {Role.CLAIM_WORKFLOW_REPORTING.value}"},
        )

        rows = parse_csv_rows(response.text)
        statuses = [row["Claim status"] for row in rows]
        submission_dates = [row["Submission date"] for row in rows]

        assert ClaimStatus.SUBMITTED in statuses
        assert ClaimStatus.REJECTED not in statuses
        assert submission_dates == sorted(submission_dates)

    def test_200_when_no_qualifying_claims_returns_headers_only(self, session, client):
        claims = session.exec(select(Claim)).all()
        for claim in claims:
            session.delete(claim)
        session.commit()

        response = client.get(
            "/reports/claims/backlog",
            headers={"Authorization": f"Bearer {Role.CLAIM_WORKFLOW_REPORTING.value}"},
        )

        assert response.status_code == 200
        assert parse_csv_fieldnames(response.text) == CLAIMS_BACKLOG_REPORT_HEADERS
        assert parse_csv_rows(response.text) == []


class TestGetClaimBacklogReportAuth:
    """Authentication tests for GET /reports/claims/backlog."""

    def test_200_returns_ok_when_caseworker_token(self, client):
        response = client.get(
            "/reports/claims/backlog",
            headers={"Authorization": f"Bearer {Role.CLAIM_WORKFLOW_REPORTING.value}"},
        )

        assert response.status_code == 200
