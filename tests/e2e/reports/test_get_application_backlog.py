from datetime import UTC, datetime

from app.auth.rbac import Role
from app.domain.constants.report_csv_headers import APPLICATION_BACKLOG_REPORT_HEADERS
from app.models.application.enums import MeritsDecision
from tests.factories.persisted import create_application
from tests.helpers.csv_helpers import parse_csv_rows


class TestGetApplicationBacklogReport:
    """E2E tests for GET /reports/applications/backlog."""

    def test_200_returns_csv_with_pending_applications(self, client):
        response = client.get(
            "/reports/applications/backlog",
            headers={
                "Authorization": f"Bearer {Role.APPLICATION_WORKFLOW_REPORTING.value}"
            },
        )

        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        assert "attachment" in response.headers["content-disposition"]
        assert ".csv" in response.headers["content-disposition"]

    def test_200_csv_contains_expected_headers(self, session, client):
        create_application(
            session, proceeding_overrides={"merits_decision": MeritsDecision.PENDING}
        )

        response = client.get(
            "/reports/applications/backlog",
            headers={
                "Authorization": f"Bearer {Role.APPLICATION_WORKFLOW_REPORTING.value}"
            },
        )

        rows = parse_csv_rows(response.text)
        assert len(rows) >= 1
        assert list(rows[0].keys()) == APPLICATION_BACKLOG_REPORT_HEADERS

    def test_200_csv_row_contains_expected_data_for_pending_application(
        self, session, client
    ):
        create_application(
            session, proceeding_overrides={"merits_decision": MeritsDecision.PENDING}
        )

        response = client.get(
            "/reports/applications/backlog",
            headers={
                "Authorization": f"Bearer {Role.APPLICATION_WORKFLOW_REPORTING.value}"
            },
        )

        rows = parse_csv_rows(response.text)

        row = rows[0]
        assert row["Current Application Status"] == MeritsDecision.PENDING
        for header in APPLICATION_BACKLOG_REPORT_HEADERS:
            assert row[header] != "", f"Expected '{header}' to be non-empty"

    def test_200_csv_excludes_non_pending_applications(self, session, client):
        create_application(
            session,
            provider_overrides={"firm_code": "XGRANT"},
            proceeding_overrides={"merits_decision": MeritsDecision.GRANTED},
        )

        create_application(
            session,
            provider_overrides={"firm_code": "XGRANT"},
            proceeding_overrides={"merits_decision": MeritsDecision.REFUSED},
        )

        response = client.get(
            "/reports/applications/backlog",
            headers={
                "Authorization": f"Bearer {Role.APPLICATION_WORKFLOW_REPORTING.value}"
            },
        )

        rows = parse_csv_rows(response.text)
        status = [row["Current Application Status"] for row in rows]

        assert MeritsDecision.GRANTED not in status
        assert MeritsDecision.REFUSED not in status

    def test_200_csv_ordered_by_application_received_date_ascending(
        self, session, client
    ):
        pending = {"merits_decision": MeritsDecision.PENDING}

        older_app = create_application(
            session,
            proceeding_overrides=pending,
            created_at=datetime(2020, 1, 1, tzinfo=UTC),
        )

        create_application(
            session,
            proceeding_overrides=pending,
            created_at=datetime(2022, 1, 1, tzinfo=UTC),
        )

        response = client.get(
            "/reports/applications/backlog",
            headers={
                "Authorization": f"Bearer {Role.APPLICATION_WORKFLOW_REPORTING.value}"
            },
        )

        rows = parse_csv_rows(response.text)
        assert len(rows) == 2

        dates = [row["Application Received Date"] for row in rows]
        assert dates == sorted(dates)
        assert rows[0]["Application / Case Reference Number"] == str(
            older_app.laa_reference
        )


class TestGetApplicationBacklogReportAuth:
    """Authentication tests for GET /reports/applications/backlog."""

    def test_200_returns_ok_when_caseworker_token(self, client):
        response = client.get(
            "/reports/applications/backlog",
            headers={
                "Authorization": f"Bearer {Role.APPLICATION_WORKFLOW_REPORTING.value}"
            },
        )

        assert response.status_code == 200
