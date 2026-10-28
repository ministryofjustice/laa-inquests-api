import sys
from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.adapters.history_event_repository_adapter import HistoryEventRepositoryAdapter
from app.auth.rbac import Role
from app.models.application.index import Application
from app.models.claim.enums import ClaimStatus, ClaimType
from app.models.history.enums import ActorType, HistoryEventReference
from app.models.history.index import HistoryEvent
from tests.e2e.factories import create_application_in_db, create_claim_in_db
from tests.helpers.csv_helpers import parse_csv_fieldnames, parse_csv_rows

URL = "/reports/decisions"
DECISIONS_REPORT_HEADERS = [
    "Submission type",
    "Case reference",
    "Claim reference",
    "Decision",
    "Submission date",
    "Date of decision",
    "Time of decision",
    "Who",
    "Refusal reason",
    "Justification",
]
APPLICATION_WORKFLOW_HEADERS = {
    "Authorization": f"Bearer {Role.APPLICATION_WORKFLOW_REPORTING.value}"
}
CLAIM_WORKFLOW_HEADERS = {
    "Authorization": f"Bearer {Role.CLAIM_WORKFLOW_REPORTING.value}"
}
NO_PERMISSION_HEADERS = {
    "Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}"
}

DEFAULT_PARAMS = {"from": "2025-03-01", "to": "2025-03-31"}
DECIDED_AT = datetime(2025, 3, 15, 13, 5, 9, tzinfo=UTC)
SUBMITTED_AT = datetime(2025, 3, 2, 9, 30, tzinfo=UTC)
CASEWORKER = "Jane Smith"
CASEWORKER_EMAIL = "jane.smith@example.com"


def _application(session, created_at: datetime = SUBMITTED_AT) -> Application:
    return create_application_in_db(session, created_at=created_at)


