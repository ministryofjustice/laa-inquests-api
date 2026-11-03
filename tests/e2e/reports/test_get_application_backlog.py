from datetime import UTC, datetime

import pytest
from sqlmodel import select

from app.auth.rbac import Role
from app.domain.constants.report_csv_headers import APPLICATION_BACKLOG_REPORT_HEADERS
from app.models.application.enums import MeritsDecision
from app.models.application.index import Application, DuplicateApplicationRecord
from tests.e2e.factories import create_application_in_db
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
        application = session.exec(select(Application)).first()
        application.proceeding.merits_decision = MeritsDecision.SUBMITTED
        session.add(application.proceeding)
        session.commit()

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
        application = session.exec(select(Application)).first()
        application.proceeding.merits_decision = MeritsDecision.SUBMITTED
        session.add(application.proceeding)
        session.commit()

        response = client.get(
            "/reports/applications/backlog",
            headers={
                "Authorization": f"Bearer {Role.APPLICATION_WORKFLOW_REPORTING.value}"
            },
        )

        rows = parse_csv_rows(response.text)

        row = rows[0]
        assert row["Office account number"] == application.provider.office_id
        assert row["Proceeding"] == application.proceeding.proceeding_description
        assert row["Current application status"] == MeritsDecision.SUBMITTED
        for header in APPLICATION_BACKLOG_REPORT_HEADERS:
            if header == "Potential duplicate submitted application reference(s)":
                assert row[header] == ""
            else:
                assert row[header] != "", f"Expected '{header}' to be non-empty"

    def test_200_csv_excludes_non_pending_applications(self, session, client):
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
            headers={
                "Authorization": f"Bearer {Role.APPLICATION_WORKFLOW_REPORTING.value}"
            },
        )

        rows = parse_csv_rows(response.text)
        status = [row["Current application status"] for row in rows]

        assert MeritsDecision.GRANTED not in status
        assert MeritsDecision.REFUSED not in status

    def test_200_csv_ordered_by_application_received_date_ascending(
        self, session, client
    ):
        application = session.exec(select(Application)).first()
        application.proceeding.merits_decision = MeritsDecision.SUBMITTED
        session.add(application.proceeding)
        session.commit()

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
            headers={
                "Authorization": f"Bearer {Role.APPLICATION_WORKFLOW_REPORTING.value}"
            },
        )

        rows = parse_csv_rows(response.text)
        assert len(rows) >= 3

        dates = [row["Application received date"] for row in rows]
        assert dates == sorted(dates)
        assert rows[0]["Application reference"] == str(older_app.laa_reference)

    def test_200_csv_reports_direct_submitted_duplicates_in_both_directions(
        self, session, client
    ):
        first = create_application_in_db(
            session,
            laa_reference="INQ-AAA-001",
            created_at=datetime(2020, 1, 1, tzinfo=UTC),
        )
        second = create_application_in_db(
            session,
            laa_reference="INQ-AAA-002",
            created_at=datetime(2021, 1, 1, tzinfo=UTC),
        )
        third = create_application_in_db(
            session,
            laa_reference="INQ-AAA-003",
            created_at=datetime(2022, 1, 1, tzinfo=UTC),
        )
        decided = create_application_in_db(
            session,
            proceeding_overrides={"merits_decision": MeritsDecision.GRANTED},
        )
        session.add_all(
            [
                DuplicateApplicationRecord(
                    application_id=third.application_id,
                    duplicate_application_id=first.application_id,
                ),
                DuplicateApplicationRecord(
                    application_id=first.application_id,
                    duplicate_application_id=second.application_id,
                ),
                DuplicateApplicationRecord(
                    application_id=second.application_id,
                    duplicate_application_id=first.application_id,
                ),
                DuplicateApplicationRecord(
                    application_id=first.application_id,
                    duplicate_application_id=decided.application_id,
                ),
            ]
        )
        session.commit()

        response = client.get(
            "/reports/applications/backlog",
            headers={
                "Authorization": f"Bearer {Role.APPLICATION_WORKFLOW_REPORTING.value}"
            },
        )

        assert response.status_code == 200
        rows = parse_csv_rows(response.text)
        assert [row["Application reference"] for row in rows] == [
            first.laa_reference,
            second.laa_reference,
            third.laa_reference,
        ]
        assert [row["Potential duplicate"] for row in rows] == ["Yes"] * 3
        assert [
            row["Potential duplicate submitted application reference(s)"]
            for row in rows
        ] == [
            f"{second.laa_reference}; {third.laa_reference}",
            first.laa_reference,
            first.laa_reference,
        ]

    @pytest.mark.parametrize(
        "decision", [MeritsDecision.GRANTED, MeritsDecision.REFUSED]
    )
    @pytest.mark.parametrize("reverse_relationship", [False, True])
    def test_200_csv_excludes_decided_duplicate_relationships(
        self, session, client, decision, reverse_relationship
    ):
        pending = create_application_in_db(session)
        decided = create_application_in_db(
            session, proceeding_overrides={"merits_decision": decision}
        )
        source, target = (
            (decided, pending) if reverse_relationship else (pending, decided)
        )
        session.add(
            DuplicateApplicationRecord(
                application_id=source.application_id,
                duplicate_application_id=target.application_id,
            )
        )
        session.commit()

        response = client.get(
            "/reports/applications/backlog",
            headers={
                "Authorization": f"Bearer {Role.APPLICATION_WORKFLOW_REPORTING.value}"
            },
        )

        assert response.status_code == 200
        rows = parse_csv_rows(response.text)
        assert len(rows) == 1
        assert rows[0]["Application reference"] == pending.laa_reference
        assert rows[0]["Potential duplicate"] == "No"
        assert rows[0]["Potential duplicate submitted application reference(s)"] == ""

    def test_200_csv_retains_unrelated_pending_applications_alongside_duplicates(
        self, session, client
    ):
        first = create_application_in_db(
            session,
            laa_reference="INQ-AAA-001",
            created_at=datetime(2020, 1, 1, tzinfo=UTC),
        )
        unrelated = create_application_in_db(
            session,
            laa_reference="INQ-AAA-002",
            created_at=datetime(2021, 1, 1, tzinfo=UTC),
        )
        second = create_application_in_db(
            session,
            laa_reference="INQ-AAA-003",
            created_at=datetime(2022, 1, 1, tzinfo=UTC),
        )
        session.add(
            DuplicateApplicationRecord(
                application_id=first.application_id,
                duplicate_application_id=second.application_id,
            )
        )
        session.commit()

        response = client.get(
            "/reports/applications/backlog",
            headers={
                "Authorization": f"Bearer {Role.APPLICATION_WORKFLOW_REPORTING.value}"
            },
        )

        assert response.status_code == 200
        rows = parse_csv_rows(response.text)
        assert [row["Application reference"] for row in rows] == [
            first.laa_reference,
            unrelated.laa_reference,
            second.laa_reference,
        ]
        assert [row["Potential duplicate"] for row in rows] == ["Yes", "No", "Yes"]
        assert [
            row["Potential duplicate submitted application reference(s)"]
            for row in rows
        ] == [second.laa_reference, "", first.laa_reference]

    def test_200_csv_reports_no_duplicates_without_relationships(self, session, client):
        pending = create_application_in_db(session)

        response = client.get(
            "/reports/applications/backlog",
            headers={
                "Authorization": f"Bearer {Role.APPLICATION_WORKFLOW_REPORTING.value}"
            },
        )

        assert response.status_code == 200
        rows = parse_csv_rows(response.text)
        assert len(rows) == 1
        assert rows[0]["Application reference"] == pending.laa_reference
        assert rows[0]["Potential duplicate"] == "No"
        assert rows[0]["Potential duplicate submitted application reference(s)"] == ""


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
