import sys
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from freezegun import freeze_time
from sqlmodel import Session, select

from app import api
from app.auth.rbac import Role
from app.models.application.index import Application
from app.models.audit.enums import ApplicationPageType, ReportType
from app.models.audit.index import ReportAudit, ViewApplicationPagesAudit
from app.models.history.enums import ActorType, HistoryEventReference
from app.models.history.index import HistoryEvent
from app.routers.applications import get_provider_details_port
from app.use_cases.exceptions import ProviderDetailsRetrievalError
from tests.e2e.factories import create_application_in_db
from tests.helpers.csv_helpers import parse_csv_fieldnames, parse_csv_rows

AUDIT_TRAIL_REPORT_HEADERS = [
    "Event title",
    "Event description",
    "Event date",
    "Event time",
    "Username",
    "Case reference",
    "Firm name",
    "Office account number",
]

URL = "/reports/audit-trail"
ASSURANCE_HEADERS = {"Authorization": f"Bearer {Role.ASSURANCE.value}"}

IN_RANGE = datetime(2025, 3, 15, 12, 0, tzinfo=UTC)
# The longest permitted range: 30 days inclusive.
DEFAULT_PARAMS = {"from": "2025-03-02", "to": "2025-03-31"}

SEEDED_LAA_REFERENCE = "INQ-123-456"
SEEDED_FIRM_NAME = "Firm 0A123B"
SEEDED_OFFICE_ID = "0U651L"
CLAIM_REFERENCE = "INQC-AAAA-BBBB"


def _application(session: Session) -> Application:
    return session.exec(select(Application)).first()


def _other_provider_application(session: Session) -> Application:
    return create_application_in_db(
        session,
        provider_overrides={"firm_code": "0B999C", "office_id": "0X111Z"},
        laa_reference="INQ-777-888",
    )


def _add_history_event(
    session: Session,
    application: Application,
    *,
    event_reference: HistoryEventReference = HistoryEventReference.APPLICATION_SUBMITTED,
    timestamp: datetime = IN_RANGE,
    actor: str = "provider@example.com",
    actor_type: ActorType = ActorType.PROVIDER,
    actor_email_address: str | None = None,
    event_data: dict | None = None,
) -> HistoryEvent:
    event = HistoryEvent(
        event_reference=event_reference,
        timestamp=timestamp,
        actor=actor,
        actor_type=actor_type,
        actor_email_address=actor_email_address,
        event_data=event_data,
        application_id=application.application_id,
    )
    session.add(event)
    session.commit()
    return event


def _add_view_event(
    session: Session,
    *,
    timestamp: datetime = IN_RANGE,
    laa_reference: str = SEEDED_LAA_REFERENCE,
    page: ApplicationPageType = ApplicationPageType.OVERVIEW,
    user_email_address: str = "caseworker@example.com",
) -> ViewApplicationPagesAudit:
    event = ViewApplicationPagesAudit(
        timestamp=timestamp,
        user_email_address=user_email_address,
        laa_reference=laa_reference,
        page=page,
    )
    session.add(event)
    session.commit()
    return event


def _add_report_event(
    session: Session,
    *,
    timestamp: datetime = IN_RANGE,
    report_type: ReportType = ReportType.CLAIMS_BACKLOG,
    user_email_address: str = "assurance@example.com",
    parameters: dict | None = None,
) -> ReportAudit:
    event = ReportAudit(
        timestamp=timestamp,
        user_email_address=user_email_address,
        report_type=report_type,
        parameters=parameters,
    )
    session.add(event)
    session.commit()
    return event


def _get(client, params: dict | None = None, headers: dict | None = None):
    return client.get(
        URL,
        params=DEFAULT_PARAMS if params is None else params,
        headers=ASSURANCE_HEADERS if headers is None else headers,
    )


def _rows(client, params: dict | None = None) -> list[dict[str, str]]:
    response = _get(client, params)
    assert response.status_code == 200
    return parse_csv_rows(response.text)


def _single_row(client) -> dict[str, str]:
    rows = _rows(client)
    assert len(rows) == 1
    return rows[0]


def _override_provider_details_port(mock_port: MagicMock) -> None:
    api.dependency_overrides[get_provider_details_port] = lambda: mock_port


