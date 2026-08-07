import csv
import io
from datetime import UTC, datetime

from app.domain.constants.report_csv_headers import APPLICATION_BACKLOG_REPORT_HEADERS
from app.models.application.enums import MeritsDecision
from tests.e2e.factories import create_application_in_db


def _parse_csv(content: str) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(content))
    return list(reader)


class TestGetApplicationBacklogReport:
    """E2E tests for GET /reports/applications/backlog."""

    def test_200_returns_csv_with_pending_applications(self, client, auth_token):
        response = client.get(
            "/reports/applications/backlog",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        assert "attachment" in response.headers["content-disposition"]
        assert ".csv" in response.headers["content-disposition"]

    def test_200_csv_contains_expected_headers(self, client, auth_token):
        response = client.get(
            "/reports/applications/backlog",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        rows = _parse_csv(response.text)
        assert len(rows) >= 1
        assert list(rows[0].keys()) == APPLICATION_BACKLOG_REPORT_HEADERS

    def test_200_csv_row_contains_expected_data_for_pending_application(
        self, client, auth_token
    ):
        response = client.get(
            "/reports/applications/backlog",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        rows = _parse_csv(response.text)

        row = rows[0]
        assert row["Current Application Status"] == MeritsDecision.PENDING
        for header in APPLICATION_BACKLOG_REPORT_HEADERS:
            assert row[header] != "", f"Expected '{header}' to be non-empty"

    def test_200_csv_excludes_non_pending_applications(
        self, session, client, auth_token
    ):
        create_application_in_db(
            session,
            provider_overrides={"firm_code": "XGRANT"},
            proceeding_overrides={"merits_decision": MeritsDecision.GRANTED},
        )

        create_application_in_db(
            session,
            provider_overrides={"firm_code": "XGRANT"},
            proceeding_overrides={"merits_decision": MeritsDecision.REFUSED},
        )

        response = client.get(
            "/reports/applications/backlog",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        rows = _parse_csv(response.text)
        status = [row["Current Application Status"] for row in rows]

        assert MeritsDecision.GRANTED not in status
        assert MeritsDecision.REFUSED not in status

    def test_200_csv_ordered_by_application_received_date_ascending(
        self, session, client, auth_token
    ):
        older_app = create_application_in_db(
            session,
            provider_overrides={"firm_code": "XOLD01"},
            created_at=datetime(2020, 1, 1, tzinfo=UTC),
        )

        create_application_in_db(
            session,
            provider_overrides={"firm_code": "XOLD01"},
            created_at=datetime(2022, 1, 1, tzinfo=UTC),
        )

        response = client.get(
            "/reports/applications/backlog",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        rows = _parse_csv(response.text)
        assert len(rows) >= 3

        dates = [row["Application Received Date"] for row in rows]
        assert dates == sorted(dates)
        assert rows[0]["Application / Case Reference Number"] == str(
            older_app.laa_reference
        )


class TestGetApplicationBacklogReportAuth:
    """Authentication tests for GET /reports/applications/backlog."""

    def test_401_returns_unauthorized_when_no_auth_header(self, entra_auth_client):
        response = entra_auth_client.get("/reports/applications/backlog")

        assert response.status_code == 401

    def test_401_returns_unauthorized_when_invalid_token(self, entra_auth_client):
        response = entra_auth_client.get(
            "/reports/applications/backlog",
            headers={"Authorization": "Bearer invalid-token"},
        )

        assert response.status_code == 401

    def test_403_returns_forbidden_when_provider_token(self, entra_auth_client):
        response = entra_auth_client.get(
            "/reports/applications/backlog",
            headers={"Authorization": "Bearer valid-provider-entra-token"},
        )

        assert response.status_code == 403

    def test_200_returns_ok_when_caseworker_token(self, entra_auth_client):
        response = entra_auth_client.get(
            "/reports/applications/backlog",
            headers={"Authorization": "Bearer valid-caseworker-entra-token"},
        )

        assert response.status_code == 200