def _add_event(
    session,
    application: Application,
    reference: HistoryEventReference,
    event_data: dict | None,
    *,
    timestamp: datetime = DECIDED_AT,
    actor: str = CASEWORKER,
    actor_type: ActorType = ActorType.CASEWORKER,
    actor_email_address: str | None = CASEWORKER_EMAIL,
) -> HistoryEvent:
    event = HistoryEvent(
        event_reference=reference,
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


def _refuse(
    session, application, *, timestamp=DECIDED_AT, justification="Out of scope"
):
    return _add_event(
        session,
        application,
        HistoryEventReference.APPLICATION_ASSESSMENT_COMPLETED,
        {
            "merits_decision": "Refused",
            "refusal_reason": "NOT_IN_SCOPE",
            "refusal_justification": justification,
        },
        timestamp=timestamp,
    )


def _grant(session, application, *, timestamp=DECIDED_AT):
    return _add_event(
        session,
        application,
        HistoryEventReference.APPLICATION_ASSESSMENT_COMPLETED,
        {"merits_decision": "Granted"},
        timestamp=timestamp,
    )


def _claim(session, application, **kwargs):
    kwargs.setdefault("submission_date", SUBMITTED_AT)
    return create_claim_in_db(
        session, application_id=application.application_id, **kwargs
    )


def _get(client, params=None, headers=None):
    return client.get(
        URL,
        params=DEFAULT_PARAMS if params is None else params,
        headers=headers or APPLICATION_WORKFLOW_HEADERS,
    )


def _rows(client, params=None) -> list[dict[str, str]]:
    response = _get(client, params)
    assert response.status_code == 200
    return parse_csv_rows(response.text)


class TestGetDecisionsReport:
    """E2E tests for GET /reports/decisions."""

    def test_200_returns_csv_attachment_with_laa_filename(self, client, monkeypatch):
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
            "2026-09-01 - Report - IDDS Claim and Applications Processing - OFFICIAL-SENSITIVE - LAA Use Only.csv"
            in response.headers["content-disposition"]
        )

    def test_200_claim_workflow_role_can_download_report(self, client):
        response = _get(client, headers=CLAIM_WORKFLOW_HEADERS)

        assert response.status_code == 200

    def test_200_no_decisions_returns_header_only_csv(self, client):
        response = _get(client)

        assert response.status_code == 200
        assert parse_csv_fieldnames(response.text) == DECISIONS_REPORT_HEADERS
        assert parse_csv_rows(response.text) == []

    def test_200_application_refusal_row_contains_expected_values(
        self, session, client
    ):
        application = _application(session)
        _refuse(session, application)

        rows = _rows(client)

        assert rows == [
            {
                "Submission type": "Application",
                "Case reference": application.laa_reference,
                "Claim reference": "",
                "Decision": "Refused",
                "Submission date": "02-03-2025",
                "Date of decision": "15-03-2025",
                "Time of decision": "13:05:09",
                "Who": CASEWORKER_EMAIL,
                "Refusal reason": "Not in scope",
                "Justification": "Out of scope",
            }
        ]

    def test_200_application_grant_row_has_blank_refusal_fields(self, session, client):
        application = _application(session)
        _grant(session, application)

        rows = _rows(client)

        assert len(rows) == 1
        assert rows[0]["Submission type"] == "Application"
        assert rows[0]["Decision"] == "Granted"
        assert rows[0]["Refusal reason"] == ""
        assert rows[0]["Justification"] == ""
        assert rows[0]["Claim reference"] == ""

    def test_200_claim_pay_in_full_row_contains_expected_values(self, session, client):
        application = _application(session)
        claim = _claim(session, application, status=ClaimStatus.PAY_IN_FULL)
        _add_event(
            session,
            application,
            HistoryEventReference.CLAIM_ASSESSMENT_COMPLETED,
            {
                "claim_type": ClaimType.FINAL_BILL.value,
                "claim_reference": claim.claim_reference,
                "claim_decision": ClaimStatus.PAY_IN_FULL.value,
            },
        )

        rows = _rows(client)

        assert rows == [
            {
                "Submission type": "Claim",
                "Case reference": application.laa_reference,
                "Claim reference": claim.claim_reference,
                "Decision": "Pay in full",
                "Submission date": "02-03-2025",
                "Date of decision": "15-03-2025",
                "Time of decision": "13:05:09",
                "Who": CASEWORKER_EMAIL,
                "Refusal reason": "",
                "Justification": "",
            }
        ]

    def test_200_claim_manual_rejection_row_includes_justification(
        self, session, client
    ):
        application = _application(session)
        claim = _claim(session, application, status=ClaimStatus.REJECTED)
        _add_event(
            session,
            application,
            HistoryEventReference.CLAIM_ASSESSMENT_COMPLETED,
            {
                "claim_type": ClaimType.FINAL_BILL.value,
                "claim_reference": claim.claim_reference,
                "claim_decision": ClaimStatus.REJECTED.value,
                "decision_justification": "Costs exceed the limit",
            },
        )

        rows = _rows(client)

        assert rows[0]["Decision"] == "Rejected"
        assert rows[0]["Justification"] == "Costs exceed the limit"
        assert rows[0]["Refusal reason"] == ""

    def test_200_auto_approved_poa_claim_is_pay_in_full_by_system(
        self, session, client
    ):
        application = _application(session)
        claim = _claim(
            session,
            application,
            status=ClaimStatus.PAY_IN_FULL,
            claim_type=ClaimType.PAYMENT_ON_ACCOUNT,
        )
        _add_event(
            session,
            application,
            HistoryEventReference.POA_AUTO_APPROVED,
            {"claim_reference": claim.claim_reference},
            actor=ActorType.SYSTEM.value,
            actor_type=ActorType.SYSTEM,
        )

        rows = _rows(client)

        assert rows[0]["Submission type"] == "Claim"
        assert rows[0]["Claim reference"] == claim.claim_reference
        assert rows[0]["Decision"] == "Pay in full"
        assert rows[0]["Who"] == "System"

    def test_200_auto_rejected_poa_claim_is_rejected_by_system(self, session, client):
        application = _application(session)
        claim = _claim(
            session,
            application,
            status=ClaimStatus.REJECTED,
            claim_type=ClaimType.PAYMENT_ON_ACCOUNT,
        )
        _add_event(
            session,
            application,
            HistoryEventReference.POA_AUTO_REJECTED,
            {"claim_reference": claim.claim_reference},
            actor=ActorType.SYSTEM.value,
            actor_type=ActorType.SYSTEM,
        )

        rows = _rows(client)

        assert rows[0]["Decision"] == "Rejected"
        assert rows[0]["Who"] == "System"
        assert rows[0]["Justification"] == ""

    def test_200_rows_are_ordered_by_decision_time_oldest_first(self, session, client):
        newest = _application(session)
        oldest = _application(session)
        middle = _application(session)
        _grant(session, newest, timestamp=datetime(2025, 3, 20, 10, tzinfo=UTC))
        _grant(session, oldest, timestamp=datetime(2025, 3, 5, 10, tzinfo=UTC))
        _grant(session, middle, timestamp=datetime(2025, 3, 10, 10, tzinfo=UTC))

        rows = _rows(client)

        assert [row["Case reference"] for row in rows] == [
            oldest.laa_reference,
            middle.laa_reference,
            newest.laa_reference,
        ]

    def test_200_only_decisions_inside_inclusive_date_range_are_returned(
        self, session, client
    ):
        applications = {
            name: _application(session)
            for name in ("before", "first_second", "last_second", "after")
        }
        _grant(
            session,
            applications["before"],
            timestamp=datetime(2025, 2, 28, 23, 59, 59, tzinfo=UTC),
        )
        _grant(
            session,
            applications["first_second"],
            timestamp=datetime(2025, 3, 1, 0, 0, 0, tzinfo=UTC),
        )
        _grant(
            session,
            applications["last_second"],
            timestamp=datetime(2025, 3, 31, 23, 59, 59, tzinfo=UTC),
        )
        _grant(
            session,
            applications["after"],
            timestamp=datetime(2025, 4, 1, 0, 0, 0, tzinfo=UTC),
        )

        rows = _rows(client)

        assert [row["Case reference"] for row in rows] == [
            applications["first_second"].laa_reference,
            applications["last_second"].laa_reference,
        ]

    def test_200_non_decision_events_are_excluded(self, session, client):
        application = _application(session)
        for reference in (
            HistoryEventReference.APPLICATION_SUBMITTED,
            HistoryEventReference.CASE_NOTE_ADDED,
            HistoryEventReference.APPLICATION_GRANTED_EMAIL,
            HistoryEventReference.CLAIM_SUBMITTED,
            HistoryEventReference.CLAIM_REJECTED_EMAIL,
        ):
            _add_event(session, application, reference, None)

        assert _rows(client) == []

    def test_200_range_ending_same_day_next_month_is_allowed(self, client):
        response = _get(client, {"from": "2025-03-01", "to": "2025-04-01"})

        assert response.status_code == 200

    def test_200_returns_2000_records_without_truncation(self, session, client):
        application = _application(session)
        session.add_all(
            HistoryEvent(
                event_reference=HistoryEventReference.APPLICATION_ASSESSMENT_COMPLETED,
                timestamp=datetime(2025, 3, 10, 10, 0, tzinfo=UTC),
                actor=CASEWORKER,
                actor_type=ActorType.CASEWORKER,
                actor_email_address=CASEWORKER_EMAIL,
                event_data={"merits_decision": "Granted"},
                application_id=application.application_id,
            )
            for _ in range(2000)
        )
        session.commit()

        assert len(_rows(client)) == 2000

    @pytest.mark.parametrize("value", ["=SUM(A1:A2)", "+1", "-1", "@cmd"])
    def test_200_formula_justification_is_neutralised(self, session, client, value):
        application = _application(session)
        _refuse(session, application, justification=value)

        rows = _rows(client)

        assert rows[0]["Justification"] == f"'{value}"

    def test_200_caseworker_decision_who_is_the_stored_email_address(
        self, session, client
    ):
        _refuse(session, _application(session))

        assert _rows(client)[0]["Who"] == CASEWORKER_EMAIL

    def test_200_claim_decision_who_is_the_stored_email_address(self, session, client):
        application = _application(session)
        claim = _claim(session, application, status=ClaimStatus.PAY_IN_FULL)
        _add_event(
            session,
            application,
            HistoryEventReference.CLAIM_ASSESSMENT_COMPLETED,
            {
                "claim_reference": claim.claim_reference,
                "claim_decision": ClaimStatus.PAY_IN_FULL.value,
            },
        )

        assert _rows(client)[0]["Who"] == CASEWORKER_EMAIL

    @pytest.mark.parametrize("missing_email", [None, ""])
    def test_200_caseworker_decision_without_email_falls_back_to_actor_name(
        self, session, client, missing_email
    ):
        _add_event(
            session,
            _application(session),
            HistoryEventReference.APPLICATION_ASSESSMENT_COMPLETED,
            {"merits_decision": "Granted"},
            actor_email_address=missing_email,
        )

        assert _rows(client)[0]["Who"] == CASEWORKER

    @pytest.mark.parametrize(
        "reference",
        [
            HistoryEventReference.POA_AUTO_APPROVED,
            HistoryEventReference.POA_AUTO_REJECTED,
        ],
    )
    def test_200_system_decision_who_is_system_without_an_email(
        self, session, client, reference
    ):
        application = _application(session)
        claim = _claim(session, application, claim_type=ClaimType.PAYMENT_ON_ACCOUNT)
        _add_event(
            session,
            application,
            reference,
            {"claim_reference": claim.claim_reference},
            actor=ActorType.SYSTEM.value,
            actor_type=ActorType.SYSTEM,
            actor_email_address=None,
        )

        assert _rows(client)[0]["Who"] == "System"

    def test_200_who_is_the_email_not_the_display_name_when_an_email_is_stored(
        self, session, client
    ):
        _refuse(session, _application(session))

        response = _get(client)

        assert response.status_code == 200
        assert CASEWORKER_EMAIL in response.text
        assert CASEWORKER not in response.text

    def test_200_formula_like_actor_name_fallback_is_neutralised(self, session, client):
        _add_event(
            session,
            _application(session),
            HistoryEventReference.APPLICATION_ASSESSMENT_COMPLETED,
            {"merits_decision": "Granted"},
            actor="=Jane",
            actor_email_address=None,
        )

        assert _rows(client)[0]["Who"] == "'=Jane"

    @pytest.mark.parametrize("prefix", ["=", "+", "-", "@"])
    def test_200_formula_like_email_is_neutralised(self, session, client, prefix):
        email = f"{prefix}a@example.com"
        _add_event(
            session,
            _application(session),
            HistoryEventReference.APPLICATION_ASSESSMENT_COMPLETED,
            {"merits_decision": "Granted"},
            actor_email_address=email,
        )

        assert _rows(client)[0]["Who"] == f"'{email}"

    def test_422_from_date_after_to_date(self, client):
        response = _get(client, {"from": "2025-03-31", "to": "2025-03-01"})

        assert response.status_code == 422

    def test_422_range_longer_than_one_calendar_month(self, client):
        response = _get(client, {"from": "2025-03-01", "to": "2025-04-02"})

        assert response.status_code == 422

    @pytest.mark.parametrize(
        "params", [{}, {"from": "2025-03-01"}, {"to": "2025-03-31"}]
    )
    def test_422_missing_date_parameters(self, client, params):
        assert _get(client, params).status_code == 422

    def test_422_invalid_date_format(self, client):
        response = _get(client, {"from": "01-03-2025", "to": "31-03-2025"})

        assert response.status_code == 422

    def test_500_unknown_claim_decision_returns_no_csv(self, session, client):
        application = _application(session)
        claim = _claim(session, application)
        _grant(session, application)
        _add_event(
            session,
            application,
            HistoryEventReference.CLAIM_ASSESSMENT_COMPLETED,
            {
                "claim_reference": claim.claim_reference,
                "claim_decision": "SOMETHING_ELSE",
            },
        )

        response = _get(client)

        assert response.status_code == 500
        assert "content-disposition" not in response.headers
        assert "Submission type" not in response.text

    def test_500_claim_event_for_unknown_claim_returns_no_csv(self, session, client):
        application = _application(session)
        _add_event(
            session,
            application,
            HistoryEventReference.POA_AUTO_APPROVED,
            {"claim_reference": "INQC-NOPE-NOPE"},
        )

        response = _get(client)

        assert response.status_code == 500
        assert "content-disposition" not in response.headers

    def test_500_database_error_returns_no_csv(self, client, monkeypatch):
        def fail(*args, **kwargs):
            raise SQLAlchemyError("db down")

        monkeypatch.setattr(
            HistoryEventRepositoryAdapter, "get_decisions_report_records", fail
        )

        response = _get(client)

        assert response.status_code == 500
        assert "content-disposition" not in response.headers
        assert "db down" not in response.text

    def test_401_without_token(self, client):
        response = client.get(URL, params=DEFAULT_PARAMS)

        assert response.status_code == 401

    def test_403_role_without_report_permission(self, client):
        response = _get(client, headers=NO_PERMISSION_HEADERS)

        assert response.status_code == 403