def _assert_no_csv_produced(response) -> None:
    assert response.status_code == 500
    assert "text/csv" not in response.headers["content-type"]
    assert "content-disposition" not in response.headers
    assert "Event title" not in response.text


class TestGetAuditTrailReport:
    """E2E tests for GET /reports/audit-trail."""

    def test_200_returns_csv_attachment_with_expected_headers(
        self, client, monkeypatch
    ):
        class FixedDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime(2026, 9, 1, 16, 45, 1, tzinfo=tz)

        monkeypatch.setattr(
            sys.modules["app.routers.reports"], "datetime", FixedDatetime
        )
        response = _get(client)
        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        assert "attachment" in response.headers["content-disposition"]
        assert (
            "2026-09-01-164501 - Report - IDDS User Audit Trail - OFFICIAL-SENSITIVE - LAA Use Only.csv"
            in response.headers["content-disposition"]
        )
        assert parse_csv_fieldnames(response.text) == AUDIT_TRAIL_REPORT_HEADERS

    def test_200_provider_history_event_row_contains_expected_values(
        self, session, client
    ):
        application = _application(session)
        _add_history_event(
            session,
            application,
            event_reference=HistoryEventReference.APPLICATION_SUBMITTED,
            actor="provider@example.com",
            actor_type=ActorType.PROVIDER,
        )

        row = _single_row(client)

        assert row == {
            "Event title": "Application submitted",
            "Event description": "Application received",
            "Event date": "2025-03-15",
            "Event time": "12:00:00",
            "Username": "provider@example.com",
            "Case reference": SEEDED_LAA_REFERENCE,
            "Firm name": SEEDED_FIRM_NAME,
            "Office account number": SEEDED_OFFICE_ID,
        }

    def test_200_caseworker_history_event_row_uses_email_and_has_no_firm_details(
        self, session, client
    ):
        _add_history_event(
            session,
            _application(session),
            event_reference=HistoryEventReference.APPLICATION_ASSESSMENT_COMPLETED,
            actor="Test Name",
            actor_type=ActorType.CASEWORKER,
            actor_email_address="caseworker@example.com",
            event_data={"merits_decision": "Granted"},
        )

        row = _single_row(client)

        assert row["Username"] == "caseworker@example.com"
        assert row["Case reference"] == SEEDED_LAA_REFERENCE
        assert row["Firm name"] == ""
        assert row["Office account number"] == ""

    def test_200_historical_caseworker_event_without_email_shows_the_stored_name(
        self, session, client
    ):
        _add_history_event(
            session,
            _application(session),
            event_reference=HistoryEventReference.APPLICATION_ASSESSMENT_COMPLETED,
            actor="Test Name",
            actor_type=ActorType.CASEWORKER,
            actor_email_address=None,
            event_data={"merits_decision": "Granted"},
        )

        row = _single_row(client)

        assert row["Username"] == "Test Name"

    def test_200_system_history_event_row_has_system_username_and_no_firm_details(
        self, session, client
    ):
        _add_history_event(
            session,
            _application(session),
            event_reference=HistoryEventReference.APPLICATION_SUBMISSION_CONFIRMATION,
            actor="System",
            actor_type=ActorType.SYSTEM,
            event_data={"recipient": "provider@example.com", "channel": "email"},
        )

        row = _single_row(client)

        assert row["Username"] == "System"
        assert row["Case reference"] == SEEDED_LAA_REFERENCE
        assert row["Firm name"] == ""
        assert row["Office account number"] == ""

    def test_200_certificate_created_reports_the_stored_caseworker_actor(
        self, session, client
    ):
        _add_history_event(
            session,
            _application(session),
            event_reference=HistoryEventReference.CERTIFICATE_CREATED,
            actor="Test Name",
            actor_type=ActorType.CASEWORKER,
            actor_email_address="caseworker@example.com",
            event_data={"laa_reference": SEEDED_LAA_REFERENCE},
        )

        row = _single_row(client)

        assert row["Event title"] == "Certificate created"
        assert row["Username"] == "caseworker@example.com"

    @pytest.mark.parametrize(
        ("event_reference", "event_data", "title", "description"),
        [
            (
                HistoryEventReference.CASE_NOTE_ADDED,
                {"note_text": "Called the provider"},
                "Case note added",
                "Caseworker note added\nCalled the provider",
            ),
            (
                HistoryEventReference.APPLICATION_SUBMITTED,
                None,
                "Application submitted",
                "Application received",
            ),
            (
                HistoryEventReference.APPLICATION_ASSESSMENT_COMPLETED,
                {"merits_decision": "Granted"},
                "Application assessment complete",
                "Application granted",
            ),
            (
                HistoryEventReference.APPLICATION_ASSESSMENT_COMPLETED,
                {
                    "merits_decision": "Refused",
                    "refusal_reason": "NOT_IN_SCOPE",
                    "refusal_justification": "Outside the scope of the scheme",
                },
                "Application assessment complete",
                "Application refused\nNot in scope\nOutside the scope of the scheme",
            ),
            (
                HistoryEventReference.CERTIFICATE_CREATED,
                {"laa_reference": SEEDED_LAA_REFERENCE},
                "Certificate created",
                "Certificate created",
            ),
            (
                HistoryEventReference.INTERESTED_PARTY_UPDATED,
                {
                    "old_public_bodies": ["DEPARTMENT_FOR_TRANSPORT"],
                    "new_public_bodies": [
                        "DEPARTMENT_FOR_TRANSPORT",
                        "DEPARTMENT_OF_HEALTH_AND_SOCIAL_CARE",
                    ],
                },
                "Interested party updated",
                (
                    "Interested parties updated from DEPARTMENT_FOR_TRANSPORT to "
                    "DEPARTMENT_FOR_TRANSPORT, DEPARTMENT_OF_HEALTH_AND_SOCIAL_CARE"
                ),
            ),
            (
                HistoryEventReference.CLAIM_SUBMITTED,
                {"claim_type": "FINAL_BILL", "claim_reference": CLAIM_REFERENCE},
                "Claim submitted",
                f"Final bill claim received: {CLAIM_REFERENCE}",
            ),
            (
                HistoryEventReference.CLAIM_ASSESSMENT_COMPLETED,
                {
                    "claim_type": "FINAL_BILL",
                    "claim_reference": CLAIM_REFERENCE,
                    "claim_decision": "PAY_IN_FULL",
                },
                "Claim assessment complete",
                f"Final bill claim pay in full: {CLAIM_REFERENCE}",
            ),
            (
                HistoryEventReference.CLAIM_ASSESSMENT_COMPLETED,
                {
                    "claim_type": "FINAL_BILL",
                    "claim_reference": CLAIM_REFERENCE,
                    "claim_decision": "REJECTED",
                    "decision_justification": "Evidence is missing",
                },
                "Claim assessment complete",
                "Final bill claim rejected\nEvidence is missing",
            ),
            (
                HistoryEventReference.POA_AUTO_APPROVED,
                {"claim_reference": CLAIM_REFERENCE},
                "POA auto-approved",
                f"POA claim {CLAIM_REFERENCE} auto-approved",
            ),
            (
                HistoryEventReference.POA_AUTO_REJECTED,
                {"claim_reference": CLAIM_REFERENCE},
                "POA auto-rejected",
                f"POA claim {CLAIM_REFERENCE} auto-rejected",
            ),
            (
                HistoryEventReference.APPLICATION_SUBMISSION_CONFIRMATION,
                None,
                "Application submission confirmation",
                "Application submission confirmation sent",
            ),
            (
                HistoryEventReference.APPLICATION_GRANTED_EMAIL,
                None,
                "Application granted (Email)",
                "Application granted email sent",
            ),
            (
                HistoryEventReference.APPLICATION_GRANTED_LETTER,
                None,
                "Application granted (Letter)",
                "Application granted letter sent",
            ),
            (
                HistoryEventReference.APPLICATION_REFUSED,
                None,
                "Application refused",
                "Application refused email sent",
            ),
            (
                HistoryEventReference.CLAIM_SUBMISSION_CONFIRMATION,
                None,
                "Claim submission confirmation",
                "Claim submission confirmation sent",
            ),
            (
                HistoryEventReference.CLAIM_APPROVED_EMAIL,
                None,
                "Claim approved",
                "Claim approved email sent",
            ),
            (
                HistoryEventReference.CLAIM_REJECTED_EMAIL,
                None,
                "Claim Rejected",
                "Claim rejected email sent",
            ),
        ],
    )
    def test_200_history_event_title_and_description_match_the_event_catalogue(
        self, session, client, event_reference, event_data, title, description
    ):
        _add_history_event(
            session,
            _application(session),
            event_reference=event_reference,
            actor="System",
            actor_type=ActorType.SYSTEM,
            event_data=event_data,
        )

        row = _single_row(client)

        assert row["Event title"] == title
        assert row["Event description"] == description

    def test_200_application_overview_view_row_contains_expected_values(
        self, session, client
    ):
        _add_view_event(
            session,
            page=ApplicationPageType.OVERVIEW,
            user_email_address="caseworker@example.com",
        )

        row = _single_row(client)

        assert row == {
            "Event title": "Application viewed",
            "Event description": "Application viewed",
            "Event date": "2025-03-15",
            "Event time": "12:00:00",
            "Username": "caseworker@example.com",
            "Case reference": SEEDED_LAA_REFERENCE,
            "Firm name": "",
            "Office account number": "",
        }

    def test_200_certificate_view_row_is_reported_as_certificate_viewed(
        self, session, client
    ):
        _add_view_event(session, page=ApplicationPageType.CERTIFICATE)

        row = _single_row(client)

        assert row["Event title"] == "Certificate viewed"
        assert row["Event description"] == "Certificate viewed"
        assert row["Case reference"] == SEEDED_LAA_REFERENCE

    def test_200_view_row_for_an_unknown_case_is_still_reported(self, session, client):
        _add_view_event(session, laa_reference="INQ-999-999")

        row = _single_row(client)

        assert row["Event title"] == "Application viewed"
        assert row["Case reference"] == "INQ-999-999"

    @pytest.mark.parametrize(
        ("report_type", "report_name"),
        [
            (ReportType.CLAIMS_BACKLOG, "Claims Backlog"),
            (ReportType.APPLICATIONS_BACKLOG, "Applications Backlog"),
            (ReportType.PAYMENT_EXTRACT, "Payment Extract"),
        ],
    )
    def test_200_report_download_row_contains_expected_values(
        self, session, client, report_type, report_name
    ):
        _add_report_event(
            session,
            report_type=report_type,
            user_email_address="assurance@example.com",
        )

        row = _single_row(client)

        assert row == {
            "Event title": "Report downloaded",
            "Event description": f"{report_name} downloaded",
            "Event date": "2025-03-15",
            "Event time": "12:00:00",
            "Username": "assurance@example.com",
            "Case reference": "",
            "Firm name": "",
            "Office account number": "",
        }

    def test_200_includes_events_from_all_sources_across_all_cases_ordered_by_time(
        self, session, client
    ):
        seeded = _application(session)
        other = _other_provider_application(session)
        _add_view_event(session, timestamp=datetime(2025, 3, 15, 10, 0, tzinfo=UTC))
        _add_report_event(session, timestamp=datetime(2025, 3, 15, 11, 30, tzinfo=UTC))
        _add_history_event(
            session,
            other,
            event_reference=HistoryEventReference.APPLICATION_SUBMITTED,
            timestamp=datetime(2025, 3, 15, 9, 0, tzinfo=UTC),
        )
        _add_view_event(
            session,
            timestamp=datetime(2025, 3, 15, 10, 30, tzinfo=UTC),
            laa_reference=other.laa_reference,
            page=ApplicationPageType.CERTIFICATE,
        )
        _add_history_event(
            session,
            seeded,
            event_reference=HistoryEventReference.CASE_NOTE_ADDED,
            timestamp=datetime(2025, 3, 15, 9, 30, tzinfo=UTC),
            actor="Test Name",
            actor_type=ActorType.CASEWORKER,
            actor_email_address="caseworker@example.com",
            event_data={"note_text": "A note"},
        )

        rows = _rows(client)

        assert [
            (row["Event time"], row["Event title"], row["Case reference"])
            for row in rows
        ] == [
            ("09:00:00", "Application submitted", other.laa_reference),
            ("09:30:00", "Case note added", SEEDED_LAA_REFERENCE),
            ("10:00:00", "Application viewed", SEEDED_LAA_REFERENCE),
            ("10:30:00", "Certificate viewed", other.laa_reference),
            ("11:30:00", "Report downloaded", ""),
        ]

    def test_200_firm_details_come_from_the_provider_of_each_case(
        self, session, client
    ):
        other = _other_provider_application(session)
        _add_history_event(
            session,
            _application(session),
            timestamp=datetime(2025, 3, 15, 9, 0, tzinfo=UTC),
        )
        _add_history_event(
            session, other, timestamp=datetime(2025, 3, 15, 10, 0, tzinfo=UTC)
        )

        rows = _rows(client)

        assert [(row["Firm name"], row["Office account number"]) for row in rows] == [
            (SEEDED_FIRM_NAME, SEEDED_OFFICE_ID),
            ("Firm 0B999C", "0X111Z"),
        ]

    @pytest.mark.parametrize(
        ("add_event", "event_title"),
        [
            pytest.param(
                lambda session, timestamp: _add_history_event(
                    session, _application(session), timestamp=timestamp
                ),
                "Application submitted",
                id="history_event",
            ),
            pytest.param(
                lambda session, timestamp: _add_view_event(
                    session, timestamp=timestamp
                ),
                "Application viewed",
                id="application_view",
            ),
            pytest.param(
                lambda session, timestamp: _add_report_event(
                    session, timestamp=timestamp
                ),
                "Report downloaded",
                id="report_download",
            ),
        ],
    )
    def test_200_filters_on_event_time_with_inclusive_utc_days(
        self, session, client, add_event, event_title
    ):
        for timestamp in (
            datetime(2025, 3, 1, 23, 59, 59, tzinfo=UTC),
            datetime(2025, 3, 2, 0, 0, 0, tzinfo=UTC),
            datetime(2025, 3, 31, 23, 59, 59, tzinfo=UTC),
            datetime(2025, 4, 1, 0, 0, 0, tzinfo=UTC),
        ):
            add_event(session, timestamp)

        rows = _rows(client)

        assert [(row["Event date"], row["Event time"]) for row in rows] == [
            ("2025-03-02", "00:00:00"),
            ("2025-03-31", "23:59:59"),
        ]
        assert {row["Event title"] for row in rows} == {event_title}

    def test_200_returns_headers_only_when_no_events_in_range(self, session, client):
        _add_history_event(
            session,
            _application(session),
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
        )
        _add_view_event(session, timestamp=datetime(2024, 1, 1, tzinfo=UTC))
        _add_report_event(session, timestamp=datetime(2024, 1, 1, tzinfo=UTC))

        response = _get(client)

        assert response.status_code == 200
        assert parse_csv_fieldnames(response.text) == AUDIT_TRAIL_REPORT_HEADERS
        assert parse_csv_rows(response.text) == []

    @pytest.mark.parametrize("character", ["=", "+", "-", "@"])
    def test_200_prefixes_cells_that_could_be_read_as_formulas(
        self, session, client, character
    ):
        _add_history_event(
            session,
            _application(session),
            actor=f"{character}cmd@example.com",
            actor_type=ActorType.PROVIDER,
        )

        row = _single_row(client)

        assert row["Username"] == f"'{character}cmd@example.com"

    @freeze_time("2026-09-01 16:45:01")
    def test_200_records_the_request_as_an_audit_trail_report_download(
        self, session, client
    ):
        params = {"from": "2026-09-01", "to": "2026-09-01"}

        response = _get(client, params)

        assert response.status_code == 200
        audit_entry = session.exec(select(ReportAudit)).one()
        assert audit_entry.report_type == ReportType.AUDIT_TRAIL
        assert audit_entry.user_email_address == "test@example.com"
        assert audit_entry.parameters == params

    @freeze_time("2026-09-01 16:45:01")
    def test_200_includes_the_request_itself_in_the_extract(self, client):
        params = {"from": "2026-09-01", "to": "2026-09-01"}

        row = _rows(client, params)[0]

        assert row == {
            "Event title": "Report downloaded",
            "Event description": "User Audit Trail downloaded",
            "Event date": "2026-09-01",
            "Event time": "16:45:01",
            "Username": "test@example.com",
            "Case reference": "",
            "Firm name": "",
            "Office account number": "",
        }

    @freeze_time("2026-09-01 16:45:01")
    def test_200_includes_audit_rows_for_denied_attempts(self, client):
        params = {"from": "2026-09-01", "to": "2026-09-01"}
        denied = _get(
            client,
            params,
            headers={"Authorization": f"Bearer {Role.APPLICATIONS_CASEWORKER.value}"},
        )
        assert denied.status_code == 403

        rows = _rows(client, params)

        assert [row["Event title"] for row in rows] == ["Report downloaded"] * 2
        assert {row["Event description"] for row in rows} == {
            "User Audit Trail downloaded"
        }

    @pytest.mark.parametrize(
        "params",
        [
            {"to": "2025-03-31"},
            {"from": "2025-03-01"},
            {},
        ],
    )
    def test_422_when_date_params_missing(self, client, params):
        response = _get(client, params)

        assert response.status_code == 422

    @pytest.mark.parametrize(
        "params",
        [
            {"from": "not-a-date", "to": "2025-03-31"},
            {"from": "2025-03-01", "to": "31/03/2025"},
        ],
    )
    def test_422_when_date_params_invalid(self, client, params):
        response = _get(client, params)

        assert response.status_code == 422

    def test_422_when_from_is_after_to(self, client):
        response = _get(client, {"from": "2025-04-01", "to": "2025-03-31"})

        assert response.status_code == 422

    def test_422_when_date_range_exceeds_30_days(self, client):
        response = _get(client, {"from": "2025-03-01", "to": "2025-03-31"})

        assert response.status_code == 422
        assert "30 days" in response.json()["detail"]

    def test_200_when_date_range_is_exactly_30_days(self, client):
        response = _get(client, {"from": "2025-03-01", "to": "2025-03-30"})

        assert response.status_code == 200

    def test_500_and_no_csv_when_firm_name_missing(self, session, client):
        _add_history_event(session, _application(session))
        mock_port = MagicMock()
        mock_port.get_firms_by_ids.return_value = []
        _override_provider_details_port(mock_port)

        response = _get(client)

        _assert_no_csv_produced(response)

    def test_500_and_no_csv_when_only_some_firm_names_are_found(self, session, client):
        _add_history_event(session, _application(session))
        _add_history_event(session, _other_provider_application(session))
        mock_port = MagicMock()
        mock_port.get_firms_by_ids.side_effect = lambda firm_ids: [
            {"firmNumber": "0A123B", "firmName": SEEDED_FIRM_NAME}
        ]
        _override_provider_details_port(mock_port)

        response = _get(client)

        _assert_no_csv_produced(response)

    def test_500_and_no_csv_when_provider_details_retrieval_fails(
        self, session, client
    ):
        _add_history_event(session, _application(session))
        mock_port = MagicMock()
        mock_port.get_firms_by_ids.side_effect = ProviderDetailsRetrievalError()
        _override_provider_details_port(mock_port)

        response = _get(client)

        _assert_no_csv_produced(response)


class TestGetAuditTrailReportAuth:
    """Authentication and authorisation tests for GET /reports/audit-trail."""

    # The audit trail shares the MI report permission until it is amended separately.
    def test_200_returns_ok_for_the_assurance_role(self, client):
        response = _get(client)

        assert response.status_code == 200

    @pytest.mark.parametrize(
        "role",
        [role for role in Role if role != Role.ASSURANCE],
        ids=lambda r: r.name,
    )
    def test_403_for_roles_without_mi_report_permission(self, client, role):
        response = _get(client, headers={"Authorization": f"Bearer {role.value}"})

        assert response.status_code == 403

    def test_401_without_credentials(self, client):
        response = client.get(URL, params=DEFAULT_PARAMS)

        assert response.status_code == 401

    def test_401_with_invalid_token(self, client):
        response = _get(client, headers={"Authorization": "Bearer not-a-valid-token"})

        assert response.status_code == 401
