import sys
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from sqlmodel import Session, select

from app import api
from app.auth.rbac import Role
from app.models.application.enums import MeritsDecision, ProceedingId, PublicBodyId
from app.models.application.index import (
    Application,
    ApplicationProceeding,
    ApplicationPublicBody,
    Proceeding,
)
from app.models.claim.enums import ClaimStatus, ClaimType
from app.routers.reports import get_cost_limit_forecast_report_port
from tests.e2e.factories import create_application_in_db, create_claim_in_db
from tests.helpers.csv_helpers import parse_csv_fieldnames, parse_csv_rows

COST_LIMIT_FORECAST_REPORT_HEADERS = [
    "Case Reference",
    "Public Body(ies)",
    "Cost Limit",
    "Total Remaining Cost Limit Value",
    "Certificate Effective Date",
]

URL = "/reports/cost-limit-forecast"
FINANCE_HEADERS = {"Authorization": f"Bearer {Role.FINANCE.value}"}
FORECAST_ROLES = [Role.FINANCE, Role.POLICY]

EFFECTIVE_DATE = date(2019, 3, 15)
DEFAULT_PARAMS = {"from": "2019-01-01", "to": "2019-12-31"}
PAST_DATE = date(2019, 6, 1)
FAR_FUTURE_DATE = date(2099, 1, 1)


def _application(session: Session) -> Application:
    return session.exec(select(Application)).first()


def _set_certificate(
    session: Session,
    application: Application,
    *,
    start: date | None = EFFECTIVE_DATE,
    end: date | None = None,
    merits_decision: MeritsDecision = MeritsDecision.GRANTED,
    status: str = "LIVE",
) -> Application:
    application.status = status
    application.proceeding.merits_decision = merits_decision
    application.proceeding.certificate_start_date = start
    application.proceeding.certificate_end_date = end
    session.add(application)
    session.commit()
    session.refresh(application)
    return application


def _live_application(session: Session, **certificate_fields) -> Application:
    return _set_certificate(session, _application(session), **certificate_fields)


def _another_application(
    session: Session,
    laa_reference: str,
    *,
    bodies: tuple[PublicBodyId, ...] = (PublicBodyId.HOME_OFFICE,),
    **certificate_fields,
) -> Application:
    application = create_application_in_db(
        session,
        laa_reference=laa_reference,
        public_bodies=[ApplicationPublicBody(public_body_id=body) for body in bodies],
    )
    return _set_certificate(session, application, **certificate_fields)


def _claim(
    session: Session,
    application: Application,
    status: ClaimStatus,
    *,
    gross: str = "1000.00",
    claim_type: ClaimType = ClaimType.PAYMENT_ON_ACCOUNT,
    submission_date: datetime | None = None,
):
    return create_claim_in_db(
        session,
        application_id=application.application_id,
        status=status,
        claim_type=claim_type,
        total_profit_cost_gross=gross,
        total_profit_cost_vat_zero="0.00",
        submission_date=submission_date,
    )


def _set_public_bodies(
    session: Session, application: Application, bodies: list[PublicBodyId]
) -> None:
    for existing in session.exec(
        select(ApplicationPublicBody).where(
            ApplicationPublicBody.application_id == application.application_id
        )
    ).all():
        session.delete(existing)
    session.commit()
    for body in bodies:
        session.add(
            ApplicationPublicBody(
                application_id=application.application_id, public_body_id=body
            )
        )
    session.commit()


def _get(client, params: dict | None = None):
    return client.get(
        URL,
        params=DEFAULT_PARAMS if params is None else params,
        headers=FINANCE_HEADERS,
    )


def _rows(client, params: dict | None = None) -> list[dict[str, str]]:
    response = _get(client, params)
    assert response.status_code == 200
    return parse_csv_rows(response.text)


def _references(client, params: dict | None = None) -> list[str]:
    return [row["Case Reference"] for row in _rows(client, params)]


