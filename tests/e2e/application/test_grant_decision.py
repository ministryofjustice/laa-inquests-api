from datetime import UTC, date, datetime

from app.auth.rbac import Role
from app.models.application.enums import CorrespondenceRecipientType, MeritsDecision
from tests.e2e.factories import create_application_in_db


def _grant_decision_payload(overrides=None):
    payload = {"certificateStartDate": "2000-01-01"}
    if overrides:
        payload.update(overrides)
    return payload


def test_204_grant_decision_to_granted(session, client):
    application = create_application_in_db(session)
    laa_reference = application.laa_reference
    assert application.proceeding.substantive_cost_limitation == 0

    response = client.patch(
        f"/applications/{laa_reference}/grant-decision",
        json=_grant_decision_payload(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Role.APPLICATIONS_CASEWORKER.value}",
        },
    )

    assert response.status_code == 204

    session.refresh(application)
    assert application.proceeding.merits_decision == MeritsDecision.GRANTED
    assert application.proceeding.certificate_start_date == date(2000, 1, 1)
    assert application.proceeding.certificate_issue_date == datetime.now(UTC).date()
    assert application.proceeding.substantive_cost_limitation == 10000


def test_204_grant_decision_does_not_persist_care_of_recipient_into_client_address(
    session, client
):
    application = create_application_in_db(
        session,
        client_overrides={
            "correspondence_recipient_type": CorrespondenceRecipientType.PERSON,
            "correspondence_recipient_name": "Test Recipient Name",
        },
    )
    original_address_line_1 = application.client.home_address.address_line_1

    response = client.patch(
        f"/applications/{application.laa_reference}/grant-decision",
        json=_grant_decision_payload(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Role.APPLICATIONS_CASEWORKER.value}",
        },
    )

    assert response.status_code == 204
    session.expire_all()
    assert application.client.home_address.address_line_1 == original_address_line_1


def test_404_grant_decision_application_not_found(client):
    response = client.patch(
        "/applications/99999/grant-decision",
        json=_grant_decision_payload(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Role.APPLICATIONS_CASEWORKER.value}",
        },
    )

    assert response.status_code == 404


def test_422_grant_decision_missing_certificate_start_date(client):
    response = client.patch(
        "/applications/1/grant-decision",
        json={},
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Role.APPLICATIONS_CASEWORKER.value}",
        },
    )

    assert response.status_code == 422


def test_422_grant_decision_certificate_start_date_in_future(client):
    future_date = date(datetime.now(UTC).year + 1, 1, 1).isoformat()

    response = client.patch(
        "/applications/1/grant-decision",
        json=_grant_decision_payload({"certificateStartDate": future_date}),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Role.APPLICATIONS_CASEWORKER.value}",
        },
    )

    assert response.status_code == 422


def test_409_grant_decision_application_already_granted(client, session):
    application = create_application_in_db(
        session, proceeding_overrides={"merits_decision": MeritsDecision.GRANTED}
    )
    laa_reference = application.laa_reference

    response = client.patch(
        f"/applications/{laa_reference}/grant-decision",
        json=_grant_decision_payload(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Role.APPLICATIONS_CASEWORKER.value}",
        },
    )

    assert response.status_code == 409
