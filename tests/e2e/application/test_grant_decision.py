from datetime import date, datetime, UTC
import pytest
from sqlmodel import select

from app.models.application.enums import MeritsDecision
from app.models.application.index import Application


pytestmark = pytest.mark.usefixtures("mock_gov_notify")


def _grant_decision_payload(overrides=None):
    payload = {"certificateStartDate": "2000-01-01"}
    if overrides:
        payload.update(overrides)
    return payload


def test_204_grant_decision_to_granted(session, client, auth_token):
    application = session.exec(select(Application)).first()
    laa_reference = application.laa_reference

    response = client.patch(
        f"/applications/{laa_reference}/grant-decision",
        json=_grant_decision_payload(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 204

    session.refresh(application)
    assert application.proceedings[0].merits_decision == MeritsDecision.GRANTED
    assert application.proceedings[0].certificate_start_date == date(2000, 1, 1)
    assert application.proceedings[0].certificate_issue_date == datetime.now(UTC).date()


def test_404_grant_decision_application_not_found(client, auth_token):
    response = client.patch(
        "/applications/99999/grant-decision",
        json=_grant_decision_payload(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 404


def test_422_grant_decision_missing_certificate_start_date(client, auth_token):
    response = client.patch(
        "/applications/1/grant-decision",
        json={},
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 422


def test_422_grant_decision_certificate_start_date_in_future(client, auth_token):
    future_date = date(datetime.now(UTC).year + 1, 1, 1).isoformat()

    response = client.patch(
        "/applications/1/grant-decision",
        json=_grant_decision_payload({"certificateStartDate": future_date}),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 422
