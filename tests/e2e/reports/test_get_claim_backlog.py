import csv
import io
from datetime import UTC, datetime

from sqlmodel import select

from app.models.application.index import Application
from app.models.claim.enums import ClaimStatus
from app.models.claim.index import Claim
from tests.e2e.factories import create_claim_in_db

CLAIMS_BACKLOG_REPORT_HEADERS = [
    "Claims Reference Number",
    "Current Claims Status",
    "Claim Received Date",
    "Firm Name",
    "Firm Account Number",
    "Proceeding Code",
    "Matter Type",
]


def _parse_csv_rows(content: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(content)))


def _parse_csv_fieldnames(content: str) -> list[str]:
    reader = csv.DictReader(io.StringIO(content))
    return reader.fieldnames or []


class TestGetClaimBacklogReport:
    """E2E tests for GET /reports/claims/backlog."""

    def test_200_csv_has_good_data_quality(self, session, client, auth_token):
        application = session.exec(select(Application)).first()
        claim = create_claim_in_db(
            session,
            laa_reference=application.laa_reference,
            status=ClaimStatus.SUBMITTED,
            submission_date=datetime(2026, 1, 1, tzinfo=UTC),
        )

        response = client.get(
            "/reports/claims/backlog",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        assert "attachment" in response.headers["content-disposition"]
        assert "claims_backlog_report.csv" in response.headers["content-disposition"]
        assert _parse_csv_fieldnames(response.text) == CLAIMS_BACKLOG_REPORT_HEADERS

        rows = _parse_csv_rows(response.text)
        assert len(rows) == 1
        row = rows[0]
        assert row["Claims Reference Number"] == str(claim.claim_id)
        assert row["Current Claims Status"] == ClaimStatus.SUBMITTED
        assert row["Claim Received Date"] == "2026-01-01 00:00:00"
        assert row["Firm Account Number"] == application.provider.firm_code
        assert row["Firm Name"] == f"Firm {application.provider.firm_code}"
        assert row["Proceeding Code"] == application.proceeding.proceeding_id
        assert row["Matter Type"] == application.proceeding.matter_type

    def test_200_csv_excludes_non_open_claims(self, session, client, auth_token):
        application = session.exec(select(Application)).first()

        create_claim_in_db(
            session,
            laa_reference=application.laa_reference,
            status=ClaimStatus.SUBMITTED,
            submission_date=datetime(2026, 4, 1, tzinfo=UTC),
        )
        create_claim_in_db(
            session,
            laa_reference=application.laa_reference,
            status=ClaimStatus.REJECTED,
            submission_date=datetime(2026, 4, 2, tzinfo=UTC),
        )
        create_claim_in_db(
            session,
            laa_reference=application.laa_reference,
            status=ClaimStatus.PAY_IN_FULL,
            submission_date=datetime(2026, 4, 3, tzinfo=UTC),
        )

        response = client.get(
            "/reports/claims/backlog",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        rows = _parse_csv_rows(response.text)
        statuses = [row["Current Claims Status"] for row in rows]

        assert ClaimStatus.SUBMITTED in statuses
        assert ClaimStatus.REJECTED not in statuses
        assert ClaimStatus.PAY_IN_FULL not in statuses

    def test_200_when_no_qualifying_claims_returns_headers_only(
        self, session, client, auth_token
    ):
        claims = session.exec(select(Claim)).all()
        for claim in claims:
            session.delete(claim)
        session.commit()

        response = client.get(
            "/reports/claims/backlog",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 200
        assert _parse_csv_fieldnames(response.text) == CLAIMS_BACKLOG_REPORT_HEADERS
        assert _parse_csv_rows(response.text) == []


class TestGetClaimBacklogReportAuth:
    """Authentication tests for GET /reports/claims/backlog."""

    def test_401_returns_unauthorized_when_no_auth_header(self, entra_auth_client):
        response = entra_auth_client.get("/reports/claims/backlog")

        assert response.status_code == 401

    def test_401_returns_unauthorized_when_invalid_token(self, entra_auth_client):
        response = entra_auth_client.get(
            "/reports/claims/backlog",
            headers={"Authorization": "Bearer invalid-token"},
        )

        assert response.status_code == 401

    def test_403_returns_forbidden_when_provider_token(self, entra_auth_client):
        response = entra_auth_client.get(
            "/reports/claims/backlog",
            headers={"Authorization": "Bearer valid-provider-entra-token"},
        )

        assert response.status_code == 403

    def test_200_returns_ok_when_caseworker_token(self, entra_auth_client):
        response = entra_auth_client.get(
            "/reports/claims/backlog",
            headers={"Authorization": "Bearer valid-caseworker-entra-token"},
        )

        assert response.status_code == 200
