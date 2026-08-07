import csv
import io
from datetime import UTC, datetime

from sqlmodel import select

from app.models.application.index import Application
from app.models.claim.enums import ClaimStatus
from app.models.claim.index import Claim
from tests.e2e.factories import create_application_in_db, create_claim_in_db

CLAIMS_BACKLOG_REPORT_HEADERS = [
    "Claims Reference Number",
    "Current Claims Status",
    "Claim Submission Date",
    "Office Name",
    "Office Account Number (Firm Office Code)",
    "Total 0% VAT claim value",
    "Net total claim value",
    "Gross total claim value",
    "Claim type (POA or final bill)",
]


def _parse_csv_rows(content: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(content)))


def _parse_csv_fieldnames(content: str) -> list[str]:
    reader = csv.DictReader(io.StringIO(content))
    return reader.fieldnames or []


class TestGetClaimBacklogReport:
    """E2E tests for GET /reports/claims/backlog."""

    def test_200_returns_csv_with_submitted_claims(self, session, client, auth_token):
        application = session.exec(select(Application)).first()
        create_claim_in_db(
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

    def test_200_csv_has_good_data_quality(self, session, client, auth_token):
        first_application = session.exec(select(Application)).first()
        second_application = create_application_in_db(
            session,
            provider_overrides={"firm_code": "OFFICE2", "office_id": "002"},
        )

        create_claim_in_db(
            session,
            laa_reference=second_application.laa_reference,
            status=ClaimStatus.SUBMITTED,
            submission_date=datetime(2026, 6, 1, tzinfo=UTC),
        )
        older_claim = create_claim_in_db(
            session,
            laa_reference=first_application.laa_reference,
            status=ClaimStatus.SUBMITTED,
            submission_date=datetime(2026, 1, 1, tzinfo=UTC),
        )

        response = client.get(
            "/reports/claims/backlog",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        rows = _parse_csv_rows(response.text)
        dates = [row["Claim Submission Date"] for row in rows]

        assert response.status_code == 200
        # Headers
        actual_headers = _parse_csv_fieldnames(response.text)
        assert actual_headers == CLAIMS_BACKLOG_REPORT_HEADERS

        assert len(rows) >= 2
        assert dates == sorted(dates)
        assert rows[0]["Claims Reference Number"] == str(older_claim.claim_id)

        for row in rows:
            assert row["Current Claims Status"] == ClaimStatus.SUBMITTED
            for header in CLAIMS_BACKLOG_REPORT_HEADERS:
                assert row[header] != "", f"Expected '{header}' to be non-empty"

    def test_200_csv_excludes_non_submitted_claims(self, session, client, auth_token):
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