class TestGetCostLimitForecastReport:
    """E2E tests for GET /reports/cost-limit-forecast."""

    def test_200_returns_csv_attachment_with_expected_headers_and_filename(
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
            "2026-09-01-164501 - Report - IDDS Cost estimation and Forecasting - "
            "OFFICIAL-SENSITIVE - LAA Use Only.csv"
        ) in response.headers["content-disposition"]
        assert parse_csv_fieldnames(response.text) == COST_LIMIT_FORECAST_REPORT_HEADERS

    def test_200_returns_headers_only_when_no_records_qualify(self, client):
        response = _get(client)

        assert response.status_code == 200
        assert parse_csv_fieldnames(response.text) == COST_LIMIT_FORECAST_REPORT_HEADERS
        assert parse_csv_rows(response.text) == []

    def test_200_row_contains_all_required_fields(self, session, client):
        _live_application(session)

        assert _rows(client) == [
            {
                "Case Reference": "INQ-123-456",
                "Public Body(ies)": PublicBodyId.DEPARTMENT_FOR_TRANSPORT.value,
                "Cost Limit": "10000.00",
                "Total Remaining Cost Limit Value": "10000.00",
                "Certificate Effective Date": "15-03-2019",
            }
        ]

    def test_200_cost_limit_comes_from_the_proceeding_cost_limitation(
        self, session, client
    ):
        _live_application(session)
        proceeding = session.exec(
            select(Proceeding).where(Proceeding.proceeding_id == ProceedingId.IQOT)
        ).one()
        proceeding.substantive_cost_limitation = 25000
        session.add(proceeding)
        session.commit()

        row = _rows(client)[0]

        assert row["Cost Limit"] == "25000.00"
        assert row["Total Remaining Cost Limit Value"] == "25000.00"

    def test_200_remaining_value_only_deducts_pay_in_full_claims(self, session, client):
        application = _live_application(session)
        _claim(session, application, ClaimStatus.PAY_IN_FULL, gross="3000.00")
        _claim(session, application, ClaimStatus.PAY_IN_FULL, gross="250.50")
        _claim(session, application, ClaimStatus.SUBMITTED, gross="500.00")
        _claim(session, application, ClaimStatus.REJECTED, gross="700.00")
        _claim(session, application, ClaimStatus.REJECTED_WITH_AMENDMENT, gross="90.00")

        row = _rows(client)[0]

        assert row["Total Remaining Cost Limit Value"] == "6749.50"

    def test_200_remaining_value_ignores_the_stored_claim_balance_snapshot(
        self, session, client
    ):
        application = _live_application(session)
        earlier_claim = _claim(
            session,
            application,
            ClaimStatus.SUBMITTED,
            gross="2000.00",
            submission_date=datetime(2019, 2, 1, tzinfo=UTC),
        )
        latest_claim = _claim(
            session,
            application,
            ClaimStatus.SUBMITTED,
            gross="1000.00",
            submission_date=datetime(2019, 3, 1, tzinfo=UTC),
        )
        latest_claim.total_funds_remaining_after_claim = Decimal("8000.00")
        session.add(latest_claim)
        earlier_claim.status_id = ClaimStatus.PAY_IN_FULL
        session.add(earlier_claim)
        session.commit()

        row = _rows(client)[0]

        assert row["Total Remaining Cost Limit Value"] == "8000.00"

    def test_200_one_row_per_case_with_public_bodies_sorted_and_semicolon_separated(
        self, session, client
    ):
        application = _live_application(session)
        _set_public_bodies(
            session,
            application,
            [PublicBodyId.MINISTRY_OF_JUSTICE, PublicBodyId.CABINET_OFFICE],
        )
        _claim(session, application, ClaimStatus.PAY_IN_FULL, gross="100.00")
        _claim(session, application, ClaimStatus.PAY_IN_FULL, gross="100.00")

        rows = _rows(client)

        assert len(rows) == 1
        assert rows[0]["Public Body(ies)"] == "Cabinet Office; Ministry of Justice"

    def test_200_filters_on_certificate_effective_date_with_inclusive_bounds(
        self, session, client
    ):
        _live_application(session, start=date(2019, 1, 1))
        _another_application(session, "INQ-000-002", start=date(2019, 12, 31))
        _another_application(session, "INQ-000-003", start=date(2018, 12, 31))
        _another_application(session, "INQ-000-004", start=date(2020, 1, 1))
        _another_application(session, "INQ-000-005", start=None)

        assert sorted(_references(client)) == ["INQ-000-002", "INQ-123-456"]

    def test_200_orders_by_effective_date_oldest_first(self, session, client):
        _live_application(session, start=date(2019, 9, 1))
        _another_application(session, "INQ-000-002", start=date(2019, 2, 1))
        _another_application(session, "INQ-000-003", start=date(2019, 5, 1))

        rows = _rows(client)

        assert [row["Certificate Effective Date"] for row in rows] == [
            "01-02-2019",
            "01-05-2019",
            "01-09-2019",
        ]

    def test_200_orders_same_effective_date_by_case_reference(self, session, client):
        _live_application(session)
        _another_application(session, "INQ-000-002")
        _another_application(session, "INQ-999-999")

        assert _references(client) == ["INQ-000-002", "INQ-123-456", "INQ-999-999"]

    @pytest.mark.parametrize(
        "certificate_fields",
        [
            pytest.param({"status": "CANCELLED"}, id="not-live"),
            pytest.param(
                {"merits_decision": MeritsDecision.SUBMITTED}, id="not-granted"
            ),
            pytest.param({"merits_decision": MeritsDecision.REFUSED}, id="refused"),
            pytest.param({"end": PAST_DATE}, id="certificate-expired"),
        ],
    )
    def test_200_excludes_certificates_that_are_not_live(
        self, session, client, certificate_fields
    ):
        _live_application(session, **certificate_fields)

        assert _rows(client) == []

    @pytest.mark.parametrize(
        "end", [None, FAR_FUTURE_DATE], ids=["no-end-date", "future-end-date"]
    )
    def test_200_includes_certificates_that_have_not_ended(self, session, client, end):
        _live_application(session, end=end)

        assert _references(client) == ["INQ-123-456"]

    def test_200_excludes_certificate_ending_before_today_but_includes_one_ending_today(
        self, session, client, monkeypatch
    ):
        class FixedDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime(2019, 6, 1, 9, 0, 0, tzinfo=tz)

        monkeypatch.setattr(
            sys.modules["app.use_cases.generate_cost_limit_forecast_report"],
            "datetime",
            FixedDatetime,
        )
        _live_application(session, end=date(2019, 6, 1))
        _another_application(session, "INQ-000-002", end=date(2019, 5, 31))

        assert _references(client) == ["INQ-123-456"]

    def test_200_excludes_certificate_with_a_pay_in_full_final_bill(
        self, session, client
    ):
        application = _live_application(session)
        _claim(
            session,
            application,
            ClaimStatus.PAY_IN_FULL,
            gross="100.00",
            claim_type=ClaimType.FINAL_BILL,
        )

        assert _rows(client) == []

    @pytest.mark.parametrize(
        ("claim_type", "status"),
        [
            (ClaimType.FINAL_BILL, ClaimStatus.SUBMITTED),
            (ClaimType.FINAL_BILL, ClaimStatus.REJECTED),
            (ClaimType.PAYMENT_ON_ACCOUNT, ClaimStatus.PAY_IN_FULL),
            (ClaimType.NIL_BILL, ClaimStatus.SUBMITTED),
        ],
    )
    def test_200_keeps_certificate_when_no_final_bill_is_paid_in_full(
        self, session, client, claim_type, status
    ):
        application = _live_application(session)
        _claim(session, application, status, gross="100.00", claim_type=claim_type)

        assert _references(client) == ["INQ-123-456"]

    @pytest.mark.parametrize("gross", ["10000.00", "10500.00"])
    def test_200_excludes_certificate_with_no_remaining_value(
        self, session, client, gross
    ):
        application = _live_application(session)
        _claim(session, application, ClaimStatus.PAY_IN_FULL, gross=gross)

        assert _rows(client) == []

    def test_200_supports_at_least_2000_records(self, session, client):
        template = _application(session)
        applications = [
            Application(
                proceeding=ApplicationProceeding(
                    proceeding_id=ProceedingId.IQOT,
                    merits_decision=MeritsDecision.GRANTED,
                    certificate_start_date=date(2019, 1, 1)
                    + timedelta(days=index % 300),
                ),
                client_id=template.client_id,
                deceased_id=template.deceased_id,
                provider_id=template.provider_id,
                laa_reference=f"INQ-{index // 1000:03d}-{index % 1000:03d}",
                public_bodies=[
                    ApplicationPublicBody(public_body_id=PublicBodyId.HOME_OFFICE)
                ],
            )
            for index in range(2000)
        ]
        session.add_all(applications)
        session.commit()

        assert len(_rows(client)) == 2000

    @pytest.mark.parametrize(
        "params",
        [{"to": "2019-12-31"}, {"from": "2019-01-01"}, {}],
    )
    def test_422_when_date_params_missing(self, client, params):
        assert _get(client, params).status_code == 422

    @pytest.mark.parametrize(
        "params",
        [
            {"from": "not-a-date", "to": "2019-12-31"},
            {"from": "2019-01-01", "to": "31/12/2019"},
        ],
    )
    def test_422_when_date_params_invalid(self, client, params):
        assert _get(client, params).status_code == 422

    def test_422_when_from_is_after_to_and_no_csv_is_returned(self, client):
        response = _get(client, {"from": "2019-12-31", "to": "2019-01-01"})

        assert response.status_code == 422
        assert "text/csv" not in response.headers["content-type"]

    def test_200_accepts_a_range_of_many_years(self, session, client):
        _live_application(session)

        assert _references(client, {"from": "2000-01-01", "to": "2099-12-31"}) == [
            "INQ-123-456"
        ]

    def test_500_when_a_qualifying_case_has_no_public_bodies_and_no_csv_is_returned(
        self, session, client
    ):
        application = _live_application(session)
        _set_public_bodies(session, application, [])

        response = _get(client)

        assert response.status_code == 500
        assert "text/csv" not in response.headers["content-type"]

    def test_500_when_generation_fails_part_way_and_no_csv_is_returned(self, client):
        def failing_candidates(*_args):
            raise RuntimeError("database connection lost")
            yield  # pragma: no cover

        port = MagicMock()
        port.iter_forecast_candidates.side_effect = failing_candidates
        api.dependency_overrides[get_cost_limit_forecast_report_port] = lambda: port

        response = _get(client)

        assert response.status_code == 500
        assert "text/csv" not in response.headers["content-type"]
        assert "content-disposition" not in response.headers
        assert COST_LIMIT_FORECAST_REPORT_HEADERS[0] not in response.text


class TestGetCostLimitForecastReportAuth:
    """Authentication tests for GET /reports/cost-limit-forecast."""

    @pytest.mark.parametrize("role", FORECAST_ROLES, ids=lambda r: r.name)
    def test_200_returns_ok_for_finance_and_policy(self, client, role):
        response = client.get(
            URL,
            params=DEFAULT_PARAMS,
            headers={"Authorization": f"Bearer {role.value}"},
        )

        assert response.status_code == 200

    @pytest.mark.parametrize(
        "role",
        [role for role in Role if role not in FORECAST_ROLES],
        ids=lambda r: r.name,
    )
    def test_403_for_roles_without_costs_permission(self, client, role):
        response = client.get(
            URL,
            params=DEFAULT_PARAMS,
            headers={"Authorization": f"Bearer {role.value}"},
        )

        assert response.status_code == 403

    def test_401_without_credentials(self, client):
        response = client.get(URL, params=DEFAULT_PARAMS)

        assert response.status_code == 401
